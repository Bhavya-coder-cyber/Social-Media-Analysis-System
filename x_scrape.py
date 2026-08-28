import time
import csv
import json
import re

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


# ============================================================
# CONFIG
# ============================================================

SCROLL_PAUSE = 2.5
POST_LOAD_WAIT = 4


# ============================================================
# DRIVER
# ============================================================

def create_driver():

    options = Options()

    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-notifications")

    # Keep browser visible while debugging
    # options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)

    return driver


# ============================================================
# EXTRACT NUMBER
# ============================================================

def parse_count(text):

    if not text:
        return 0

    text = text.replace(",", "").strip()

    # Examples:
    # 123
    # 1.2K
    # 3.5M
    # 1B

    match = re.search(
        r"([\d.]+)\s*([KMB])?",
        text,
        re.IGNORECASE
    )

    if not match:
        return 0

    number = float(match.group(1))
    suffix = match.group(2)

    if suffix:

        suffix = suffix.upper()

        if suffix == "K":
            number *= 1_000

        elif suffix == "M":
            number *= 1_000_000

        elif suffix == "B":
            number *= 1_000_000_000

    return int(number)


# ============================================================
# FIND METRIC FROM ARTICLE
# ============================================================

def extract_metric(article, metric):

    try:

        # ----------------------------------------------------
        # First try aria-label
        # ----------------------------------------------------

        elements = article.find_elements(
            By.XPATH,
            ".//*[@aria-label]"
        )

        for element in elements:

            aria = element.get_attribute("aria-label")

            if not aria:
                continue

            aria_lower = aria.lower()

            if metric == "replies":
                keywords = [
                    "reply",
                    "replies"
                ]

            elif metric == "reposts":
                keywords = [
                    "repost",
                    "reposts",
                    "retweet",
                    "retweets"
                ]

            elif metric == "likes":
                keywords = [
                    "like",
                    "likes"
                ]

            elif metric == "bookmarks":
                keywords = [
                    "bookmark",
                    "bookmarks"
                ]

            elif metric == "views":
                keywords = [
                    "view",
                    "views"
                ]

            else:
                keywords = []

            for keyword in keywords:

                if keyword in aria_lower:

                    value = parse_count(aria)

                    if value > 0:
                        return value

        # ----------------------------------------------------
        # Try data-testid buttons
        # ----------------------------------------------------

        testid_map = {

            "replies": [
                "reply"
            ],

            "reposts": [
                "retweet"
            ],

            "likes": [
                "like"
            ],

            "bookmarks": [
                "bookmark"
            ],

            "views": [
                "analytics"
            ]

        }

        for testid in testid_map.get(metric, []):

            elements = article.find_elements(
                By.XPATH,
                f'.//*[@data-testid="{testid}"]'
            )

            for element in elements:

                try:

                    text = element.text.strip()

                    if text:

                        value = parse_count(text)

                        if value > 0:
                            return value

                    aria = element.get_attribute(
                        "aria-label"
                    )

                    if aria:

                        value = parse_count(aria)

                        if value > 0:
                            return value

                except Exception:
                    pass

    except Exception:
        pass

    return 0


# ============================================================
# FIND ACTUAL POST ARTICLE
# ============================================================

def find_post_article(driver, post_url):

    try:

        # Wait until an article exists
        WebDriverWait(
            driver,
            15
        ).until(
            EC.presence_of_element_located(
                (By.TAG_NAME, "article")
            )
        )

    except TimeoutException:

        return None

    articles = driver.find_elements(
        By.TAG_NAME,
        "article"
    )

    target_status = post_url.split("/status/")[-1]

    # --------------------------------------------------------
    # Find article containing THIS exact status URL
    # --------------------------------------------------------

    for article in articles:

        try:

            links = article.find_elements(
                By.TAG_NAME,
                "a"
            )

            for link in links:

                href = link.get_attribute(
                    "href"
                )

                if not href:
                    continue

                if (
                    "/status/" in href
                    and target_status in href
                ):

                    return article

        except Exception:
            continue

    # --------------------------------------------------------
    # Fallback: find article containing tweet text
    # --------------------------------------------------------

    for article in articles:

        try:

            tweet_text = article.find_elements(
                By.XPATH,
                './/*[@data-testid="tweetText"]'
            )

            if tweet_text:

                return article

        except Exception:
            continue

    return None


# ============================================================
# POST TEXT
# ============================================================

def extract_text(article):

    try:

        elements = article.find_elements(
            By.XPATH,
            './/*[@data-testid="tweetText"]'
        )

        texts = []

        for element in elements:

            text = element.text.strip()

            if text:
                texts.append(text)

        return "\n".join(texts)

    except Exception:

        return ""


# ============================================================
# POST DATE
# ============================================================

def extract_date(article):

    try:

        time_element = article.find_element(
            By.TAG_NAME,
            "time"
        )

        return (
            time_element
            .get_attribute("datetime")
            or ""
        )

    except Exception:

        return ""


# ============================================================
# AUTHOR
# ============================================================

def extract_author(article):

    try:

        # Look for links that point to a profile
        links = article.find_elements(
            By.XPATH,
            './/a[contains(@href, "/")]'
        )

        for link in links:

            href = link.get_attribute(
                "href"
            )

            if not href:
                continue

            # Ignore status links
            if "/status/" in href:
                continue

            if "x.com/" not in href:
                continue

            username = href.rstrip(
                "/"
            ).split("/")[-1]

            # Ignore navigation links
            if username.lower() in [
                "home",
                "explore",
                "notifications",
                "messages",
                "search",
                "settings"
            ]:
                continue

            if username:

                return username

    except Exception:
        pass

    return ""


# ============================================================
# MEDIA
# ============================================================

def extract_media(article):

    media = []

    try:

        # ----------------------------------------------------
        # Only images inside the actual tweet
        # ----------------------------------------------------

        images = article.find_elements(
            By.XPATH,
            './/img[contains(@src, "pbs.twimg.com/media")]'
        )

        for image in images:

            src = image.get_attribute(
                "src"
            )

            if src and src not in media:

                # Prefer original/large image
                src = re.sub(
                    r"&name=[^&]+",
                    "&name=large",
                    src
                )

                media.append(src)

    except Exception:
        pass

    return media


# ============================================================
# SCRAPE SINGLE POST
# ============================================================

def scrape_post(driver, post_url):

    print()
    print("=" * 70)
    print("SCRAPING")
    print(post_url)
    print("=" * 70)

    driver.get(post_url)

    time.sleep(POST_LOAD_WAIT)

    result = {

        "post_url": post_url,

        "author": "",

        "text": "",

        "date": "",

        "replies": 0,

        "reposts": 0,

        "likes": 0,

        "bookmarks": 0,

        "views": 0,

        "media": []

    }

    article = find_post_article(
        driver,
        post_url
    )

    if article is None:

        print("❌ Could not find actual post article")

        return result

    # --------------------------------------------------------
    # Extract everything
    # --------------------------------------------------------

    result["author"] = extract_author(
        article
    )

    result["text"] = extract_text(
        article
    )

    result["date"] = extract_date(
        article
    )

    result["replies"] = extract_metric(
        article,
        "replies"
    )

    result["reposts"] = extract_metric(
        article,
        "reposts"
    )

    result["likes"] = extract_metric(
        article,
        "likes"
    )

    result["bookmarks"] = extract_metric(
        article,
        "bookmarks"
    )

    result["views"] = extract_metric(
        article,
        "views"
    )

    result["media"] = extract_media(
        article
    )

    # --------------------------------------------------------
    # Print
    # --------------------------------------------------------

    print(
        "Author   :",
        result["author"]
    )

    print(
        "Text     :",
        result["text"][:100]
    )

    print(
        "Date     :",
        result["date"]
    )

    print(
        "Replies  :",
        result["replies"]
    )

    print(
        "Reposts  :",
        result["reposts"]
    )

    print(
        "Likes    :",
        result["likes"]
    )

    print(
        "Bookmarks:",
        result["bookmarks"]
    )

    print(
        "Views    :",
        result["views"]
    )

    print(
        "Media    :",
        len(result["media"])
    )

    return result


# ============================================================
# COLLECT ONLY USER'S POSTS
# ============================================================

def scrape_post_urls(
    driver,
    username,
    target_count
):

    profile_url = (
        f"https://x.com/{username}"
    )

    print()
    print("=" * 70)
    print("OPENING PROFILE")
    print("=" * 70)

    driver.get(profile_url)

    time.sleep(5)

    post_urls = []

    seen = set()

    previous_height = 0
    no_change_count = 0

    # Normalize username
    username = username.lower().lstrip("@")

    while len(post_urls) < target_count:

        articles = driver.find_elements(
            By.TAG_NAME,
            "article"
        )

        print(
            f"Visible articles: {len(articles)} | "
            f"Collected: {len(post_urls)}/{target_count}"
        )

        for article in articles:

            if len(post_urls) >= target_count:
                break

            try:

                links = article.find_elements(
                    By.TAG_NAME,
                    "a"
                )

                for link in links:

                    href = link.get_attribute(
                        "href"
                    )

                    if not href:
                        continue

                    if "/status/" not in href:
                        continue

                    href = href.split("?")[0]

                    # ------------------------------------------------
                    # IMPORTANT:
                    # Only collect URLs belonging to requested user
                    # ------------------------------------------------

                    match = re.search(
                        r"x\.com/([^/]+)/status/(\d+)",
                        href,
                        re.IGNORECASE
                    )

                    if not match:
                        continue

                    post_username = (
                        match.group(1)
                        .lower()
                    )

                    if post_username != username:
                        continue

                    if href in seen:
                        continue

                    seen.add(href)
                    post_urls.append(href)

                    print(
                        f"[{len(post_urls)}/{target_count}] "
                        f"{href}"
                    )

                    break

            except Exception:
                continue

        if len(post_urls) >= target_count:
            break

        # --------------------------------------------------------
        # Scroll
        # --------------------------------------------------------

        driver.execute_script(
            "window.scrollTo("
            "0, document.body.scrollHeight"
            ");"
        )

        time.sleep(
            SCROLL_PAUSE
        )

        current_height = driver.execute_script(
            "return document.body.scrollHeight"
        )

        if current_height == previous_height:

            no_change_count += 1

        else:

            no_change_count = 0

        previous_height = current_height

        if no_change_count >= 5:

            print(
                "\n⚠️ No new posts are loading."
            )

            break

    return post_urls[:target_count]


# ============================================================
# SAVE CSV
# ============================================================

def save_csv(
    posts,
    filename="x_posts.csv"
):

    if not posts:
        return

    fieldnames = [
        "post_url",
        "author",
        "text",
        "date",
        "replies",
        "reposts",
        "likes",
        "bookmarks",
        "views",
        "media"
    ]

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for post in posts:

            row = post.copy()

            row["media"] = " | ".join(
                row["media"]
            )

            writer.writerow(row)


# ============================================================
# SAVE JSON
# ============================================================

def save_json(
    posts,
    filename="x_posts.json"
):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            posts,
            file,
            indent=4,
            ensure_ascii=False
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    username = input(
        "Enter X username: "
    ).strip()

    username = username.lstrip("@")

    count_input = input(
        "Number of posts to collect (default 12): "
    ).strip()

    if count_input:

        try:

            target_count = int(
                count_input
            )

        except ValueError:

            print(
                "❌ Invalid number"
            )

            exit()

    else:

        target_count = 12

    if target_count <= 0:

        print(
            "❌ Number must be greater than 0"
        )

        exit()

    driver = create_driver()

    try:

        # ====================================================
        # STEP 1
        # Get post URLs
        # ====================================================

        post_urls = scrape_post_urls(
            driver,
            username,
            target_count
        )

        print()
        print("=" * 70)
        print(
            f"FOUND {len(post_urls)} POSTS"
        )
        print("=" * 70)

        # ====================================================
        # STEP 2
        # Scrape each post
        # ====================================================

        posts = []

        for index, post_url in enumerate(
            post_urls,
            start=1
        ):

            print(
                f"\nProcessing "
                f"{index}/{len(post_urls)}"
            )

            post = scrape_post(
                driver,
                post_url
            )

            posts.append(post)

            time.sleep(1)

        # ====================================================
        # STEP 3
        # Save
        # ====================================================

        save_csv(
            posts
        )

        save_json(
            posts
        )

        print()
        print("=" * 70)
        print("SCRAPING COMPLETE")
        print("=" * 70)

        print(
            f"Posts scraped: {len(posts)}"
        )

        print(
            "CSV  : x_posts.csv"
        )

        print(
            "JSON : x_posts.json"
        )

    finally:

        driver.quit()