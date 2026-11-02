// ============================================================
// PLATFORM & APPLICATION STATE
// ============================================================

const PLATFORM_DEFAULTS = () => ({
    reference: '',
    limit: 25,
    commentsPerVideo: 10,
    latest: null,
    fetchStatus: null
});

const state = {
    page: 'cross',
    currentPlatform: 'instagram',
    workspace: [],
    health: null,

    perPlatform: {
        instagram: PLATFORM_DEFAULTS(),
        x: PLATFORM_DEFAULTS(),
        linkedin: PLATFORM_DEFAULTS(),
        youtube: PLATFORM_DEFAULTS()
    }
};


// ============================================================
// DOM HELPERS & BASIC UTILITIES
// ============================================================

// Get a single DOM element.
const $ = s => document.querySelector(s);

// Get all matching DOM elements.
const $$ = s => document.querySelectorAll(s);

// Format numbers using the Indian numbering system.
const fmt = n =>
    new Intl.NumberFormat('en-IN', {
        notation: 'compact',
        maximumFractionDigits: 1
    }).format(Number(n) || 0);

// Escape HTML-sensitive characters before inserting user/source data.
const esc = s =>
    String(s ?? '').replace(
        /[&<>"']/g,
        m => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        }[m])
    );


// ============================================================
// TOAST NOTIFICATIONS
// ============================================================

function toast(m) {
    const t = $('#toast');

    t.textContent = m;
    t.classList.add('show');

    clearTimeout(toast.t);

    toast.t = setTimeout(
        () => t.classList.remove('show'),
        2600
    );
}


// ============================================================
// API HELPER
// ============================================================

async function api(url, opts = {}) {
    const r = await fetch(url, {
        headers: {
            'Content-Type': 'application/json',
            ...(opts.headers || {})
        },
        ...opts
    });

    let d = {};

    try {
        d = await r.json();
    } catch { }

    if (!r.ok) {
        throw new Error(
            d.error || `Request failed (${r.status})`
        );
    }

    return d;
}


// ============================================================
// PLATFORM STATE MANAGEMENT
// ============================================================

function platformState(p = state.currentPlatform) {
    return (
        state.perPlatform[p] ||
        (state.perPlatform[p] = PLATFORM_DEFAULTS())
    );
}


// ============================================================
// PAGE NAVIGATION
// ============================================================

function setPage(p) {
    state.page = p;

    // Update visible page.
    $$('.page').forEach(x =>
        x.classList.remove('active')
    );

    $(`#page-${p}`)?.classList.add('active');

    // Update active navigation item.
    $$('.nav').forEach(x =>
        x.classList.toggle(
            'active',
            x.dataset.page === p
        )
    );

    const titles = {
        cross: [
            'Cross Analytics',
            'Live cross-platform performance from your latest analyses'
        ],
        explorer: [
            'Content Explorer',
            'Search the live workspace'
        ],
        saved: [
            'Saved Analyses',
            'Load or manage snapshots'
        ],
        settings: [
            'Connection Setup',
            'Configure live platform connectors'
        ]
    };

    if (p === 'cross') {
        setHeader(...titles.cross);
        renderCross();
    } else if (p === 'explorer') {
        setHeader(...titles.explorer);
        renderExplorer();
    } else if (p === 'saved') {
        setHeader(...titles.saved);
        loadSaved();
    } else if (p === 'settings') {
        setHeader(...titles.settings);
        renderHealth();
    } else {
        openPlatform(p);
    }
}


// ============================================================
// HEADER
// ============================================================

function setHeader(a, b) {
    $('#pageTitle').textContent = a;
    $('#pageSub').textContent = b;
}


// ============================================================
// KPI CARD
// ============================================================

function k(label, val, sub) {
    return `
        <div class="kpi">
            <small>${label}</small>
            <b>${val}</b>
            <span>${sub}</span>
        </div>
    `;
}


// ============================================================
// WORKSPACE DATA
// ============================================================

// Combine records from all analyzed platforms.
function allRecords() {
    return state.workspace.flatMap(
        x => x.records || []
    );
}


// ============================================================
// WORKSPACE SUMMARY
// ============================================================

function workspaceSummary() {
    const rs = allRecords();
    const uniq = {};

    rs.forEach(r => {
        const key = `${r.platform}|${r.username}`;

        uniq[key] = Math.max(
            uniq[key] || 0,
            +r.followers || 0
        );
    });

    const followers = Object.values(uniq).reduce(
        (a, b) => a + (+b || 0),
        0
    );

    const views = rs.reduce(
        (a, r) => a + (+r.views || 0),
        0
    );

    const inter = rs.reduce(
        (a, r) => a + (+r.interactions || 0),
        0
    );

    const posts = rs.reduce(
        (a, r) =>
            a + (r.is_profile_snapshot ? 0 : 1),
        0
    );

    return {
        posts,
        creators: Object.keys(uniq).length,
        followers,
        views,
        interactions: inter,

        likes: rs.reduce(
            (a, r) => a + (+r.likes || 0),
            0
        ),

        comments: rs.reduce(
            (a, r) => a + (+r.comments || 0),
            0
        ),

        shares: rs.reduce(
            (a, r) => a + (+r.shares || 0),
            0
        ),

        engagement_rate: views
            ? +(inter / views * 100).toFixed(2)
            : followers
                ? +(inter / followers * 100).toFixed(2)
                : 0
    };
}


// ============================================================
// SENTIMENT SUMMARY
// ============================================================

function sentSummary(rs) {
    const c = {
        Positive: 0,
        Neutral: 0,
        Negative: 0
    };

    rs.forEach(r => {
        c[r.sentiment] =
            (c[r.sentiment] || 0) + 1;
    });

    const t = rs.length || 1;

    return {
        counts: c,

        percentages: {
            Positive: +(c.Positive / t * 100).toFixed(1),
            Neutral: +(c.Neutral / t * 100).toFixed(1),
            Negative: +(c.Negative / t * 100).toFixed(1)
        }
    };
}


// ============================================================
// CROSS-PLATFORM ANALYTICS
// ============================================================

function renderCross() {
    const s = workspaceSummary();
    const sm = sentSummary(allRecords());

    // Render cross-platform KPI cards.
    $('#crossKpis').innerHTML = [
        k(
            'Posts analyzed',
            fmt(s.posts),
            'Fresh live content'
        ),
        k(
            'Creators',
            fmt(s.creators),
            'Platform identities'
        ),
        k(
            'Followers',
            fmt(s.followers),
            'Available from sources'
        ),
        k(
            'Interactions',
            fmt(s.interactions),
            'Likes + comments + shares'
        ),
        k(
            'Views / reach',
            fmt(s.views),
            'Where the source provides views'
        ),
        k(
            'Engagement',
            s.engagement_rate + '%',
            'Weighted by views when available'
        )
    ].join('');

    // Render sentiment donut chart.
    const p = sm.percentages;

    $('#posPct').textContent =
        p.Positive + '%';

    $('#donut').style.background = `
        conic-gradient(
            var(--green) 0 ${p.Positive}%,
            var(--yellow) ${p.Positive}% ${p.Positive + p.Neutral}%,
            var(--red) ${p.Positive + p.Neutral}% 100%
        )
    `;

    // Render sentiment rows.
    $('#sentRows').innerHTML = [
        ['Positive', p.Positive, 'var(--green)'],
        ['Neutral', p.Neutral, 'var(--yellow)'],
        ['Negative', p.Negative, 'var(--red)']
    ]
        .map(
            x => `
                <div class="sent-row">
                    <i style="background:${x[2]}"></i>
                    <span>${x[0]}</span>
                    <b>${x[1]}%</b>
                </div>
            `
        )
        .join('');

    renderBars();
    renderCreators();
}


// ============================================================
// PLATFORM COMPARISON BARS
// ============================================================

function renderBars() {
    const metric = $('#crossMetric').value;

    const vals = {
        instagram: 0,
        x: 0,
        linkedin: 0,
        youtube: 0
    };

    const followerMap = {};

    allRecords().forEach(r => {
        if (metric === 'followers') {
            const key =
                `${r.platform}|${r.username}`;

            followerMap[key] = Math.max(
                followerMap[key] || 0,
                +r.followers || 0
            );
        } else {
            vals[r.platform] +=
                metric === 'views'
                    ? +r.views || 0
                    : metric === 'posts'
                        ? (r.is_profile_snapshot ? 0 : 1)
                        : +r.interactions || 0;
        }
    });

    if (metric === 'followers') {
        Object.entries(followerMap).forEach(
            ([key, v]) => {
                const p = key.split('|')[0];
                vals[p] += v;
            }
        );
    }

    const max = Math.max(
        ...Object.values(vals),
        1
    );

    $('#platformBars').innerHTML =
        Object.entries(vals)
            .map(
                ([p, v]) => `
                    <div class="barrow">
                        <span class="bar-label">
                            ${p === 'x' ? 'X / Twitter' : p}
                        </span>

                        <div class="track">
                            <div
                                class="fill"
                                style="width:${v / max * 100}%"
                            ></div>
                        </div>

                        <span class="barval">
                            ${fmt(v)}
                        </span>
                    </div>
                `
            )
            .join('') ||
        `
            <div class="note">
                Run a live analysis on one or more platforms
                to populate cross analytics.
            </div>
        `;
}


// ============================================================
// CREATOR COMPARISON
// ============================================================

function renderCreators() {
    const map = {};

    allRecords().forEach(r => {
        const key = (r.username || '').toLowerCase();

        const b = map[key] ??= {
            creator: r.username,
            name: r.name,
            platforms: {},
            followers: 0,
            posts: 0,
            interactions: 0,
            views: 0
        };

        b.platforms[r.platform] =
            (b.platforms[r.platform] || 0) + 1;

        b.followers = Math.max(
            b.followers,
            +r.followers || 0
        );

        if (!r.is_profile_snapshot) {
            b.posts++;
        }

        b.interactions +=
            +r.interactions || 0;

        b.views +=
            +r.views || 0;
    });

    const rows = Object.values(map);

    $('#creatorRows').innerHTML =
        rows
            .map(
                c => `
                    <tr>
                        <td>
                            ${esc(c.name)}

                            <div
                                style="
                                    color:#647087;
                                    font-size:8px;
                                    margin-top:3px;
                                "
                            >
                                @${esc(c.creator)}
                            </div>
                        </td>

                        <td>
                            ${Object.keys(c.platforms)
                        .map(
                            x =>
                                `<span class="pill">${x}</span>`
                        )
                        .join(' ')}
                        </td>

                        <td>${fmt(c.followers)}</td>
                        <td>${fmt(c.posts)}</td>
                        <td>${fmt(c.interactions)}</td>

                        <td>
                            ${c.views
                        ? (
                            c.interactions /
                            c.views *
                            100
                        ).toFixed(2) + '%'
                        : '—'
                    }
                        </td>
                    </tr>
                `
            )
            .join('') ||
        `
            <tr>
                <td
                    colspan="6"
                    style="color:#68758b"
                >
                    No live analyses yet.
                    Use a platform page to run one.
                </td>
            </tr>
        `;
}


// ============================================================
// PLATFORM METADATA
// ============================================================

const meta = {
    instagram: [
        '◎',
        'Instagram Analytics',
        'Fresh profile, post and engagement analytics',
        'Username or profile URL'
    ],

    x: [
        '𝕏',
        'X / Twitter Analytics',
        'Fresh post, reach and conversation analytics',
        'Username or profile URL'
    ],

    linkedin: [
        'in',
        'LinkedIn Analytics',
        'Fresh professional content and interaction analytics',
        'Profile URL or username'
    ],

    youtube: [
        '▶',
        'YouTube Analytics',
        'Fresh videos, views and optional comment sentiment',
        'Channel handle or channel ID'
    ]
};


// ============================================================
// OPEN PLATFORM PAGE
// ============================================================

function openPlatform(p) {
    state.page = p;
    state.currentPlatform = p;

    $$('.page').forEach(x =>
        x.classList.remove('active')
    );

    $('#page-platform').classList.add('active');

    $$('.nav').forEach(x =>
        x.classList.toggle(
            'active',
            x.dataset.page === p
        )
    );

    const m = meta[p];

    setHeader(m[1], m[2]);

    $('#refLabel').textContent = m[3];

    $('#reference').placeholder =
        p === 'youtube'
            ? '@channelhandle or UC...'
            : p === 'linkedin'
                ? 'https://www.linkedin.com/in/username/'
                : '@username or profile URL';

    // Comments are only configurable for YouTube.
    $('#commentField').classList.toggle(
        'hidden',
        p !== 'youtube'
    );

    // Display connector status.
    $('#connectorState').textContent =
        p === 'youtube'
            ? (
                state.health?.youtube
                    ? 'YouTube connector ready'
                    : 'YouTube API key missing'
            )
            : (
                state.health?.apify
                    ? 'Apify connector ready'
                    : 'Apify token missing'
            );

    const ps = platformState(p);

    $('#reference').value =
        ps.reference || '';

    $('#limit').value =
        ps.limit;

    $('#commentsPerVideo').value =
        ps.commentsPerVideo;

    if (ps.fetchStatus) {
        setFetchStatus(...ps.fetchStatus);
    } else {
        clearFetchStatus();
    }

    renderLatest();
}


// ============================================================
// FETCH STATUS
// ============================================================

function setFetchStatus(kind, title, body) {
    const el = $('#fetchStatus');

    if (!el) return;

    el.className =
        `fetch-status ${kind || ''}`;

    el.innerHTML = `
        <strong>${esc(title)}</strong>
        ${esc(body || '')}
    `;

    el.classList.remove('hidden');

    platformState().fetchStatus = [
        kind,
        title,
        body
    ];
}


function clearFetchStatus() {
    const el = $('#fetchStatus');

    if (!el) return;

    el.classList.add('hidden');
    el.innerHTML = '';

    platformState().fetchStatus = null;
}


// ============================================================
// CSV EXPORT
// ============================================================

async function exportCsv() {
    const d = platformState().latest;

    const records =
        d &&
            d.records &&
            d.records.length
            ? d.records
            : state.workspace.flatMap(
                w => w.records || []
            );

    if (!records.length) {
        toast(
            'Run an analysis before exporting.'
        );
        return;
    }

    try {
        const r = await fetch(
            '/api/export-csv',
            {
                method: 'POST',
                headers: {
                    'Content-Type':
                        'application/json'
                },
                body: JSON.stringify({
                    records
                })
            }
        );

        if (!r.ok) {
            const e =
                await r.json().catch(
                    () => ({})
                );

            throw new Error(
                e.error || 'Export failed'
            );
        }

        const blob = await r.blob();

        const url =
            URL.createObjectURL(blob);

        const a =
            document.createElement('a');

        a.href = url;

        a.download =
            `social-media-analysis-${Date.now()}.csv`;

        document.body.appendChild(a);

        a.click();

        a.remove();

        URL.revokeObjectURL(url);

        toast('CSV exported.');
    } catch (e) {
        toast(e.message);
    }
}


// ============================================================
// LIVE PLATFORM ANALYSIS
// ============================================================

async function analyze() {
    const platform =
        state.currentPlatform;

    const ps =
        platformState(platform);

    const ref =
        $('#reference').value.trim();

    if (!ref) {
        setFetchStatus(
            'error',
            'Missing input',
            'Enter a username, handle, profile URL, or YouTube channel ID.'
        );

        $('#reference').focus();

        return;
    }

    const btn =
        $('#analyzeBtn');

    btn.disabled = true;

    btn.textContent =
        'Fetching live data…';

    setFetchStatus(
        '',
        'Fetching live data',
        'The application is calling the configured connector. This can take up to a few minutes for Apify.'
    );

    try {
        const data = await api(
            `/api/analyze/${state.currentPlatform}`,
            {
                method: 'POST',

                body: JSON.stringify({
                    reference: ref,
                    limit:
                        +$('#limit').value,
                    comments_per_video:
                        +$('#commentsPerVideo').value
                })
            }
        );
        ps.reference = ref;

        ps.limit =
            +$('#limit').value;

        ps.commentsPerVideo =
            +$('#commentsPerVideo').value;

        ps.latest = data;

        state.workspace.push(data);

        if (
            state.currentPlatform ===
            platform
        ) {
            renderLatest();
        }

        renderCross();

        if (data.records?.length) {
            setFetchStatus(
                'success',
                'Live data loaded',
                `${data.records.length} items returned in ${data.elapsed_seconds || 0}s.`
            );

            toast(
                `Fresh ${state.currentPlatform} data loaded.`
            );
        } else {
            setFetchStatus(
                'warn',
                'Connector returned no records',
                data.warning ||
                'Check the Actor input and output schema in Apify Console.'
            );
        }
    } catch (e) {
        setFetchStatus(
            'error',
            'Live fetch failed',
            e.message
        );

        toast(
            `Fetch failed: ${e.message}`
        );
    } finally {
        if (
            state.currentPlatform ===
            platform
        ) {
            btn.disabled = false;

            btn.textContent =
                'Fetch Live Data →';
        }
    }
}


// ============================================================
// METRIC FORMATTING
// ============================================================

function metricFmt(v) {
    return Number(v) > 0
        ? fmt(v)
        : '—';
}


// ============================================================
// LATEST PLATFORM ANALYSIS
// ============================================================

function renderLatest() {
    const d =
        platformState().latest;

    if (
        !d ||
        d.records?.length === 0
    ) {
        $('#platformKpis').innerHTML =
            k(
                'Status',
                'No data',
                'Run a live analysis above'
            );

        $('#platformPerformance').innerHTML =
            '<div class="note">No live result loaded.</div>';

        $('#platformSentiment').innerHTML =
            '<div class="note">No sentiment data yet.</div>';

        $('#postRows').innerHTML = '';

        renderInsights(null);

        return;
    }

    const s = d.summary;

    // Platform KPI cards.
    $('#platformKpis').innerHTML = [
        k(
            'Posts',
            fmt(s.posts),
            'Live content items'
        ),

        k(
            'Followers',
            metricFmt(s.followers),
            'Profile audience when available'
        ),

        k(
            'Likes',
            metricFmt(s.likes),
            'From live response'
        ),

        k(
            'Comments',
            metricFmt(s.comments),
            'From live response'
        ),

        k(
            'Views',
            metricFmt(s.views),
            'When source provides views'
        ),

        k(
            'Engagement',
            s.engagement_rate + '%',
            'Calculated from available metrics'
        )
    ].join('');

    // Performance metrics.
    const stats = [
        ['Views', s.views],
        ['Interactions', s.interactions],
        ['Likes', s.likes],
        ['Comments', s.comments]
    ];

    const max = Math.max(
        ...stats.map(x => x[1]),
        1
    );

    $('#platformPerformance').innerHTML =
        stats
            .map(
                x => `
                    <div class="barrow">
                        <span class="bar-label">
                            ${x[0]}
                        </span>

                        <div class="track">
                            <div
                                class="fill"
                                style="width:${x[1] / max * 100}%"
                            ></div>
                        </div>

                        <span class="barval">
                            ${metricFmt(x[1])}
                        </span>
                    </div>
                `
            )
            .join('');

    // Sentiment summary.
    const sm =
        d.sentiment?.percentages || {
            Positive: 0,
            Neutral: 0,
            Negative: 0
        };

    $('#platformSentiment').innerHTML = [
        [
            'Positive',
            sm.Positive,
            'positive'
        ],
        [
            'Neutral',
            sm.Neutral,
            'neutral'
        ],
        [
            'Negative',
            sm.Negative,
            'negative'
        ]
    ]
        .map(
            x => `
                <div class="sent-row">
                    <span class="pill ${x[2]}">
                        ${x[0]}
                    </span>

                    <b>${x[1]}%</b>
                </div>
            `
        )
        .join('');

    // Likes, Views and Engagement trend.
    const metricSelector = $('#trendMetric');

    const renderTrendChart = () => {
        const metric = metricSelector.value;

        const metricConfig = {
            likes: {
                title: 'Likes Trend',
                label: 'Likes',
                color: '#8b5cf6',
                format: value => Number(value).toLocaleString()
            },
            views: {
                title: 'Views Trend',
                label: 'Views',
                color: '#06b6d4',
                format: value => Number(value).toLocaleString()
            },
            engagement_rate: {
                title: 'Engagement Trend',
                label: 'Engagement',
                color: '#22c55e',
                format: value => `${Number(value).toFixed(2)}%`
            }
        };

        const config = metricConfig[metric] || metricConfig.likes;

        $('#trendChartTitle').textContent = config.title;

        const trendRecords = d.records
            .filter(r => !r.is_profile_snapshot)
            .map(r => ({
                date: Date.parse(r.date),
                value: Number(r[metric])
            }))
            .filter(r =>
                !isNaN(r.date) &&
                Number.isFinite(r.value)
            )
            .sort((a, b) => a.date - b.date);

        const chartWidth = 900;
        const chartHeight = 300;

        const left = 65;
        const right = 25;
        const top = 25;
        const bottom = 50;

        const maxValue = Math.max(
            ...trendRecords.map(r => r.value),
            1
        );

        const chartPoints = trendRecords.map((r, i) => {
            const x = left +
                (i / Math.max(trendRecords.length - 1, 1)) *
                (chartWidth - left - right);

            const y = chartHeight - bottom -
                (r.value / maxValue) *
                (chartHeight - top - bottom);

            return { x, y, ...r };
        });

        const linePoints = chartPoints
            .map(p => `${p.x},${p.y}`)
            .join(' ');

        const chartContainer = $('#likesTrendChart');

        // Clear previous chart and tooltip.
        chartContainer.innerHTML = '';

        if (trendRecords.length === 0) {
            chartContainer.innerHTML =
                '<div class="note">No data available for this metric.</div>';
            return;
        }

        chartContainer.innerHTML = `
        <svg
            viewBox="0 0 ${chartWidth} ${chartHeight}"
            width="100%"
            role="img"
            aria-label="${config.title}"
        >
            ${[0, 1, 2, 3, 4].map(i => {
            const y = top +
                (i / 4) * (chartHeight - top - bottom);

            const value = maxValue * (1 - i / 4);

            return `
                    <line
                        x1="${left}"
                        y1="${y}"
                        x2="${chartWidth - right}"
                        y2="${y}"
                        stroke="#334155"
                        stroke-dasharray="4 5"
                    />

                    <text
                        x="${left - 10}"
                        y="${y + 4}"
                        fill="#94a3b8"
                        font-size="12"
                        text-anchor="end"
                    >${config.format(value)}</text>
                `;
        }).join('')}

            <polyline
                points="${linePoints}"
                fill="none"
                stroke="${config.color}"
                stroke-width="3"
                stroke-linecap="round"
                stroke-linejoin="round"
            />

            ${chartPoints.map(p => `
                <circle
                    cx="${p.x}"
                    cy="${p.y}"
                    r="5"
                    fill="${config.color}"
                    stroke="#ffffff"
                    stroke-width="1.5"
                    class="likes-node"
                    data-date="${new Date(p.date).toLocaleDateString()}"
                    data-value="${p.value}"
                    style="cursor:pointer"
                />
            `).join('')}

            ${[
                chartPoints[0],
                chartPoints[Math.floor(chartPoints.length / 2)],
                chartPoints[chartPoints.length - 1]
            ].filter((p, i, arr) =>
                p && arr.indexOf(p) === i
            ).map(p => `
                <text
                    x="${p.x}"
                    y="${chartHeight - 15}"
                    fill="#94a3b8"
                    font-size="12"
                    text-anchor="middle"
                >
                    ${new Date(p.date).toLocaleDateString()}
                </text>
            `).join('')}
        </svg>
    `;

        // Custom floating tooltip.
        const tooltip = document.createElement('div');
        tooltip.className = 'likes-tooltip';

        tooltip.innerHTML = `
        <div class="tooltip-title">POST PERFORMANCE</div>

        <div class="tooltip-row">
            <span>📅 Posted</span>
            <span class="tooltip-value tooltip-date"></span>
        </div>

        <div class="tooltip-row">
            <span>${metric === 'likes' ? '❤️' :
                metric === 'views' ? '👁️' : '📈'} ${config.label}</span>
            <span class="tooltip-value tooltip-metric"></span>
        </div>
    `;

        chartContainer.appendChild(tooltip);

        chartContainer.querySelectorAll('.likes-node').forEach(node => {

            node.addEventListener('mouseenter', () => {
                tooltip.querySelector('.tooltip-date').textContent =
                    node.dataset.date;

                tooltip.querySelector('.tooltip-metric').textContent =
                    config.format(node.dataset.value);

                tooltip.style.display = 'block';
            });

            node.addEventListener('mousemove', event => {
                const tooltipWidth = tooltip.offsetWidth;
                const tooltipHeight = tooltip.offsetHeight;

                let x = event.clientX + 15;
                let y = event.clientY - tooltipHeight - 15;

                if (x + tooltipWidth > window.innerWidth - 10) {
                    x = event.clientX - tooltipWidth - 15;
                }

                if (y < 10) {
                    y = event.clientY + 15;
                }

                tooltip.style.left = `${Math.max(10, x)}px`;
                tooltip.style.top = `${y}px`;
            });

            node.addEventListener('mouseleave', () => {
                tooltip.style.display = 'none';
            });
        });
    };

    // Initial chart.
    renderTrendChart();

    // Update chart whenever metric changes.
    metricSelector.onchange = renderTrendChart;

    // Sort posts based on the selected filter.
    const sortBy = $('#contentSortFilter').value;

    const rows = [...d.records]
        .filter(
            r => !r.is_profile_snapshot
        )
        .sort((a, b) => {

            // Default: Highest engagement first.
            if (sortBy === 'engagement') {
                return (
                    (Number(b.engagement_rate) || 0) -
                    (Number(a.engagement_rate) || 0)
                );
            }

            // Convert post dates into timestamps.
            const dateA = Date.parse(a.date);
            const dateB = Date.parse(b.date);

            // Keep posts with invalid dates at the bottom.
            if (isNaN(dateA)) return 1;
            if (isNaN(dateB)) return -1;

            // Newest first.
            if (sortBy === 'latest') {
                return dateB - dateA;
            }

            // Oldest first.
            if (sortBy === 'oldest') {
                return dateA - dateB;
            }

            return 0;
        })
        .slice(0, 15);

    $('#postRows').innerHTML =
        rows
            .map(
                r => `
                    <tr>
                        <td>
                            ${String(
                    r.date || ''
                ).slice(0, 10) || '—'
                    }
                        </td>

                        <td>
                            ${r.url
                        ? `
                                        <a
                                            href="${esc(r.url)}"
                                            target="_blank"
                                            rel="noopener"
                                            style="
                                                color:#b9abff;
                                                text-decoration:none;
                                            "
                                        >
                                            ${esc(
                            (
                                r.text ||
                                '(untitled)'
                            )
                                .replace(
                                    /\s+/g,
                                    ' '
                                )
                                .slice(
                                    0,
                                    100
                                )
                        )}
                                        </a>
                                    `
                        : esc(
                            (
                                r.text ||
                                '(untitled)'
                            )
                                .replace(
                                    /\s+/g,
                                    ' '
                                )
                                .slice(
                                    0,
                                    100
                                )
                        )
                    }
                        </td>

                        <td>
                            ${metricFmt(r.likes)}
                        </td>

                        <td>
                            ${metricFmt(r.comments)}
                        </td>

                        <td>
                            ${metricFmt(r.shares)}
                        </td>

                        <td>
                            ${metricFmt(r.views)}
                        </td>

                        <td>
                            <b>
                                ${r.engagement_rate}%
                            </b>
                        </td>
                    </tr>
                `
            )
            .join('') ||
        `
            <tr>
                <td
                    colspan="7"
                    style="color:#68758b"
                >
                    No content posts were returned.
                    Profile-only data is still available
                    in the KPI cards.
                </td>
            </tr>
        `;

    renderInsights(d.insights);
}


// ============================================================
// CONTENT EXPLORER
// ============================================================

function renderExplorer() {
    const q =
        ($('#search').value || '').toLowerCase();

    const p =
        $('#fPlatform').value;

    const s =
        $('#fSent').value;

    const rows = allRecords()
        .filter(
            r =>
                (p === 'all' ||
                    r.platform === p) &&
                (s === 'all' ||
                    r.sentiment === s) &&
                (
                    (r.text || '')
                        .toLowerCase()
                        .includes(q) ||
                    (r.username || '')
                        .toLowerCase()
                        .includes(q)
                )
        )
        .slice(0, 120);

    $('#exploreRows').innerHTML =
        rows
            .map(
                r => `
                    <tr>
                        <td>
                            <span class="pill">
                                ${esc(r.platform)}
                            </span>
                        </td>

                        <td>
                            ${esc(r.name)}

                            <div
                                style="
                                    color:#647087;
                                    font-size:8px;
                                "
                            >
                                @${esc(r.username)}
                            </div>
                        </td>

                        <td>
                            ${esc(
                    (r.text || '')
                        .replace(
                            /\s+/g,
                            ' '
                        )
                        .slice(0, 120)
                )}
                        </td>

                        <td>
                            ${String(
                    r.date || ''
                ).slice(0, 10) || '—'
                    }
                        </td>

                        <td>
                            ${fmt(r.interactions)}
                        </td>

                        <td>
                            ${r.engagement_rate}%
                        </td>

                        <td>
                            <span
                                class="pill ${r.sentiment.toLowerCase()}"
                            >
                                ${r.sentiment}
                            </span>
                        </td>
                    </tr>
                `
            )
            .join('') ||
        `
            <tr>
                <td
                    colspan="7"
                    style="color:#68758b"
                >
                    No matching content in the
                    current live workspace.
                </td>
            </tr>
        `;
}


// ============================================================
// SAVE ANALYSIS
// ============================================================

async function saveRecords(
    records,
    source = ''
) {
    try {
        const d = await api(
            '/api/save',
            {
                method: 'POST',

                body: JSON.stringify({
                    records,
                    source_ref: source
                })
            }
        );

        toast(
            'Analysis saved locally.'
        );

        return d;
    } catch (e) {
        toast(e.message);
    }
}


// ============================================================
// LOAD SAVED ANALYSES
// ============================================================

async function loadSaved() {
    const list =
        await api('/api/saved');

    $('#savedList').innerHTML =
        list
            .map(
                x => `
                    <div class="saved-item">
                        <div>
                            <strong>
                                ${esc(
                    x.source_ref ||
                    'Cross-platform workspace'
                )}
                            </strong>

                            <small>
                                ${new Date(
                    x.created_at
                ).toLocaleString()}
                                · ${x.posts} posts
                                · ${x.platforms.join(', ')}
                            </small>
                        </div>

                        <div class="saved-actions">
                            <button
                                class="ghost load-btn"
                                data-id="${x.run_id}"
                            >
                                Load
                            </button>

                            <a
                                class="ghost"
                                href="/api/export?run_id=${encodeURIComponent(x.run_id)}"
                            >
                                Download
                            </a>

                            <button
                                class="ghost del-btn"
                                data-id="${x.run_id}"
                            >
                                Delete
                            </button>
                        </div>
                    </div>
                `
            )
            .join('') ||
        `
            <div class="note">
                No saved analyses yet.
            </div>
        `;

    // Load saved analysis buttons.
    $$('.load-btn').forEach(
        b =>
            b.onclick = () =>
                loadOne(b.dataset.id)
    );

    // Delete saved analysis buttons.
    $$('.del-btn').forEach(
        b =>
            b.onclick = async () => {
                if (
                    !confirm(
                        'Delete this saved analysis?'
                    )
                ) {
                    return;
                }

                await api(
                    '/api/saved/' +
                    b.dataset.id,
                    {
                        method: 'DELETE'
                    }
                );

                loadSaved();

                toast(
                    'Saved analysis deleted.'
                );
            }
    );
}


// ============================================================
// LOAD ONE SAVED ANALYSIS
// ============================================================

async function loadOne(id) {
    const d =
        await api(
            '/api/saved/' + id
        );

    const plat =
        d.records?.[0]?.platform;

    if (plat) {
        const ps =
            platformState(plat);

        ps.latest = d;

        ps.reference =
            d.source_ref ||
            ps.reference;
    }

    state.workspace = [d];

    setPage(
        d.records?.[0]?.platform ||
        'cross'
    );

    toast(
        'Saved analysis loaded into the current workspace.'
    );
}


// ============================================================
// SAVE ENTIRE WORKSPACE
// ============================================================

async function saveAll() {
    const rs = allRecords();

    if (!rs.length) {
        toast(
            'Run at least one live analysis first.'
        );

        return;
    }

    try {
        await api(
            '/api/save-all',
            {
                method: 'POST',

                body: JSON.stringify({
                    records: rs
                })
            }
        );

        toast(
            'Entire cross-platform workspace saved.'
        );
    } catch (e) {
        toast(e.message);
    }
}


// ============================================================
// CONNECTOR / API HEALTH
// ============================================================

async function renderHealth() {
    const h =
        await api('/api/health');

    state.health = h;

    $('#connectorList').innerHTML = [
        ['Instagram', 'Apify', h.apify],
        ['X / Twitter', 'Apify', h.apify],
        ['LinkedIn', 'Apify', h.apify],
        ['YouTube', 'YouTube Data API', h.youtube]
    ]
        .map(
            x => `
                <div
                    class="saved-item"
                    style="
                        grid-template-columns:1fr auto;
                        margin-bottom:8px;
                    "
                >
                    <div>
                        <strong>
                            ${x[0]}
                        </strong>

                        <small>
                            ${x[1]}
                        </small>
                    </div>

                    <span
                        class="pill ${x[2]
                    ? 'positive'
                    : 'negative'
                }"
                    >
                        ${x[2]
                    ? 'READY'
                    : 'NOT CONFIGURED'
                }
                    </span>
                </div>
            `
        )
        .join('');

    $('#engineStatus').textContent =
        (
            h.youtube ||
            (
                h.apify &&
                Object.values(
                    h.actors || {}
                ).some(Boolean)
            )
        )
            ? 'Live connectors configured'
            : 'Connector setup needed';
}


// ============================================================
// EVENT LISTENERS
// ============================================================

// Main navigation.
$$('.nav').forEach(
    b =>
        b.onclick = () =>
            setPage(
                b.dataset.page
            )
);

// Cross analytics metric selector.
$('#crossMetric').onchange =
    renderBars;
// Top content sorting filter.
$('#contentSortFilter').onchange = () => {
    renderLatest();
};
// Analyze button.
$('#analyzeBtn').onclick =
    analyze;

// Press Enter in reference input to analyze.
$('#reference').onkeydown =
    e => {
        if (e.key === 'Enter') {
            analyze();
        }
    };

// Save current analysis.
$('#saveRunBtn').onclick = () => {
    const d =
        platformState().latest;

    d &&
        saveRecords(
            d.records,
            d.source_ref
        );
};

// Keep platform reference state updated.
$('#reference').oninput =
    e => {
        platformState().reference =
            e.target.value;
    };

// Update record limit.
$('#limit').onchange =
    e => {
        platformState().limit =
            +e.target.value;
    };

// Update YouTube comments per video.
$('#commentsPerVideo').onchange =
    e => {
        platformState().commentsPerVideo =
            +e.target.value;
    };

// Export CSV.
$('#exportCsvBtn') &&
    (
        $('#exportCsvBtn').onclick =
        exportCsv
    );

// Save complete workspace.
$('#saveAllBtn').onclick =
    saveAll;


// ============================================================
// REFRESH BUTTON
// ============================================================

$('#refreshBtn').onclick = () => {
    if (state.page === 'cross') {
        renderCross();

        toast(
            'Cross analytics refreshed.'
        );
    } else if (
        [
            'instagram',
            'x',
            'linkedin',
            'youtube'
        ].includes(state.page)
    ) {
        analyze();
    } else {
        renderCross();

        if (
            state.page === 'explorer'
        ) {
            renderExplorer();
        }

        toast(
            'View refreshed.'
        );
    }
};


// ============================================================
// CONTENT EXPLORER FILTERS
// ============================================================

$('#search').oninput =
    renderExplorer;

$('#fPlatform').onchange =
    renderExplorer;

$('#fSent').onchange =
    renderExplorer;


// ============================================================
// RELOAD SAVED ANALYSES
// ============================================================

$('#reloadSaved').onclick =
    loadSaved;


// ============================================================
// INITIAL CONNECTOR HEALTH CHECK
// ============================================================

(async () => {
    try {
        state.health =
            await api('/api/health');

        $('#engineStatus').textContent =
            (
                state.health.youtube ||
                (
                    state.health.apify &&
                    Object.values(
                        state.health.actors || {}
                    ).some(Boolean)
                )
            )
                ? 'Live connectors configured'
                : 'Connector setup needed';
    } catch { }
})();


// ============================================================
// INSIGHTS
// ============================================================

function renderInsights(ins) {
    const h =
        $('#insightHashtags');

    const t =
        $('#insightTiming');

    if (!h || !t) {
        return;
    }

    // Display empty state when insights are unavailable.
    if (!ins) {
        h.innerHTML =
            '<div class="note">No insights yet.</div>';

        t.innerHTML =
            '<div class="note">No insights yet.</div>';

        return;
    }

    // --------------------------------------------------------
    // TOP HASHTAGS
    // --------------------------------------------------------

    const tags =
        ins.top_hashtags || [];

    h.innerHTML =
        tags.length
            ? tags
                .slice(0, 8)
                .map(x => {
                    const max =
                        Math.max(
                            ...tags.map(
                                y =>
                                    y.avg_interactions
                            ),
                            1
                        );

                    return `
                        <div class="barrow">
                            <span class="bar-label">
                                ${esc(x.tag)}
                            </span>

                            <div class="track">
                                <div
                                    class="fill"
                                    style="
                                        width:${x.avg_interactions /
                        max *
                        100
                        }%
                                    "
                                ></div>
                            </div>

                            <span class="barval">
                                ${metricFmt(
                            x.avg_interactions
                        )}
                            </span>
                        </div>
                    `;
                })
                .join('')
            : `
                <div class="note">
                    No hashtags found in this content.
                </div>
            `;


    // --------------------------------------------------------
    // BEST HOURS & DAYS
    // --------------------------------------------------------

    const hrs =
        ins.best_hours || [];

    const dys =
        ins.best_days || [];

    const hrHtml =
        hrs.length
            ? `
                <div
                    class="note"
                    style="margin-bottom:6px"
                >
                    Top hours (UTC)
                </div>
            ` +
            hrs
                .slice(0, 5)
                .map(x => {
                    const max =
                        Math.max(
                            ...hrs.map(
                                y =>
                                    y.avg_interactions
                            ),
                            1
                        );

                    return `
                        <div class="barrow">
                            <span class="bar-label">
                                ${String(
                        x.hour
                    ).padStart(2, '0')}:00
                            </span>

                            <div class="track">
                                <div
                                    class="fill"
                                    style="
                                        width:${x.avg_interactions /
                        max *
                        100
                        }%
                                    "
                                ></div>
                            </div>

                            <span class="barval">
                                ${metricFmt(
                            x.avg_interactions
                        )}
                            </span>
                        </div>
                    `;
                })
                .join('')
            : '';


    const dyHtml =
        dys.length
            ? `
                <div
                    class="note"
                    style="
                        margin:10px 0 6px
                    "
                >
                    Top days
                </div>
            ` +
            dys
                .slice(0, 5)
                .map(x => {
                    const max =
                        Math.max(
                            ...dys.map(
                                y =>
                                    y.avg_interactions
                            ),
                            1
                        );

                    return `
                        <div class="barrow">
                            <span class="bar-label">
                                ${esc(x.day)}
                            </span>

                            <div class="track">
                                <div
                                    class="fill"
                                    style="
                                        width:${x.avg_interactions /
                        max *
                        100
                        }%
                                    "
                                ></div>
                            </div>

                            <span class="barval">
                                ${metricFmt(
                            x.avg_interactions
                        )}
                            </span>
                        </div>
                    `;
                })
                .join('')
            : '';


    // Render timing insights or the appropriate empty state.
    t.innerHTML =
        (hrHtml + dyHtml) ||
        `
            <div class="note">
                Post dates were not returned,
                so timing insights are unavailable.
            </div>
        `;
}