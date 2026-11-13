from os import path
import os, json, uuid, glob, csv, io
from datetime import datetime, timezone
import time
from flask import Flask, jsonify, render_template, request, send_file, Response
from dotenv import load_dotenv
from services.analytics import normalize, normalize_linkedin, summary, sentiment_summary, cross, insights, PLATFORMS, sentiment
from scrapers.live import instagram, x, linkedin, youtube
from services.ai_context import build_ai_context
from services.ai_providers.openai_client import generate_insights
from services.forecasting import forecast_all_metrics
from services.forecasting import (
    prepare_historical_data,
    forecast_metric,
    evaluate_model
)

BASE=os.path.dirname(os.path.abspath(__file__))
STORAGE=os.path.join(BASE,"storage")
os.makedirs(STORAGE,exist_ok=True)
load_dotenv(os.path.join(BASE,".env"))
app=Flask(__name__,template_folder="templates",static_folder="static")
app.secret_key=os.getenv("SECRET_KEY","dev-secret")


def payload(records, source_ref="", run_id=None):
    s=summary(records); return {"run_id":run_id or uuid.uuid4().hex[:12],"created_at":datetime.now(timezone.utc).isoformat(),"source_ref":source_ref,"records":records,"summary":s,"sentiment":sentiment_summary(records),"insights":insights(records)}

def json_dump(path,data):
    with open(path,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)

def analysis_folder(records):
    platforms = {
        r.get("platform")
        for r in records
        if r.get("platform") in PLATFORMS
    }

    if len(platforms) == 1:
        return platforms.pop()

    return "cross_analysis"

def find_saved_path(run_id):
    path = os.path.basename(run_id)
    if not run_id or path != run_id:
        return None

    matches = glob.glob(
        os.path.join(STORAGE, "**", run_id + ".json"),
        recursive=True
    )

    return matches[0] if matches else None

def saved_runs():
    out=[]
    for p in glob.glob(os.path.join(STORAGE,"**","*.json"), recursive=True):
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)

            out.append({
                "run_id": d.get("run_id"),
                "created_at": d.get("created_at"),
                "platforms": sorted(set(
                    r.get("platform")
                    for r in d.get("records", [])
                    if r.get("platform")
                )),
                "posts": len(d.get("records", [])),
                "source_ref": d.get("source_ref", ""),
                "file": os.path.basename(p)
            })

        except Exception:
            pass
        
    return sorted(
        out,
        key=lambda x:x.get("created_at",""),
        reverse=True
    )

@app.get("/")
def home(): return render_template("index.html")

@app.get("/api/health")
def health():
    def configured(name, fallback):
        v=os.getenv(name, fallback).strip()
        return bool(v) and "YOUR_" not in v.upper() and "CHANGE-ME" not in v.upper()
    return jsonify({
        "apify": bool(os.getenv("APIFY_TOKEN", "").strip()),
        "youtube": bool(os.getenv("YOUTUBE_API_KEY", "").strip()),
        "platforms": list(PLATFORMS),
        "actors": {
            "instagram": configured("INSTAGRAM_ACTOR_ID", ""),
            "x": configured("X_ACTOR_ID", ""),
            "linkedin": configured("LINKEDIN_ACTOR_ID", "")
        },
        "actor_ids": {p: os.getenv(k, "") for p,k in {
            "instagram":"INSTAGRAM_ACTOR_ID","x":"X_ACTOR_ID","linkedin":"LINKEDIN_ACTOR_ID"
        }.items()}
    })

@app.post("/api/analyze/<platform>")
def analyze(platform):
    if platform not in PLATFORMS:return jsonify({"error":"Unsupported platform"}),404
    data=request.get_json(silent=True) or {}
    ref=(data.get("reference") or "").strip()
    limit=max(1,min(int(data.get("limit",25)),100))
    if not ref:return jsonify({"error":"Enter a username, handle, or profile/channel URL."}),400
    started=time.time()
    try:
        if platform=="instagram": records=instagram(ref,limit)
        elif platform=="x": records=x(ref,limit)
        elif platform=="linkedin": records=linkedin(ref,limit)
        else:
            cp=max(0,min(int(data.get("comments_per_video",0)),100)); rows,ch=youtube(ref,min(limit,50),cp)
            records=normalize("youtube",{"channel":{"title":ch.get("snippet",{}).get("title",ref),"subscribers":ch.get("statistics",{}).get("subscriberCount",0)},"items":rows},ref)[1]
            for i,p in enumerate(records):
                raw=rows[i] if i<len(rows) else {}; texts=raw.get("comments_text",[]); labels=[sentiment(t)[0] for t in texts]; p["comment_sentiment"]={"positive":labels.count("Positive"),"neutral":labels.count("Neutral"),"negative":labels.count("Negative"),"total":len(labels)}
        result=payload(records,ref)
        result["elapsed_seconds"]=round(time.time()-started,2)
        if not records:
            result["warning"]="The live connector completed but returned 0 items. Check the Actor input schema/output in Apify Console."
        return jsonify(result)
    except Exception as exc:
        msg=str(exc) or "Live analysis failed."
        return jsonify({"error":msg,"platform":platform,"reference":ref,"elapsed_seconds":round(time.time()-started,2)}),502

@app.post("/api/save")
def save():
    data=request.get_json(silent=True) or {} 
    records=data.get("records") or []
    print("PLATFORMS:", PLATFORMS)

    print("RECORD PLATFORMS:", {
        r.get("platform") for r in records
    })

    print("SELECTED FOLDER:", analysis_folder(records))
    if not records:
        return jsonify({
            "error":"Nothing to save. Run at least one live analysis first."
        }),400
    run=payload(
        records,
        data.get("source_ref",""),
        data.get("run_id")
    )
    folder = analysis_folder(records)
    directory = os.path.join(STORAGE, folder)
    os.makedirs(directory, exist_ok=True)
    path=os.path.join(directory, run["run_id"]+".json")
    json_dump(path,run)
    return jsonify({
        "ok":True,
        "run_id":run["run_id"],
        "file":os.path.basename(path),
        "created_at":run["created_at"]
    })

@app.get("/api/saved")
def saved(): 
    return jsonify(saved_runs())

@app.get("/api/saved/<run_id>")
def saved_one(run_id):
    path=find_saved_path(run_id)
    if not path:
        return jsonify({
            "error":"Saved analysis not found"
        }),404
    with open(path, encoding="utf-8") as f:
        return jsonify(json.load(f))

@app.delete("/api/saved/<run_id>")
def delete_saved(run_id):
    path=find_saved_path(run_id)

    if not path:
        return jsonify({
            "error":"Not found"
        }),404
    os.remove(path)
    return jsonify({"ok":True})

@app.post("/api/save-all")
def save_all():
    data=request.get_json(silent=True) or {} 
    records=data.get("records") or []
    if not records:
        return jsonify({
            "error":"No current analytics to save."
        }),400
    run=payload(
        records,
        "Cross-platform workspace",
        data.get("run_id")
    )
    directory = os.path.join(STORAGE, "cross_analysis")
    os.makedirs(directory, exist_ok=True)

    path = os.path.join(directory, run["run_id"] + ".json")
    json_dump(path, run)

    return jsonify({
        "ok": True,
        "run_id": run["run_id"],
        "file": os.path.basename(path)
    })
@app.get("/api/export")
def export_data():
    run_id=request.args.get("run_id","").strip()
    path=find_saved_path(run_id)
    if not path: 
        return jsonify({
            "error":"Saved analysis not found"
        }),404
    return send_file(
        path,
        as_attachment=True,
        download_name=f"social-media-analysis-{run_id}.json",
        mimetype="application/json"
    )
CSV_COLUMNS=["platform","username","name","followers","post_id","date","media_type","text","likes","comments","shares","views","interactions","engagement_rate","sentiment","compound","url"]

@app.post("/api/insights")
def insights_api():
    data = request.get_json(silent=True) or {}

    records = data.get("records") or []

    if not records:
        return jsonify({"error": "No records supplied."}), 400

    return jsonify(insights(records))

@app.post("/api/ai/context")
def ai_context_api():
    data = request.get_json(silent=True) or {}

    selected_ids = data.get("selected_ids") or []

    if not selected_ids:
        return jsonify({"error": "No analyses selected."}), 400

    try:
        analyses = []

        for run_id in selected_ids:
            path = find_saved_path(run_id)

            if not path:
                return jsonify({
                    "error": f"Saved analysis not found: {run_id}"
                }), 404

            with open(path, "r", encoding="utf-8") as file:
                analyses.append(json.load(file))

        context = build_ai_context(analyses)

        return jsonify(context)

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception as error:
        return jsonify({"error": str(error)}), 500

@app.post("/api/ai/analyze")
def ai_analyze_api():
    data = request.get_json(silent=True) or {}

    selected_ids = data.get("selected_ids") or []

    if not selected_ids:
        return jsonify({"error": "No analyses selected."}), 400

    try:
        analyses = []

        for run_id in selected_ids:
            path = find_saved_path(run_id)

            if not path:
                return jsonify({
                    "error": f"Saved analysis not found: {run_id}"
                }), 404

            with open(path, "r", encoding="utf-8") as file:
                analyses.append(json.load(file))

        # Prepare standardized analytics context
        context = build_ai_context(analyses)

        # Generate insights using OpenAI
        ai_result = generate_insights(context)

        return jsonify({
            "success": True,
            "provider": "openai",
            "insights": ai_result
        })

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception as error:
        return jsonify({"error": str(error)}), 500


@app.post("/api/forecast")
def forecast_api():
    data = request.get_json(silent=True) or {}
    selected_ids = data.get("selected_ids") or []

    if not selected_ids:
        return jsonify({"error": "No analyses selected."}), 400

    try:
        analyses = []

        # Load selected saved analyses
        for run_id in selected_ids:
            saved_path = find_saved_path(run_id)

            if not saved_path:
                return jsonify({
                    "error": f"Saved analysis not found: {run_id}"
                }), 404

            with open(saved_path, "r", encoding="utf-8") as file:
                analyses.append(json.load(file))

        # Collect records separately by platform
        platform_records = {}

        for analysis in analyses:
            for record in analysis.get("records", []):
                if record.get("is_profile_snapshot"):
                    continue

                platform = record.get("platform")

                if not platform:
                    continue

                platform_records.setdefault(platform, []).append(record)

        forecast_results = {}

        # Generate forecasts independently for each platform
        for platform, records in platform_records.items():

            daily_data = prepare_historical_data(records)

            platform_forecasts = {}

            metrics = [
                "total_views",
                "total_interactions",
                "average_engagement_rate"
            ]

            for metric in metrics:
                try:
                    forecast_result = forecast_metric(
                        daily_data,
                        metric=metric,
                        periods=7
                    )

                    forecast_result["historical"] = [
                        {
                            "date": item["date"],
                            "value": item[metric]
                        }
                        for item in daily_data
                    ]

                    platform_forecasts[metric] = forecast_result

                except ValueError as error:
                    platform_forecasts[metric] = {
                        "available": False,
                        "reason": str(error)
                    }

            forecast_results[platform] = {
                "historical_observations": len(daily_data),
                "forecasts": platform_forecasts
            }

        return jsonify({
            "success": True,
            "forecast_periods": 7,
            "platforms": forecast_results,
            "follower_forecast": {
                "available": False,
                "reason": "Historical follower snapshots are required."
            }
        })

    except Exception as error:
        return jsonify({"error": str(error)}), 500

    
@app.post("/api/export-csv")
def export_csv():
    data=request.get_json(silent=True) or {}
    records=data.get("records") or []
    if not records: return jsonify({"error":"Nothing to export. Run an analysis first."}),400
    buf=io.StringIO()
    w=csv.DictWriter(buf,fieldnames=CSV_COLUMNS,extrasaction="ignore")
    w.writeheader()
    for r in records:
        row={k:r.get(k,"") for k in CSV_COLUMNS}
        row["text"]=(row.get("text") or "").replace("\n"," ").strip()
        w.writerow(row)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return Response(buf.getvalue(),mimetype="text/csv",
        headers={"Content-Disposition":f"attachment; filename=social-media-analysis-{stamp}.csv"})

@app.get("/api/ai/forecast")
def ai_forecast_api():
    data = request.get_json(silent=True) or {}
    selected_ids = data.get("selected_ids") or []
    if not selected_ids:
        return jsonify({"error": "No analyses selected."}), 400

    try:
        records = []

        # Load selected saved analyses
        for run_id in selected_ids:
            path = find_saved_path(run_id)

            if not path:
                return jsonify({
                    "error": f"Saved analysis not found: {run_id}"
                }), 404

            with open(path, "r", encoding="utf-8") as file:
                analysis = json.load(file)

            records.extend(analysis.get("records", []))

        if not records:
            return jsonify({"error": "No records found."}), 400

        # Keep the current follower count as profile context
        platform_followers = {}

        for record in records:
            platform = record.get("platform")
            followers = record.get("followers") or 0

            if platform:
                platform_followers[platform] = max(
                    platform_followers.get(platform, 0),
                    followers
                )

        # Generate numerical forecasts
        forecasts = forecast_all_metrics(records, periods=7)

        return jsonify({
            "success": True,
            "forecasts": forecasts,
            "current_followers": platform_followers
        })

    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    except Exception as error:
        return jsonify({"error": str(error)}), 500


@app.get("/api/cross")
def cross_api():
    records=[]
    paths = glob.glob(os.path.join(STORAGE,"*.json"))
    for platform in PLATFORMS:
        paths += glob.glob(
            os.path.join(STORAGE, platform, "*.json")
        )
    for p in paths:
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            saved_records = data.get("records", [])
            if os.path.dirname(p) == STORAGE:
                platforms = {
                    r.get("platform")
                    for r in saved_records
                    if r.get("platform")
                }

                if len(platforms) != 1:
                    continue
            records.extend(saved_records)
        except Exception:
            pass

        return jsonify({
            "records": records,
            "summary": summary(records),
            "sentiment": sentiment_summary(records),
            "creators": cross(records),
            "insights": insights(records)
        })

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",5000)),debug=True)
