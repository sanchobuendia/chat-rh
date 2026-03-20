from langchain.chat_models import init_chat_model
from app.core.config import get_settings

settings = get_settings()


def get_chat_model():
    provider = settings.MODEL_PROVIDER.strip()
    model_name = settings.BEDROCK_MODEL_ID.strip()

    if not provider:
        raise ValueError("MODEL_PROVIDER is not configured")
    if not model_name:
        raise ValueError("MODEL_NAME is not configured")

    return init_chat_model(
        model_name,
        model_provider=provider,
        temperature=settings.MODEL_TEMPERATURE,
    )
