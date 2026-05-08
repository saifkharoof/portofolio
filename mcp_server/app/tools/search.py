import json
from loguru import logger
from app.services.vector_db import vector_db

FETCH_K = 20
_RANKER_TYPE = "weighted"
_RANKER_PARAMS = {"weights": [0.85, 0.15]}  # [dense, sparse]


def search_portfolio_images(query: str = "", **kwargs) -> str:
    """
    Search for images in the photography portfolio using hybrid semantic search.

    Returns a JSON string of matching images and their metadata/URLs, filtered
    by a calibrated similarity threshold. If no photos pass the threshold,
    returns a plain-text message.
    """
    if not query or not query.strip():
        return "No matching photos found in the portfolio."

    if not vector_db.vector_store:
        return "Search is currently unavailable (Vector DB not configured)."

    try:
        docs_and_scores = vector_db.vector_store.similarity_search_with_score(
            query,
            k=FETCH_K,
            ranker_type=_RANKER_TYPE,
            ranker_params=_RANKER_PARAMS,
        )

        logger.debug(
            f"Search '{query}': {docs_and_scores} docs "
            f"Scores: {[round(s, 4) for _, s in docs_and_scores]}"
        )

        formatted = []
        for doc, score in docs_and_scores:
            meta = doc.metadata
            formatted.append({
                "title": meta.get("title", "Unknown"),
                "category": meta.get("category", "Unknown"),
                "tags": meta.get("tags", ""),
                "image_url": meta.get("image_url", ""),
                "description": doc.page_content,
                "relevance_score": round(score, 4),
            })

        return json.dumps(formatted, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error during portfolio search for query '{query}': {e}")
        return f"Tool Execution Error: {str(e)}"
