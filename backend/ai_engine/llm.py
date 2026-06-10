import os
from django.conf import settings
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler

def get_llm(model_name: str = "gpt-4o-mini", temperature: float = 0) -> ChatOpenAI:
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in Django settings.")
        
    return ChatOpenAI(
        openai_api_key=api_key,
        model=model_name,
        temperature=temperature
    )

def get_langfuse_handler() -> CallbackHandler:
    secret_key = getattr(settings, 'LANGFUSE_SECRET_KEY', None)
    public_key = getattr(settings, 'LANGFUSE_PUBLIC_KEY', None)
    host = getattr(settings, 'LANGFUSE_HOST', 'https://cloud.langfuse.com')
    
    if not secret_key or not public_key:
        return None
        
    os.environ['LANGFUSE_SECRET_KEY'] = secret_key
    os.environ['LANGFUSE_PUBLIC_KEY'] = public_key
    os.environ['LANGFUSE_HOST'] = host
    
    return CallbackHandler()
