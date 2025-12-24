import re
from typing import List, Dict, Optional
import os
import requests
from PyPDF2 import PdfReader
from mcp.server.fastmcp import FastMCP
from transformers import pipeline
from dotenv import load_dotenv

load_dotenv()
# Nom du serveur MCP
mcp = FastMCP("PDF-and-sentiment")

# Modèle de sentiment multilingue (1 à 5 étoiles)
sentiment_model = pipeline(
    "sentiment-analysis",
    model="nlptown/bert-base-multilingual-uncased-sentiment",
)

# -----------------------------
# Utils
# -----------------------------
def _clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def _stars_to_binary(label: str) -> str:
    """
    '1 star' / '2 stars' -> NEGATIVE
    '3 stars'           -> NEUTRAL
    '4 stars' / '5 stars' -> POSITIVE
    """
    stars = int(label[0])
    if stars <= 2:
        return "NEGATIVE"
    if stars == 3:
        return "NEUTRAL"
    return "POSITIVE"


# -----------------------------
# MCP tools
# -----------------------------
@mcp.tool()
def pdf_to_page_list(pdf_path: str) -> List[str]:
    """
    Reads a PDF file and returns a list of strings, one per page.
    """
    reader = PdfReader(pdf_path)
    pages: List[str] = []

    for page in reader.pages:
        text = _clean_text(page.extract_text())
        pages.append(text)

    return pages


@mcp.tool()
def analysis_of_sentiment(text: str) -> Dict:
    """
    Analyse le sentiment d'un texte (multilingue).

    Returns:
        {
          "stars": int (1..5),
          "binary_label": "POSITIVE" | "NEGATIVE" | "NEUTRAL",
          "score": float
        }
    """
    cleaned = _clean_text(text)

    if not cleaned:
        return {
            "stars": 3,
            "binary_label": "NEUTRAL",
            "score": 0.0,
        }

    result = sentiment_model(cleaned, truncation=True)[0]
    stars = int(result["label"][0])

    return {
        "stars": stars,
        "binary_label": _stars_to_binary(result["label"]),
        "score": float(result["score"]),
    }

@mcp.tool()
def newsbytheme(topic: str) -> List[Dict[str, Optional[str]]]:
    """
    Tool MCP : récupère 5 articles NewsAPI liés à un thème.
    """
    api_key = os.getenv("NEWSAPI_KEY")

    if not api_key:
        return [{
            "error": "MISSING_API_KEY",
            "message": "NEWSAPI_KEY non trouvée (dotenv non chargé ?)"
        }]

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": topic,
        "language": "fr",
        "pageSize": 50,
        "apiKey": api_key
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return [{"error": "HTTP_ERROR", "message": str(e)}]

    if data.get("status") != "ok":
        return [{"error": "NEWSAPI_ERROR", "message": str(data)}]

    return [
        {
            "title": a.get("title"),
            "source": (a.get("source") or {}).get("name"),
            "published_at": a.get("publishedAt"),
            "url": a.get("url"),
            "description": a.get("description")
        }
        for a in data.get("articles", [])
    ]





if __name__ == "__main__":
    mcp.run(transport="stdio")
