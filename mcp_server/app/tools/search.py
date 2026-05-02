import json
from app.services.vector_db import vector_db
from loguru import logger

def search_portfolio_images(query: str) -> str:
    """
    Search for images in the photography portfolio using semantic understanding.
    Returns a JSON string of matching images and their URLs.
    """
    retriever = vector_db.get_retriever(search_kwargs={"k": 5})
    
    if not retriever:
        return "Search is currently unavailable (Vector DB not configured)."
        
    try:
        docs = retriever.invoke(query)
        if not docs:
            return "No matching photos found in the portfolio."
            
        formatted = []
        for doc in docs:
            # Depending on how metadata is stored by langchain_milvus
            meta = doc.metadata
            formatted.append({
                "title": meta.get("title", "Unknown"),
                "category": meta.get("category", "Unknown"),
                "tags": meta.get("tags", ""),
                "image_url": meta.get("image_url", ""),
                "description": doc.page_content
            })
            
        return json.dumps(formatted)
    except Exception as e:
        logger.error(f"Error during LangChain Milvus search: {e}")
        return f"Tool Execution Error: {str(e)}"
