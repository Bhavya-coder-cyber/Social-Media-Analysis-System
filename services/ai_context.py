from services.analytics import summary, sentiment_summary, insights
def build_ai_context(analyses):
    if not analyses:
        raise ValueError("Analyses list cannot be empty")

    prepared_analyses = []
    all_platforms = set()

    for analysis in analyses:
        records = analysis.get("records", [])
        if not records:
            continue  # Skip analyses with no records

        platforms = sorted({
            record.get("platform") for record in records if record.get("platform")
        })
        platform_records = {
            platform: [
                record for record in records
                if record.get("platform") == platform
                and not record.get("is_profile_snapshot")
            ]
            for platform in platforms
        }
        creators = sorted({
            (record.get("platform"), record.get("username")) for record in records if record.get("username")
        })
        all_platforms.update(platforms)

        dates = sorted({
            record.get("date") for record in records if record.get("date")
        })

        snapshot_records = [
            record for record in records 
            if record.get("is_profile_snapshot")
        ]

        prepared_analyses.append({
            "run_id": analysis.get("run_id"),
            "source_ref": analysis.get("source_ref", ""),

            "platforms": platforms,
            "creators": [
                {
                    "platform": platform,
                    "username": username
                }
                for platform, username in creators
            ],

            "date_range": {
                "start": dates[0] if dates else None,
                "end": dates[-1] if dates else None
            },

            "platform_analytics": {
                platform: {
                    "summary": summary(platform_records[platform]),
                    "sentiment": sentiment_summary(platform_records[platform]),
                    "content_insights": insights(platform_records[platform])
                }
                for platform in platforms
            },
            "historical_data": { #Used for forecasting and trend analysis
                platform: [
                    {
                        "date": record.get("date"),
                        "views": record.get("views", 0),
                        "interactions": record.get("interactions", 0),
                        "likes": record.get("likes", 0),
                        "comments": record.get("comments", 0),
                        "shares": record.get("shares", 0),
                        "engagement_rate": record.get("engagement_rate", 0)
                    }
                    for record in platform_records[platform]
                    if record.get("date")
                ]
                for platform in platforms
            },
            
            "data_quality": {
                platform: {
                    "total_records": len(platform_records[platform]),

                    "profile_snapshots": len([
                        r for r in records
                        if r.get("platform") == platform
                        and r.get("is_profile_snapshot")
                    ]),

                    "has_date_information": any(
                        r.get("date")
                        for r in platform_records[platform]
                    ),

                    "confidence": calculate_confidence(
                        platform_records[platform]
                    ),

                    "metric_completeness": {
                        metric: {
                            "available": sum(
                                1 for r in platform_records[platform]
                                if r.get("metric_availability", {}).get(metric, False)
                            ),
                            "missing": sum(
                                1 for r in platform_records[platform]
                                if not r.get("metric_availability", {}).get(metric, False)
                            )
                        }
                        for metric in [
                            "views", "likes", "comments", "shares"
                        ]
                    }
                }
                for platform in platforms
            }

        })

        # This section must be OUTSIDE the for loop

    if not prepared_analyses:
        raise ValueError("No valid analyses with records found")

    mode = (
        "individual" if len(prepared_analyses) == 1 else "comparative"
    )

    return {
        "analysis_mode": mode,
        "selected_analysis_count": len(prepared_analyses),
        "platforms": sorted(all_platforms),
        "analyses": prepared_analyses
    }


def calculate_confidence(records):
    total_records = len(records)

    if total_records < 20:
        return "Low"

    dated_records = [
        record for record in records
        if record.get("date")
    ]

    if not dated_records:
        return "Low"

    required_metrics = [
        "views", "likes", "comments", "interactions"
    ]

    available_metrics = sum(
        1
        for record in records
        for metric in required_metrics
        if record.get(metric) is not None
    )

    total_metrics = total_records * len(required_metrics)

    completeness = available_metrics / total_metrics

    if completeness < 0.70:
        return "Low"

    if total_records >= 50 and completeness >= 0.90:
        return "High"

    return "Medium"
