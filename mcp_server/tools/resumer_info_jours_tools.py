from supabase import create_client
import os
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)

client = OpenAI()


def recup_traitement_date_bdd(date) -> pd.DataFrame:
    response = (
        supabase
        .table("articles")
        .select("id")
        .gte("published_at", f"{date}T00:00:00")
        .lte("published_at", f"{date}T23:59:59")
        .eq("feed_id", "3")
        .execute()
    )
    return pd.DataFrame(response.data)


def recup_full(lst):
    response = (
        supabase
        .table("article_texts")
        .select("content")
        .in_("article_id", lst)
        .execute()
    )
    return pd.DataFrame(response.data)


def register(mcp) -> None:
    @mcp.tool()
    def resumer_jour(date: str) -> str:
        """
        Input: date 'YYYY-MM-DD'
        Output: résumé texte de la journée
        """
        df_ids = recup_traitement_date_bdd(date)
        if df_ids.empty:
            return "Aucun article pour cette date."

        ids = df_ids["id"].tolist()

        df_txt = recup_full(ids)
        if df_txt.empty:
            return "Articles trouvés mais aucun contenu."

        articles = df_txt["content"].dropna().tolist()
        if not articles:
            return "Articles trouvés mais contenus vides."

        texte = "\n\n".join(articles)  # limite simple

        prompt = f"""
Résume les informations importantes de la journée ({date}) en français, en 8-12 lignes max.

Articles :
{texte}
""".strip()

        resp = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            temperature=0.2,
        )

        return resp.output_text