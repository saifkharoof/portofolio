from app.services.storage import storage
from app.core.config import settings

def get_portfolio_context() -> str:
    """
    Returns the base prompt persona for the agent along with the parsed CV text.
    This allows the Chat and Voice agents to fetch real-time persona instructions.
    """
    cv_text = storage.get_cv_text()
    
    context = f"""
{settings.bot_persona}

Below is Saif's most up-to-date Curriculum Vitae (CV) for context:
---
{cv_text}
---

Use this information to answer questions about Saif's experience, education, and skills.
    """
    
    return context.strip()
