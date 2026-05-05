import json
import base64
from loguru import logger
from app.services.vector_db import vector_db
from app.core.config import settings

SCORE_THRESHOLD = 0.59

FETCH_K = 20

_RANKER_TYPE = "weighted"
_RANKER_PARAMS = {"weights": [0.85, 0.15]}  # [dense, sparse]


def search_portfolio_images(query: str = "", image_base64: str | None = None) -> str:
    """
    Search for images in the photography portfolio using hybrid semantic search.
    If image_base64 is provided, it embeds the image directly using a multimodal model.

    Returns a JSON string of matching images and their metadata/URLs, filtered
    by a calibrated similarity threshold so only genuinely relevant photos are
    returned. If no photos pass the threshold, returns a plain-text message.
    """
    if not vector_db.vector_store:
        return "Search is currently unavailable (Vector DB not configured)."

    original_embed = None
    try:
        if image_base64:
            from google import genai
            from google.genai import types
            
            original_embed = vector_db.vector_store.embedding_func
            
            class MultimodalEmbedder:
                def embed_query(self, text: str):
                    img_data = base64.b64decode(image_base64)
                    client = genai.Client(api_key=settings.gemini_api_key)
                    
                    # Combine the image and text into a single Content object.
                    # This is critical: if passed as a Python list [text, part], the SDK 
                    # embeds them as two separate documents, discarding the image embedding.
                    parts = [types.Part.from_bytes(data=img_data, mime_type="image/jpeg")]
                    if text and text.strip() and text.strip().lower() != "image matching":
                        parts.append(types.Part.from_text(text=text) if hasattr(types.Part, "from_text") else types.Part(text=text))
                        
                    content_obj = types.Content(parts=parts)
                    
                    res = client.models.embed_content(
                        model=settings.gemini_embedding_model,
                        contents=content_obj,
                        config=types.EmbedContentConfig(output_dimensionality=768)
                    )
                    return res.embeddings[0].values
                    
                def embed_documents(self, texts: list[str]):
                    return [self.embed_query(t) for t in texts]

            vector_db.vector_store.embedding_func = MultimodalEmbedder()

        safe_query = query if query.strip() else "image matching"

        # --- HyDE (Hypothetical Document Embeddings) ---
        # If it's a pure text query, use the LLM to generate a hypothetical
        # visual description of the photo to improve vector match accuracy.
        if not image_base64 and safe_query != "image matching":
            try:
                from google import genai
                client = genai.Client(api_key=settings.gemini_api_key)
                hyde_prompt = (
                    f"Write a brief, highly visual description of a photography portfolio image "
                    f"that perfectly matches this request: '{safe_query}'. "
                    f"Focus only on visual elements (colors, subjects, lighting, composition). "
                    f"Do not include introductory text."
                )
                res = client.models.generate_content(
                    model=settings.gemini_model_name,
                    contents=hyde_prompt
                )
                if res.text:
                    # Append the hypothetical description to the original query
                    safe_query = f"{safe_query}\n{res.text}"
                    logger.debug(f"HyDE expansion applied: {res.text}")
            except Exception as e:
                logger.warning(f"HyDE generation failed, using original query: {e}")

        try:
            docs_and_scores = vector_db.vector_store.similarity_search_with_score(
                safe_query,
                k=FETCH_K,
                ranker_type=_RANKER_TYPE,
                ranker_params=_RANKER_PARAMS,
            )
        finally:
            if original_embed is not None:
                vector_db.vector_store.embedding_func = original_embed

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
        if original_embed is not None:
            vector_db.vector_store.embedding_func = original_embed
        return f"Tool Execution Error: {str(e)}"
