from apify_client import ApifyClient
from datetime import datetime
import json
import re


# ==============================
# CONFIG
# ==============================

API_TOKEN = "<YOUR_API_TOKEN>"

ACTOR_ID = "Wpp1BZ6yGWjySadk3"

PROFILE_URL = input("Enter the LinkedIn profile URL: ")

MAX_POSTS = int(input("Enter the maximum number of posts to scrape. Default is 30: "))

MAX_POSTS = MAX_POSTS if MAX_POSTS > 0 else 30


# ==============================
# APIFY CLIENT
# ==============================

client = ApifyClient(API_TOKEN)


# ==============================
# HASHTAG / MENTION EXTRACTION
# ==============================

def extract_hashtags(text):
    if not text:
        return []

    return re.findall(r'#[A-Za-z0-9_]+', text)


def extract_mentions(text):
    if not text:
        return []

    return re.findall(r'@[A-Za-z0-9_.-]+', text)


# ==============================
# ACTOR INPUT
# ==============================

run_input = {
    "urls": [PROFILE_URL],
    "limitPerSource": MAX_POSTS,
    "deepScrape": True,
    "fetchDocumentDetails": False,
    "numComments": 0,
    "numLikes": 0,
    "rawData": False
}


# ==============================
# RUN ACTOR
# ==============================

print("Scraping LinkedIn...")

run = client.actor(ACTOR_ID).call(
    run_input=run_input
)


# ==============================
# GET DATASET
# ==============================

dataset = client.dataset(run.default_dataset_id)

items = list(dataset.iterate_items())


# ==============================
# PROFILE DATA
# ==============================

profile = {
    "username": None,
    "name": None,
    "followers": None,
    "profile_url": PROFILE_URL
}


posts = []


# ==============================
# PROCESS POSTS
# ==============================

for item in items:

    # Get profile information
    if profile["username"] is None:
        profile["username"] = item.get("authorProfileId")

    if profile["name"] is None:
        profile["name"] = item.get("authorName")

    if profile["profile_url"] == PROFILE_URL:
        profile["profile_url"] = item.get(
            "authorProfileUrl"
        ) or PROFILE_URL


    # Get post text
    text = item.get("text") or ""


    # Create simplified post
    post = {
        "post_url": item.get("url"),
        "text": text,
        "hashtags": extract_hashtags(text),
        "mentions": extract_mentions(text),
        "date": item.get("postedAtISO"),
        "likes": item.get("numLikes"),
        "comments": item.get("numComments"),
        "shares": item.get("numShares")
    }

    posts.append(post)


# ==============================
# FINAL JSON
# ==============================

result = {
    "platform": "linkedin",
    "username": profile["username"],
    "profile_url": PROFILE_URL,

    "profile": profile,

    "posts_count": len(posts),

    "posts": posts,

    "scraped_at": datetime.now().isoformat()
}


# ==============================
# SAVE JSON
# ==============================

filename = f"linkedin_{profile['username']}.json"

with open(filename, "w", encoding="utf-8") as f:
    json.dump(
        result,
        f,
        indent=2,
        ensure_ascii=False
    )


print(f"\nSaved successfully: {filename}")


# ==============================
# DISPLAY
# ==============================

print(json.dumps(
    result,
    indent=2,
    ensure_ascii=False
))