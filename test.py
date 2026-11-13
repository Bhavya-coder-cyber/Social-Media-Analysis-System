from services.forecasting import forecast_all_metrics

historical_data = [
    {
        "platform": "instagram",
        "date": f"2026-11-{day:02d}",
        "views": 10000 + (day - 1) * 1000,
        "interactions": 500 + (day - 1) * 50,
        "engagement_rate": 5 + (day - 1) * 0.2
    }
    for day in range(1, 6)
]

result = forecast_all_metrics(historical_data)

print(result)