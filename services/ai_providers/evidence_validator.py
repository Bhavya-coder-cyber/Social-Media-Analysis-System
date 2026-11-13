from datetime import datetime
import re

def calculate_posting_time_evidence(records):
    day_stats = {}
    hour_stats = {}

    for record in records:
        date_value = record.get("date")

        if not date_value:
            continue

        try:
            date = datetime.fromisoformat(
                date_value.replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            continue

        day = date.strftime("%A")
        hour = date.hour
        interactions = record.get("interactions", 0) or 0

        if day not in day_stats:
            day_stats[day] = []

        if hour not in hour_stats:
            hour_stats[hour] = []

        day_stats[day].append(interactions)
        hour_stats[hour].append(interactions)

    return {
        "days": {
            day: {
                "posts": len(values),
                "avg_interactions": sum(values) / len(values)
            }
            for day, values in day_stats.items()
            if len(values) >= 3
        },
        "hours": {
            hour: {
                "posts": len(values),
                "avg_interactions": sum(values) / len(values)
            }
            for hour, values in hour_stats.items()
            if len(values) >= 3
        }
    }

def calculate_day_hour_evidence(records):

    combinations = {}

    for record in records:
        date_value = record.get("date")

        if not date_value:
            continue

        try:
            date = datetime.fromisoformat(
                date_value.replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            continue

        day = date.strftime("%A")
        hour = date.hour
        key = (day, hour)

        if key not in combinations:
            combinations[key] = []

        combinations[key].append(
            record.get("interactions", 0) or 0
        )

    return {
        f"{day}_{hour}": {
            "day": day,
            "hour": hour,
            "posts": len(values),
            "avg_interactions": sum(values) / len(values)
        }
        for (day, hour), values in combinations.items()
    }

def validate_posting_time_recommendations(ai_result, context):
    for analysis in context.get("analyses", []):
        for platform, records in analysis.get("historical_data", {}).items():

            evidence = calculate_posting_time_evidence(records)
            combination_evidence = calculate_day_hour_evidence(records)

            for platform_insight in ai_result.get("platform_insights", []):
                if platform_insight.get("platform", "").lower() != platform.lower():
                    continue

                # Validate posting days in weekly plan
                for item in platform_insight.get("weekly_plan", []):
                    day = item.get("day", "").strip().capitalize()

                    if day not in evidence["days"]:
                        item["task"] = (
                            f"{item.get('task', '')} "
                            "Note: No sufficient historical posting data "
                            f"supports a recommendation for {day}."
                        )

                # Validate posting hours in growth tips
                for tip in platform_insight.get("growth_tips", []):
                    text = (
                        tip.get("action", "") + " " +
                        tip.get("explanation", "")
                    )

                    import re

                    times = re.findall(
                        r"\b(1[0-2]|0?[1-9])\s*(AM|PM)\b",
                        text,
                        re.IGNORECASE
                    )

                    for hour_text, period in times:
                        hour = int(hour_text) % 12

                        if period.upper() == "PM":
                            hour += 12

                        if hour not in evidence["hours"]:
                            tip["explanation"] = (
                                tip.get("explanation", "") +
                                f" Historical data does not provide "
                                f"sufficient evidence for {hour_text} "
                                f"{period.upper()}."
                            )
                    # Validate day-hour combinations
                    day_names = re.findall(
                        r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)s?\b",
                        text,
                        re.IGNORECASE
                    )

                    unsupported_combinations = []

                    for day in day_names:
                        day = day.capitalize()

                        for hour_text, period in times:
                            hour = int(hour_text) % 12

                            if period.upper() == "PM":
                                hour += 12

                            key = f"{day}_{hour}"
                            combination = combination_evidence.get(key)

                            if not combination or combination["posts"] < 3:
                                unsupported_combinations.append(
                                    f"{day} at {hour_text} {period.upper()}"
                                )

                    if unsupported_combinations:
                        tip["evidence_status"] = "insufficient"
                        tip["explanation"] += (
                            " These day-time combinations lack sufficient evidence: "
                            + ", ".join(unsupported_combinations) + "."
                        )
                    else:
                        tip["evidence_status"] = "supported"

    return ai_result

def validate_hashtag_recommendations(ai_result, context):
    # Build a lookup of hashtag evidence by platform
    hashtag_evidence = {}

    for analysis in context.get("analyses", []):
        platform_analytics = analysis.get("platform_analytics", {})

        for platform, analytics in platform_analytics.items():
            content_insights = analytics.get("content_insights", {})
            top_hashtags = content_insights.get("top_hashtags", [])

            hashtag_evidence[platform.lower()] = {
                item.get("tag", "").lower().strip(): item
                for item in top_hashtags
                if item.get("tag")
            }

    # Validate each platform's hashtag recommendations
    for platform_insight in ai_result.get("platform_insights", []):
        platform = platform_insight.get("platform", "").lower()
        evidence = hashtag_evidence.get(platform, {})

        for recommendation in platform_insight.get(
            "hashtag_recommendations", []
        ):
            if not isinstance(recommendation, dict):
                continue

            hashtag = recommendation.get("hashtag", "").lower().strip()
            hashtag = hashtag if hashtag.startswith("#") else f"#{hashtag}"

            data = evidence.get(hashtag)

            if not data:
                recommendation["reason"] = (
                    "This hashtag is not present in the available "
                    "hashtag summary, so its performance is unverified."
                )
                continue

            post_count = data.get("posts", 0)
            avg_interactions = data.get("avg_interactions")

            if post_count < 3:
                recommendation["reason"] = (
                    f"This hashtag appeared in only {post_count} analyzed "
                    "post(s). The sample is too small to establish "
                    "consistent performance."
                )
            else:
                reason = (
                    f"This hashtag appeared in {post_count} analyzed posts. "
                )

                if avg_interactions is not None:
                    reason += (
                        f"Those posts averaged {avg_interactions:.1f} "
                        "interactions. This is an observed association, "
                        "not proof that the hashtag caused higher engagement."
                    )
                else:
                    reason += (
                        "This shows usage frequency, not proof of "
                        "higher engagement."
                    )

                recommendation["reason"] = reason

    return ai_result

if __name__ == "__main__":
    import json
    from pathlib import Path

    target_run_id = "fdb984541ff6"
    records = []

    for file_path in Path("storage/instagram").glob("*.json"):
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if data.get("run_id") == target_run_id:
            records = data.get("records", [])
            break

    if not records:
        print("Analysis not found or no records available.")
    else:
        result = calculate_day_hour_evidence(records)

        print("\nDAY-HOUR EVIDENCE")
        print(json.dumps(result, indent=4))