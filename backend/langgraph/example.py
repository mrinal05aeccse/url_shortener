# LangGraph integration example (placeholder)
# This module shows an example of calling an LLM orchestrator to summarize analytics.

import requests
import os

API_BASE = os.getenv('API_BASE', 'http://localhost:8000')
LANGGRAPH_ENDPOINT = os.getenv('LANGGRAPH_ENDPOINT', 'https://api.langgraph.ai/v1/run')
LANGGRAPH_API_KEY = os.getenv('LANGGRAPH_API_KEY', '')

def fetch_analytics(alias: str, api_key: str):
    resp = requests.get(f"{API_BASE}/api/v1/analytics/{alias}?api_key={api_key}")
    resp.raise_for_status()
    return resp.json()

def summarize_with_langgraph(analytics: dict) -> dict:
    prompt = f"Provide a short summary of analytics for alias {analytics['alias']}: total clicks {analytics['total_clicks']} and daily counts {analytics['daily_counts']}."
    payload = {
        "model": "gpt-4o",
        "input": prompt,
    }
    headers = {"Authorization": f"Bearer {LANGGRAPH_API_KEY}"}
    resp = requests.post(LANGGRAPH_ENDPOINT, json=payload, headers=headers)
    if resp.status_code != 200:
        return {"error": "langgraph request failed", "status_code": resp.status_code, "text": resp.text}
    return resp.json()

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('Usage: python backend/langraph/example.py <alias> <admin_api_key>')
        sys.exit(1)
    alias = sys.argv[1]
    api_key = sys.argv[2]
    analytics = fetch_analytics(alias, api_key)
    print('Analytics:', analytics)
    summary = summarize_with_langgraph(analytics)
    print('Summary:', summary)