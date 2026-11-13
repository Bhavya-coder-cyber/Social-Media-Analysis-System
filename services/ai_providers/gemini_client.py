import os
import json

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
def generate_insights(context):

    client = genai.Client(
        api_key=os.getenv("GEMINI_API_KEY")
    )

    system_prompt = """
    You are an expert social media analytics consultant.

    Analyze the supplied social media analytics data and provide
    actionable, evidence-based insights.

    Return valid JSON with exactly these keys:

    {
        "overall_assessment": "A concise performance overview",
        "strengths": ["Strength 1", "Strength 2"],
        "weaknesses": ["Weakness 1", "Weakness 2"],
        "growth_opportunities": ["Opportunity 1", "Opportunity 2"],
        "recommendations": [
            {
                "title": "Recommendation title",
                "reason": "Why this is recommended",
                "action": "What the creator should do"
            }
        ],
        "confidence": "High, Medium, or Low"
    }

    Important:
    - Base conclusions only on supplied data.
    - Do not invent metrics or historical trends.
    - Mention data limitations where relevant.
    - Keep recommendations practical and specific.
    - Return JSON only.
    """

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=json.dumps(context),
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            temperature=0.3
        )
    )

    if not response.text:
        raise ValueError("Gemini returned an empty response.")

    return json.loads(response.text)