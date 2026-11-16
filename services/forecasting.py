from collections import defaultdict
from datetime import datetime
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.ensemble import GradientBoostingRegressor
from xgboost import XGBRegressor

def create_lag_features(values, lookback=3):
    X = []
    y = []

    for i in range(lookback, len(values)):
        X.append(values[i-lookback:i])
        y.append(values[i])

    return np.array(X), np.array(y)



def prepare_historical_data(historical_data):

    daily_data = defaultdict(lambda: {
        "views": [],
        "interactions": [],
        "engagement_rate": []
    })

    for record in historical_data:
        platform = record.get("platform")
        date_value = record.get("date")

        if not platform or not date_value:
            continue

        try:
            date = datetime.fromisoformat(
                date_value.replace("Z", "+00:00")
            ).date()
        except (ValueError, TypeError, AttributeError):
            continue

        key = (platform, str(date))

        daily_data[key]["views"].append(
            record.get("views") or 0
        )

        daily_data[key]["interactions"].append(
            record.get("interactions") or 0
        )

        daily_data[key]["engagement_rate"].append(
            record.get("engagement_rate") or 0
        )

    result = []

    for (platform, date), metrics in sorted(daily_data.items()):

        result.append({
            "platform": platform,
            "date": date,
            "posts": len(metrics["views"]),
            "total_views": sum(metrics["views"]),
            "total_interactions": sum(metrics["interactions"]),
            "average_engagement_rate": (
                sum(metrics["engagement_rate"])
                / len(metrics["engagement_rate"])
            )
        })

    return result

# def forecast_metric(daily_data, metric, periods=7):
#     if len(daily_data) < 3:
#         raise ValueError("Not enough data points to perform forecasting")
#     if metric not in daily_data[0]:
#         raise ValueError(f"Invalid metric: {metric}")

#     values = np.array([
#         float(items[metric])
#         for items in daily_data
#     ])

#     X = np.arange(len(values)).reshape(-1, 1)
#     y = values

#     model = LinearRegression()
#     model.fit(X, y)

#     future_X = np.arange(len(values), len(values) + periods).reshape(-1, 1)

#     future_predictions = model.predict(future_X)
#     future_predictions = np.maximum(future_predictions, 0)
#     slope = model.coef_[0]
#     if slope > 0:
#         trend = "increasing"
#     elif slope < 0:
#         trend = "decreasing"
#     else:
#         trend = "stable"

#     return {
#         "metric": metric,
#         "historical_observations": len(values),
#         "trend": trend,
#         "slope": round(float(slope), 2),
#         "forecast": [
#             {
#                 "period": i + 1,
#                 "predicted_value": round(float(value), 2)
#             }
#             for i, value in enumerate(future_predictions)
#         ]
#     }

def forecast_metric(daily_data, metric, periods=7):

    # if len(daily_data) < 4:
    #     raise ValueError(
    #         "Not enough data points to perform forecasting"
    #     )
    
    if len(daily_data) < 10:
        raise ValueError(
            "Not enough data points to perform forecasting. "
            "At least 10 data points are required."
        )

    if metric not in daily_data[0]:
        raise ValueError(f"Invalid metric: {metric}")

    values = np.array([
        float(item[metric])
        for item in daily_data
    ])

    lookback = 3

    X, y = create_lag_features(values, lookback)

    # model = RandomForestRegressor(
    #     n_estimators=200,
    #     max_depth=5,
    #     min_samples_split=2,
    #     min_samples_leaf=2,
    #     max_features=1.0,
    #     random_state=42,
    #     n_jobs=-1
    # )

    # model = GradientBoostingRegressor(
    #     n_estimators=100,
    #     learning_rate=0.05,
    #     max_depth=2,
    #     min_samples_split=2,
    #     min_samples_leaf=2,
    #     random_state=42
    # )

    model = XGBRegressor(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=3,
        min_child_weight=2,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1
    )

    model.fit(X, y)

    history = list(values)
    future_predictions = []

    for _ in range(periods):

        features = np.array(
            history[-lookback:]
        ).reshape(1, -1)

        prediction = model.predict(features)[0]
        prediction = max(float(prediction), 0)

        future_predictions.append(prediction)
        history.append(prediction)

    slope = (
        future_predictions[-1] - future_predictions[0]
    ) / max(periods - 1, 1)

    if slope > 0:
        trend = "increasing"
    elif slope < 0:
        trend = "decreasing"
    else:
        trend = "stable"

    return {
        "metric": metric,
        "historical_observations": len(values),
        "trend": trend,
        "slope": round(float(slope), 2),
        "forecast": [
            {
                "period": i + 1,
                "predicted_value": round(value, 2)
            }
            for i, value in enumerate(future_predictions)
        ]
    }

#For measuring the accuracy of the forecast, we can use metrics like Mean Absolute Error (MAE) or Root Mean Squared Error (RMSE). These metrics compare the predicted values against the actual values to quantify the accuracy of the forecast. The lower the error, the more accurate the forecast is considered to be.
def evaluate_forecast(actual_values, predicted_values):

    if len(actual_values) != len(predicted_values):
        raise ValueError(
            "Actual and predicted values must have equal lengths."
        )

    if not actual_values:
        raise ValueError("No values available for evaluation.")

    mae = mean_absolute_error(
        actual_values,
        predicted_values
    )

    rsme = np.sqrt(
        mean_squared_error(
            actual_values,
            predicted_values
        )
    )

    return {
        "mae": round(float(mae), 2),
        "rmse": round(float(rsme), 2),
        "observations": len(actual_values)
    }

#Creating evaluate_model function to evaluate the model's performance on a test set of 80/20 split of the data. The function takes in the daily_data, metrics to evaluate, and test_ratio (default is 0.2 for 80/20 split). It returns a dictionary containing the evaluation results for each metric.
# def evaluate_model(daily_data, metric, test_ratio=0.2):
#     sorted_data = sorted(
#         daily_data,
#         key=lambda item: item["date"]
#     )
#     if len(sorted_data) < 5:
#         raise ValueError("Not enough data points to evaluate the model.")
#     platforms = {
#         item.get("platform")
#         for item in sorted_data
#         if item.get("platform")
#     }

#     if len(platforms) > 1:
#         raise ValueError(
#             "Evaluation is only supported for a single platform."
#         )

#     if not 0 < test_ratio < 1:
#         raise ValueError("Test ratio must be between 0 and 1.")

#     values = np.array([
#         float(item[metric])
#         for item in sorted_data
#     ])
#     X = np.arange(len(values)).reshape(-1, 1)

#     split_index = int(len(values) * (1 - test_ratio))
#     split_index = max(3, min(split_index, len(values) - 1))

#     X_train, X_test = X[:split_index], X[split_index:]
#     y_train, y_test = values[:split_index], values[split_index:]

#     model = LinearRegression()
#     model.fit(X_train, y_train)

#     predictions = np.maximum(
#         model.predict(X_test), 0
#     )
#     mae = mean_absolute_error(y_test, predictions)
#     rmse = np.sqrt(mean_squared_error(y_test, predictions))

#     return {
#         "metric": metric,
#         "training_observations": len(y_train),
#         "testing_observations": len(y_test),
#         "mae": round(float(mae), 2),
#         "rmse": round(float(rmse), 2),
#         "actual": y_test.tolist(),
#         "predicted": predictions.round(2).tolist()
#     }

def evaluate_model(daily_data, metric, test_ratio=0.2):

    sorted_data = sorted(
        daily_data,
        key=lambda item: item["date"]
    )

    if len(sorted_data) < 5:
        raise ValueError(
            "Not enough data points to evaluate the model."
        )

    platforms = {
        item.get("platform")
        for item in sorted_data
        if item.get("platform")
    }

    if len(platforms) > 1:
        raise ValueError(
            "Evaluation is only supported for a single platform."
        )

    if not 0 < test_ratio < 1:
        raise ValueError("Test ratio must be between 0 and 1.")

    values = np.array([
        float(item[metric])
        for item in sorted_data
    ])

    lookback = 3

    X, y = create_lag_features(values, lookback)

    split_index = int(len(values) * (1 - test_ratio))
    split_index = max(lookback + 1, min(
        split_index, len(values) - 1
    ))

    train_end = split_index - lookback

    X_train = X[:train_end]
    y_train = y[:train_end]

    actual = []
    predictions = []

    # model = RandomForestRegressor(
    #     n_estimators=200,
    #     max_depth=5,
    #     min_samples_split=2,
    #     min_samples_leaf=2,
    #     max_features=1.0,
    #     random_state=42,
    #     n_jobs=-1
    # )

    # model = GradientBoostingRegressor(
    #     n_estimators=100,
    #     learning_rate=0.05,
    #     max_depth=2,
    #     min_samples_split=2,
    #     min_samples_leaf=2,
    #     random_state=42
    # )

    model = XGBRegressor(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=3,
        min_child_weight=2,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    history = list(values[:split_index])

    for i in range(split_index, len(values)):

        features = np.array(
            history[-lookback:]
        ).reshape(1, -1)

        prediction = model.predict(features)[0]
        prediction = max(float(prediction), 0)

        predictions.append(prediction)
        actual.append(values[i])

        # Walk-forward evaluation:
        # use the actual observation for the next prediction.
        history.append(values[i])

    mae = mean_absolute_error(actual, predictions)
    rmse = np.sqrt(
        mean_squared_error(actual, predictions)
    )
    
    return {
        "metric": metric,
        "training_observations": len(y_train),
        "testing_observations": len(actual),
        "mae": round(float(mae), 2),
        "rmse": round(float(rmse), 2),
        "actual": np.array(actual).tolist(),
        "predicted": np.round(predictions, 2).tolist()
    }

def forecast_all_metrics(historical_data, periods=7):
    daily_data = prepare_historical_data(historical_data)

    metrics = [
        "total_views",
        "total_interactions",
        "average_engagement_rate"
    ]
    results = {}
    platforms = sorted({
        item["platform"] for item in daily_data
    })
    for platform in platforms:
        platform_data = [
            item for item in daily_data
            if item["platform"] == platform
        ]
        results[platform] = {}

        for metric in metrics:
            try:
                results[platform][metric] = forecast_metric(
                    platform_data,
                    metric=metric,
                    periods=periods
                )
            except ValueError as error:
                results[platform][metric] = {
                    "available": False,
                    "reason": str(error)
                }

    return results
