import json
from loguru import logger
from app.services.vector_db import vector_db

SCORE_THRESHOLD = 0.59

FETCH_K = 20

_RANKER_TYPE = "weighted"
_RANKER_PARAMS = {"weights": [0.86, 0.14]}  # [dense, sparse]


def search_portfolio_images(query: str) -> str:
    """
    Search for images in the photography portfolio using hybrid semantic search.

    Returns a JSON string of matching images and their metadata/URLs, filtered
    by a calibrated similarity threshold so only genuinely relevant photos are
    returned. If no photos pass the threshold, returns a plain-text message.
    """
    if not vector_db.vector_store:
        return "Search is currently unavailable (Vector DB not configured)."

    try:
        docs_and_scores = vector_db.vector_store.similarity_search_with_score(
            query,
            k=FETCH_K,
            ranker_type=_RANKER_TYPE,
            ranker_params=_RANKER_PARAMS,
        )

        # Filter out results below the calibrated relevance threshold
        relevant = [
            (doc, score)
            for doc, score in docs_and_scores
            if score >= SCORE_THRESHOLD
        ]

        logger.debug(
            f"Search '{query}': {len(relevant)}/{len(docs_and_scores)} docs "
            f"passed threshold={SCORE_THRESHOLD}. "
            f"Scores: {[round(s, 4) for _, s in docs_and_scores[:5]]}"
        )

        if not relevant:
            logger.info(
                f"No results above threshold for query '{query}'. "
                f"Top score was {docs_and_scores[0][1]:.4f}"
                if docs_and_scores else f"No results at all for query '{query}'."
            )
            return "No matching photos found in the portfolio."

        # Cap at top 5 after filtering
        results = relevant[:5]

        formatted = []
        for doc, score in results:
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
