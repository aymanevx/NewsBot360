from PyPDF2 import PdfReader
from mcp.server.fastmcp import FastMCP
from transformers import pipeline

# Nom du serveur MCP
mcp = FastMCP("PDF-and-sentiment")

# On charge le modèle une seule fois au démarrage
sentiment_model = pipeline("sentiment-analysis")  # modèle par défaut HF (DistilBERT SST-2)


@mcp.tool()
def pdf_to_page_list(pdf_path: str) -> list[str]:
    """
    Reads a PDF file and returns a list of strings, one per page.
    Args:
        pdf_path (str): Path to the PDF file.
    Returns:
        list[str]: List where each element is the text of a page.
    """
    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text())
    return pages


@mcp.tool()
def analysis_of_sentiment(text: str) -> dict:
    """
    Analyse le sentiment d'un texte et indique s'il est positif ou négatif.

    Args:
        text (str): Le texte à analyser.

    Returns:
        dict: {
            "label": "POSITIVE" ou "NEGATIVE",
            "score": probabilité associée (float entre 0 et 1)
        }
    """
    result = sentiment_model(text)[0]  # ex: {'label': 'POSITIVE', 'score': 0.998...}
    return {
        "label": result["label"],
        "score": float(result["score"]),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")