from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from pathlib import Path

import json
import time
import re


# ==========================================================
# BROWSER SETUP
# ==========================================================

def prepare_browser():

    options = webdriver.ChromeOptions()

    options.add_argument("--start-maximized")

    # Persistent Chrome profile
    # This keeps your Instagram login session
    profile_path = Path.cwd() / "chrome_profile"

    options.add_argument(
        f"--user-data-dir={profile_path}"
    )

    driver = webdriver.Chrome(
        options=options
    )

    return driver


# ==========================================================
# LOGIN
# ==========================================================

def login_if_required(driver):

    driver.get(
        "https://www.instagram.com/"
    )

    print("\nOpening Instagram...")

    time.sleep(2)

    # Check existing session
    if "accounts/login" not in driver.current_url:

        print(
            "Existing Instagram session detected."
        )

        return True

    print("\n" + "=" * 60)
    print("INSTAGRAM LOGIN REQUIRED")
    print("=" * 60)

    print(
        "\nPlease log in manually in the Chrome window."
    )

    print(
        "If Instagram sends a verification code,"
    )

    print(
        "enter the code manually."
    )

    print(
        "\nWaiting up to 3 minutes..."
    )

    print("=" * 60)

    timeout = 180
    start_time = time.time()

    while time.time() - start_time < timeout:

        time.sleep(2)

        current_url = driver.current_url

        if "accounts/login" not in current_url:

            print(
                "\nLogin detected successfully."
            )

            return True

        elapsed = int(
            time.time() - start_time
        )

        print(
            f"Waiting for login... "
            f"{elapsed}/{timeout}s",
            end="\r"
        )

    print(
        "\n\nLogin timeout."
    )

    return False


# ==========================================================
# GET PROFILE INFORMATION
# ==========================================================

def get_profile(driver, username):

    profile_url = (
        f"https://www.instagram.com/"
        f"{username}/"
    )

    driver.get(profile_url)

    WebDriverWait(
        driver,
        15
    ).until(
        EC.presence_of_element_located(
            (By.TAG_NAME, "body")
        )
    )

    time.sleep(2)

    profile_data = {

        "platform": "instagram",

        "username": username,

        "profile_url": profile_url,

        "name": None,

        "bio": None,

        "followers": None,

        "following": None,

        "posts_count": None,

        "verified": False

    }

    # ------------------------------------------------------
    # Profile description
    # ------------------------------------------------------

    try:

        description_element = driver.find_element(
            By.XPATH,
            "//meta[@name='description']"
        )

        description = (
            description_element
            .get_attribute("content")
        )

        print(
            "\nRaw profile description:"
        )

        print(description)

        if description:

            # Followers
            followers_match = re.search(
                r'([\d,.]+(?:[KMB])?)\s+Followers',
                description,
                re.IGNORECASE
            )

            # Following
            following_match = re.search(
                r'([\d,.]+(?:[KMB])?)\s+Following',
                description,
                re.IGNORECASE
            )

            # Posts
            posts_match = re.search(
                r'([\d,.]+(?:[KMB])?)\s+Posts',
                description,
                re.IGNORECASE
            )

            if followers_match:

                profile_data["followers"] = (
                    convert_number(
                        followers_match.group(1)
                    )
                )

            if following_match:

                profile_data["following"] = (
                    convert_number(
                        following_match.group(1)
                    )
                )

            if posts_match:

                profile_data["posts_count"] = (
                    convert_number(
                        posts_match.group(1)
                    )
                )

    except Exception as e:

        print(
            f"Profile description error: {e}"
        )

    # ------------------------------------------------------
    # Name
    # ------------------------------------------------------

    try:

        title = driver.find_element(
            By.XPATH,
            "//meta[@property='og:title']"
        ).get_attribute("content")

        if title:

            profile_data["name"] = title

    except Exception:

        pass

    # ------------------------------------------------------
    # Bio
    # ------------------------------------------------------

    try:

        header = driver.find_element(
            By.XPATH,
            "//header"
        )

        header_text = header.text

        if header_text:

            profile_data["bio"] = header_text

    except Exception as e:

        print(
            f"Bio not found: {e}"
        )

    # ------------------------------------------------------
    # Verified
    # ------------------------------------------------------

    try:

        verified_elements = driver.find_elements(
            By.XPATH,
            "//*[@aria-label and "
            "contains(translate(@aria-label,"
            "'VERIFIED','verified'),'verified')]"
        )

        if verified_elements:

            profile_data["verified"] = True

    except Exception:

        pass

    return profile_data


# ==========================================================
# GET POST URLS
# ==========================================================

def get_posts(driver, username):

    post_elements = driver.find_elements(
        By.XPATH,
        "//a[contains(@href, '/p/') or "
        "contains(@href, '/reel/')]"
    )

    urls = set()

    for element in post_elements:

        url = element.get_attribute(
            "href"
        )

        if not url:
            continue

        # Remove query parameters
        url = url.split("?")[0]

        # Only collect posts belonging to
        # requested username
        username_path = f"/{username}/"

        if (
            username_path in url
            and (
                "/p/" in url
                or "/reel/" in url
            )
        ):

            urls.add(url)

    return urls


# ==========================================================
# COLLECT POST URLS WITH SCROLLING
# ==========================================================

def collect_post_urls(
    driver,
    username,
    target_posts=12
):

    profile_url = (
        f"https://www.instagram.com/"
        f"{username}/"
    )

    print(
        "\nOpening profile:"
    )

    print(profile_url)

    driver.get(profile_url)

    WebDriverWait(
        driver,
        15
    ).until(
        EC.presence_of_element_located(
            (By.TAG_NAME, "body")
        )
    )

    time.sleep(2)

    # ------------------------------------------------------
    # Check login redirect
    # ------------------------------------------------------

    if "accounts/login" in driver.current_url:

        print(
            "Instagram requires login."
        )

        return []

    # ------------------------------------------------------
    # Variables
    # ------------------------------------------------------

    all_urls = set()

    previous_count = 0

    no_change_count = 0

    # ------------------------------------------------------
    # Scroll
    # ------------------------------------------------------

    while len(all_urls) < target_posts:

        current_urls = get_posts(
            driver,
            username
        )

        # Keep all URLs collected across scrolling
        all_urls.update(
            current_urls
        )

        current_count = len(
            all_urls
        )

        print(
            f"Posts found: "
            f"{current_count}/{target_posts}"
        )

        # --------------------------------------------------
        # Target reached
        # --------------------------------------------------

        if current_count >= target_posts:

            print(
                "\nTarget number of posts reached."
            )

            break

        # --------------------------------------------------
        # Check if new posts loaded
        # --------------------------------------------------

        if current_count == previous_count:

            no_change_count += 1

        else:

            no_change_count = 0

        # --------------------------------------------------
        # Stop after multiple unsuccessful scrolls
        # --------------------------------------------------

        if no_change_count >= 5:

            print(
                "\nNo additional posts are loading."
            )

            break

        previous_count = current_count

        # --------------------------------------------------
        # Scroll down
        # --------------------------------------------------

        driver.execute_script(
            "window.scrollTo("
            "0, document.body.scrollHeight"
            ");"
        )

        # time.sleep(3)

    # ------------------------------------------------------
    # Convert set to list
    # ------------------------------------------------------

    post_urls = list(
        all_urls
    )

    post_urls = post_urls[
        :target_posts
    ]

    print(
        f"\nTotal post URLs collected: "
        f"{len(post_urls)}"
    )

    return post_urls


# ==========================================================
# META CONTENT
# ==========================================================

def get_meta_content(
    driver,
    property_name
):

    try:

        element = driver.find_element(
            By.XPATH,
            f"//meta[@property='{property_name}']"
        )

        return element.get_attribute(
            "content"
        )

    except Exception:

        return None


# ==========================================================
# GET CAPTION / DESCRIPTION
# ==========================================================

def get_caption(driver):

    # Try Open Graph description
    description = get_meta_content(
        driver,
        "og:description"
    )

    if description:

        return description

    # Try normal meta description
    try:

        element = driver.find_element(
            By.XPATH,
            "//meta[@name='description']"
        )

        description = (
            element.get_attribute(
                "content"
            )
        )

        if description:

            return description

    except Exception:

        pass

    return None


# ==========================================================
# CONVERT INSTAGRAM NUMBERS
# ==========================================================

def convert_number(value):

    if value is None:

        return None

    value = value.strip().replace(
        ",",
        ""
    )

    try:

        # 12K
        if value.upper().endswith("K"):

            return int(
                float(
                    value[:-1]
                ) * 1_000
            )

        # 1.5M
        elif value.upper().endswith("M"):

            return int(
                float(
                    value[:-1]
                ) * 1_000_000
            )

        # 2B
        elif value.upper().endswith("B"):

            return int(
                float(
                    value[:-1]
                ) * 1_000_000_000
            )

        # Normal number
        return int(
            float(value)
        )

    except ValueError:

        return None


# ==========================================================
# PARSE INSTAGRAM DESCRIPTION
# ==========================================================

def parse_instagram_description(
    description
):

    result = {

        "likes": None,

        "comments": None,

        "username": None,

        "date": None,

        "caption": None

    }

    if not description:

        return result

    # ------------------------------------------------------
    # Likes
    # ------------------------------------------------------

    likes_match = re.search(
        r'([\d,.]+(?:[KMB])?)\s+likes?',
        description,
        re.IGNORECASE
    )

    if likes_match:

        result["likes"] = convert_number(
            likes_match.group(1)
        )

    # ------------------------------------------------------
    # Comments
    # ------------------------------------------------------

    comments_match = re.search(
        r'([\d,.]+(?:[KMB])?)\s+comments?',
        description,
        re.IGNORECASE
    )

    if comments_match:

        result["comments"] = convert_number(
            comments_match.group(1)
        )

    # ------------------------------------------------------
    # Username
    # ------------------------------------------------------

    username_match = re.search(
        r'comments\s*-\s*([A-Za-z0-9_.]+)\s+on\s+',
        description,
        re.IGNORECASE
    )

    if username_match:

        result["username"] = (
            username_match.group(1)
        )

    # ------------------------------------------------------
    # Date
    # ------------------------------------------------------

    date_match = re.search(
        r'\bon\s+(.+?):\s*',
        description,
        re.IGNORECASE
    )

    if date_match:

        result["date"] = (
            date_match.group(1).strip()
        )

    # ------------------------------------------------------
    # Caption
    # ------------------------------------------------------

    caption_match = re.search(
        r':\s*"(.*)"\.\s*$',
        description,
        re.DOTALL
    )

    if caption_match:

        result["caption"] = (
            caption_match.group(1).strip()
        )

    else:

        # Fallback
        parts = description.split(
            ":",
            1
        )

        if len(parts) == 2:

            result["caption"] = (
                parts[1].strip()
            )

    return result


# ==========================================================
# SCRAPE INDIVIDUAL POST
# ==========================================================

def scrape_post(
    driver,
    post_url
):

    print(
        "\nOpening post:"
    )

    print(post_url)

    driver.get(post_url)

    WebDriverWait(
        driver,
        15
    ).until(
        EC.presence_of_element_located(
            (By.TAG_NAME, "body")
        )
    )

    time.sleep(2)

    # ------------------------------------------------------
    # Post type
    # ------------------------------------------------------

    if "/reel/" in post_url:

        post_type = "reel"

    else:

        post_type = "post"

    # ------------------------------------------------------
    # Initial data
    # ------------------------------------------------------

    post_data = {

        "platform": "instagram",

        "post_url": post_url,

        "post_type": post_type,

        "date": None,

        "caption": None,

        "likes": None,

        "comments": None,

    }

    # ------------------------------------------------------
    # Get description
    # ------------------------------------------------------

    try:

        description = get_caption(
            driver
        )

    except Exception as e:

        print(
            f"Description error: {e}"
        )

        description = None

    # ------------------------------------------------------
    # Parse description
    # ------------------------------------------------------

    parsed_data = (
        parse_instagram_description(
            description
        )
    )

    post_data["date"] = (
        parsed_data["date"]
    )

    post_data["caption"] = (
        parsed_data["caption"]
    )

    post_data["likes"] = (
        parsed_data["likes"]
    )

    post_data["comments"] = (
        parsed_data["comments"]
    )

    return post_data


# ==========================================================
# SAVE JSON
# ==========================================================

def save_json(
    data,
    username
):

    filename = (
        f"{username}_instagram_data.json"
    )

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

    print(
        "\nData saved to:"
    )

    print(filename)


# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    # ------------------------------------------------------
    # Username
    # ------------------------------------------------------

    username = input(
        "Enter Instagram username: "
    ).strip().replace("@", "")

    if not username:

        print(
            "Username cannot be empty."
        )

        exit()

    # ------------------------------------------------------
    # Number of posts
    # ------------------------------------------------------

    target = input(
        "Number of posts to collect "
        "(default 12): "
    ).strip()

    if target:

        try:

            target_posts = int(
                target
            )

        except ValueError:

            print(
                "Please enter a valid number."
            )

            exit()

    else:

        target_posts = 12

    # ------------------------------------------------------
    # Start browser
    # ------------------------------------------------------

    driver = prepare_browser()

    try:

        # --------------------------------------------------
        # Login
        # --------------------------------------------------

        logged_in = login_if_required(
            driver
        )

        if not logged_in:

            print(
                "Could not establish "
                "an Instagram session."
            )

            exit()

        # --------------------------------------------------
        # Get profile
        # --------------------------------------------------

        profile_data = get_profile(
            driver,
            username
        )

        # --------------------------------------------------
        # Print profile information
        # --------------------------------------------------

        print(
            "\n"
            + "=" * 60
        )

        print(
            "PROFILE INFORMATION"
        )

        print(
            "=" * 60
        )

        print(
            f"Username:   "
            f"{profile_data['username']}"
        )

        print(
            f"Name:       "
            f"{profile_data['name']}"
        )

        print(
            f"Followers:  "
            f"{profile_data['followers']}"
        )

        print(
            f"Following:  "
            f"{profile_data['following']}"
        )

        print(
            f"Posts:      "
            f"{profile_data['posts_count']}"
        )

        print(
            f"Verified:   "
            f"{profile_data['verified']}"
        )

        print(
            f"Bio:        "
            f"{profile_data['bio']}"
        )

        print(
            "=" * 60
        )

        # --------------------------------------------------
        # Collect post URLs
        # --------------------------------------------------

        post_urls = collect_post_urls(
            driver,
            username,
            target_posts
        )

        if not post_urls:

            print(
                "\nNo posts were found."
            )

            exit()

        print(
            "\n"
            + "=" * 60
        )

        print(
            "POST URL COLLECTION COMPLETE"
        )

        print(
            "=" * 60
        )

        print(
            f"Posts found: "
            f"{len(post_urls)}"
        )

        # --------------------------------------------------
        # Scrape individual posts
        # --------------------------------------------------

        all_posts = []

        for index, post_url in enumerate(
            post_urls,
            start=1
        ):

            print(
                "\n"
                + "=" * 60
            )

            print(
                f"Scraping post "
                f"{index}/{len(post_urls)}"
            )

            print(
                "=" * 60
            )

            try:

                post_data = scrape_post(
                    driver,
                    post_url
                )

                # Add username
                post_data["username"] = (
                    username
                )

                all_posts.append(
                    post_data
                )

                print(
                    "\nCollected:"
                )

                print(
                    f"Type:       "
                    f"{post_data['post_type']}"
                )

                print(
                    f"Date:       "
                    f"{post_data['date']}"
                )

                print(
                    f"Likes:      "
                    f"{post_data['likes']}"
                )

                print(
                    f"Comments:   "
                    f"{post_data['comments']}"
                )

                print(
                    f"Caption:    "
                    f"{post_data['caption']}"
                )

            except Exception as e:

                print(
                    "\nError scraping post:"
                )

                print(e)

        # --------------------------------------------------
        # Final data structure
        # --------------------------------------------------

        data = {

            "platform": "instagram",

            "username": username,

            "profile_url": (
                f"https://www.instagram.com/"
                f"{username}/"
            ),

            "profile": profile_data,

            "posts_count": len(
                all_posts
            ),

            "posts": all_posts

        }

        # --------------------------------------------------
        # Summary
        # --------------------------------------------------

        print(
            "\n"
            + "=" * 60
        )

        print(
            "SCRAPING COMPLETE"
        )

        print(
            "=" * 60
        )

        print(
            f"Username: "
            f"{username}"
        )

        print(
            f"Posts collected: "
            f"{len(all_posts)}"
        )

        # --------------------------------------------------
        # Save JSON
        # --------------------------------------------------

        save_json(
            data,
            username
        )

    finally:

        driver.quit()