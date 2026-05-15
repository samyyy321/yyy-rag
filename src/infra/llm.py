from langchain_openai import ChatOpenAI

from src.core.config import get_settings


def get_llm() -> ChatOpenAI:
    settings = get_settings()

    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.API_KEY,
        base_url=settings.BASE_URL,
        temperature=0,
    )