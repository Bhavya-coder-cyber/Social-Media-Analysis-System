from apify_client import ApifyClient
from dotenv import load_dotenv
import os
import json
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")

if not API_TOKEN:
    raise ValueError("API_TOKEN not found in .env file")


client = ApifyClient(API_TOKEN)

ACTOR_ID = "3hbiY2nfMGfbNdh1w"

username = input("Enter the username: ")

MAX_TWEETS = int(input("Enter the maximum number of tweets to scrape. Default is 50: "))


MAX_TWEETS = (MAX_TWEETS+2)*2 if MAX_TWEETS > 0 else 102


# ============================================================
# GET AUTHOR INFORMATION
# ============================================================

def get_author_info(author):

    if not author:
        return None

    return {
        "id": author.get("id"),
        "username": author.get("userName"),
        "name": author.get("name"),
        "bio": author.get("description"),
        "followers": author.get("followers"),
        "following": author.get("following"),

        "blue_verified": author.get("isBlueVerified"),

        "profile_url": author.get("twitterUrl"),

        "profile_picture": author.get("profilePicture"),

        "posts_count": author.get("statusesCount"),

        "account_created_at": author.get("createdAt")
    }


# ============================================================
# SCRAPE X PROFILE
# ============================================================

def scrape_x_profile(username):

    print(f"\nScraping @{username}...")

    run_input = {
        "searchTerms": [],
        "startUrls": [],

        "twitterHandles": [username],

        "conversationIds": [],

        "maxItems": MAX_TWEETS,

        "sort": "Latest",

        "tweetLanguage": "en",

        "onlyVerifiedUsers": False,
        "onlyTwitterBlue": False,
        "onlyImage": False,
        "onlyVideo": False,
        "onlyQuote": False,

        "includeReplies": False,

        "author": username,

        "includeSearchTerms": False,

        "debugMode": False,
    }


    # ========================================================
    # RUN APIFY ACTOR
    # ========================================================

    run = client.actor(ACTOR_ID).call(
        run_input=run_input
    )

    print("Scraping completed.")


    # ========================================================
    # GET DATASET
    # ========================================================

    dataset = client.dataset(
        run.default_dataset_id
    )


    posts = []
    profile = None


    # ========================================================
    # PROCESS TWEETS
    # ========================================================

    for item in dataset.iterate_items():

        # ----------------------------------------------------
        # AUTHOR / PROFILE
        # ----------------------------------------------------

        author = item.get("author")

        if profile is None:
            profile = get_author_info(author)


        # ----------------------------------------------------
        # MEDIA
        # ----------------------------------------------------

        media = item.get("media", [])

        media_type = item.get("mediaType")

        if media_type == "photo":
            media_type = "image"


        # ----------------------------------------------------
        # TWEET
        # ----------------------------------------------------

        post = {

            "post_id": item.get("id"),

            "post_url": item.get("url"),

            "post_type": "tweet",

            "text": item.get("text"),

            "date": item.get("createdAt"),

            # "language": item.get("lang"),


            # -----------------------------------------------
            # ENGAGEMENT
            # -----------------------------------------------

            "likes": item.get("likeCount"),

            "comments": item.get("replyCount"),

            "reposts": item.get("retweetCount"),

            "quotes": item.get("quoteCount"),

            "bookmarks": item.get("bookmarkCount"),

            "views": item.get("viewCount"),


            # -----------------------------------------------
            # POST TYPE / STATUS
            # -----------------------------------------------

            "is_repost": item.get("isRetweet"),

            "is_quote": item.get("isQuote"),

            "is_reply": item.get("isReply"),

            "is_pinned": item.get("isPinned"),


            # -----------------------------------------------
            # CONTENT
            # -----------------------------------------------

            "hashtags": item.get("hashtags", []),

            "mentions": item.get("mentions", []),

            "links": item.get("links", []),


            # -----------------------------------------------
            # MEDIA
            # -----------------------------------------------

            "media": {
                "has_media": len(media) > 0,

                "media_type": media_type,

                "media_count": len(media),

                "media_urls": media
            },
        }


        posts.append(post)


    # ========================================================
    # FALLBACK PROFILE
    # ========================================================

    if profile is None:

        profile = {
            "id": None,
            "username": username,
            "name": None,
            "bio": None,
            "followers": None,
            "following": None,
            "verified": None,
            "blue_verified": None,
            "location": None,
            "profile_url": f"https://x.com/{username}",
            "profile_picture": None,
            "posts_count": None,
            "media_count": None,
            "likes_given": None,
            "account_created_at": None
        }


    # ========================================================
    # FINAL RESULT
    # ========================================================

    result = {

        "platform": "x",

        "username": username,

        "profile_url": f"https://x.com/{username}",

        "profile": profile,

        "posts_count": len(posts),

        "posts": posts,

        "scraped_at": datetime.now().isoformat()
    }


    return result


# ============================================================
# SAVE JSON
# ============================================================

def save_json(data, username):

    filename = f"x_{username}.json"

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )

    print(f"\nJSON saved successfully: {filename}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    data = scrape_x_profile(username)

    save_json(
        data,
        username
    )

    print(
        f"\nTotal posts collected: "
        f"{data['posts_count']}"
    )