import os
import json
from datetime import datetime
from dotenv import load_dotenv
from apify_client import ApifyClient


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")

if not API_TOKEN:
    raise ValueError(
        "API_TOKEN not found in .env file"
    )


# ============================================================
# CONFIGURATION
# ============================================================

ACTOR_ID = "shu8hvrXbJbY3Eb9W"

PROFILE_NAME = input(
    "Enter the profile name: "
).strip().lower()

PROFILE_URL = (
    f"https://www.instagram.com/{PROFILE_NAME}/"
)

MAX_POSTS_INPUT = input(
    "Enter the maximum number of posts to scrape. "
    "Default is 30: "
).strip()

MAX_POSTS = (
    int(MAX_POSTS_INPUT)
    if MAX_POSTS_INPUT.isdigit()
    else 30
)

if MAX_POSTS <= 0:
    MAX_POSTS = 30


# ============================================================
# APIFY CLIENT
# ============================================================

client = ApifyClient(API_TOKEN)


# ============================================================
# 1. SCRAPE PROFILE DETAILS
# ============================================================

print()
print("=" * 60)
print("STEP 1: SCRAPING PROFILE INFORMATION")
print("=" * 60)

profile_input = {
    "resultsType": "details",

    "directUrls": [
        PROFILE_URL
    ]
}

profile_run = client.actor(
    ACTOR_ID
).call(
    run_input=profile_input
)

profile_dataset = client.dataset(
    profile_run.default_dataset_id
)

profile_items = list(
    profile_dataset.iterate_items()
)

print(
    f"Profile records received: "
    f"{len(profile_items)}"
)


# ============================================================
# INITIAL PROFILE
# ============================================================

profile = {
    "username": PROFILE_NAME,
    "name": None,
    "biography": None,
    "followers": None,
    "following": None,
    "posts_count": None,
    "verified": None,
    "is_business_account": None,
    "private": None,
    "profile_url": PROFILE_URL
}


# ============================================================
# PROCESS PROFILE INFORMATION
# ============================================================

if profile_items:

    profile_data = profile_items[0]

    profile["username"] = (
        profile_data.get("username")
        or PROFILE_NAME
    )

    profile["name"] = profile_data.get(
        "fullName"
    )

    profile["biography"] = profile_data.get(
        "biography"
    )

    profile["followers"] = profile_data.get(
        "followersCount"
    )

    profile["following"] = profile_data.get(
        "followsCount"
    )

    profile["posts_count"] = profile_data.get(
        "postsCount"
    )

    profile["verified"] = profile_data.get(
        "verified"
    )

    profile["is_business_account"] = (
        profile_data.get("isBusinessAccount")
    )

    profile["private"] = profile_data.get(
        "private"
    )

    profile["profile_url"] = (
        profile_data.get("url")
        or PROFILE_URL
    )


# ============================================================
# DISPLAY PROFILE
# ============================================================

print()
print("Profile information:")

print(
    f"Username   : {profile['username']}"
)

print(
    f"Name       : {profile['name']}"
)

print(
    f"Followers  : {profile['followers']}"
)

print(
    f"Following  : {profile['following']}"
)

print(
    f"Posts      : {profile['posts_count']}"
)

print(
    f"Verified   : {profile['verified']}"
)


# ============================================================
# 2. SCRAPE POSTS
# ============================================================

print()
print("=" * 60)
print("STEP 2: SCRAPING POSTS")
print("=" * 60)

posts_input = {
    "resultsType": "posts",

    "directUrls": [
        PROFILE_URL
    ],

    "resultsLimit": MAX_POSTS,

    "searchType": "hashtag",

    "addParentData": False
}


posts_run = client.actor(
    ACTOR_ID
).call(
    run_input=posts_input
)


# ============================================================
# GET POSTS DATASET
# ============================================================

posts_dataset = client.dataset(
    posts_run.default_dataset_id
)

items = list(
    posts_dataset.iterate_items()
)

print(
    f"Post records received: "
    f"{len(items)}"
)


# ============================================================
# POSTS LIST
# ============================================================

posts = []


# ============================================================
# PROCESS POSTS
# ============================================================

for item in items:

    # --------------------------------------------------------
    # Ignore anything that isn't a post
    # --------------------------------------------------------

    if not item.get("shortCode"):
        continue


    # --------------------------------------------------------
    # Caption
    # --------------------------------------------------------

    caption = item.get(
        "caption"
    ) or ""


    # --------------------------------------------------------
    # Hashtags
    # --------------------------------------------------------

    hashtags = item.get(
        "hashtags"
    )

    if hashtags is None:
        hashtags = []


    # --------------------------------------------------------
    # Mentions
    # --------------------------------------------------------

    mentions = item.get(
        "mentions"
    )

    if mentions is None:
        mentions = []


    # --------------------------------------------------------
    # Views
    # --------------------------------------------------------

    # Instagram only provides videoViewCount
    # for video/reel posts.

    video_view_count = None
    video_play_count = None
    if item.get("type") == "Video":
        video_view_count = item.get("videoViewCount")
        video_play_count = item.get("videoPlayCount")
    
    views = video_view_count

    # --------------------------------------------------------
    # Create normalized post
    # --------------------------------------------------------

    post = {

        "post_url": item.get(
            "url"
        ),

        "caption": caption,

        "hashtags": hashtags,

        "mentions": mentions,

        "date": item.get(
            "timestamp"
        ),

        "media_type": item.get(
            "type"
        ),

        "product_type": item.get(
            "productType"
        ),

        "likes": item.get(
            "likesCount"
        ),

        "comments": item.get(
            "commentsCount"
        ),

        "views": views,

        "video_view_count": video_view_count,

        "video_play_count": video_play_count,

        "is_pinned": item.get(
            "isPinned"
        )
    }


    posts.append(post)


# ============================================================
# FINAL RESULT
# ============================================================

result = {

    "platform": "instagram",

    "username": profile["username"],

    "profile_url": profile["profile_url"],

    "profile": profile,

    "posts_count": len(posts),

    "posts": posts,

    "scraped_at": datetime.now().isoformat()
}


# ============================================================
# SAVE JSON
# ============================================================

filename = (
    f"instagram_{profile['username']}.json"
)

with open(
    filename,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        result,
        file,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print("=" * 60)
print("INSTAGRAM SCRAPING COMPLETED")
print("=" * 60)

print(
    f"Username        : "
    f"{profile['username']}"
)

print(
    f"Name            : "
    f"{profile['name']}"
)

print(
    f"Followers       : "
    f"{profile['followers']}"
)

print(
    f"Following       : "
    f"{profile['following']}"
)

print(
    f"Total IG Posts  : "
    f"{profile['posts_count']}"
)

print(
    f"Posts Collected : "
    f"{len(posts)}"
)

print(
    f"Verified        : "
    f"{profile['verified']}"
)

print(
    f"Business        : "
    f"{profile['is_business_account']}"
)

print(
    f"Private         : "
    f"{profile['private']}"
)

print(
    f"Saved File      : "
    f"{filename}"
)

print("=" * 60)