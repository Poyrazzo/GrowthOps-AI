from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from ai_engine.llm import get_llm, get_langfuse_handler

class ReplyClassification(BaseModel):
    category: Literal['interested', 'not_interested', 'meeting_request', 'price_question', 'unsubscribe', 'bounce', 'wrong_person', 'other'] = Field(
        description="The category of the prospect's reply."
    )
    sentiment: Literal['positive', 'negative', 'neutral'] = Field(description="The general sentiment of the reply.")
    confidence: float = Field(description="Confidence score of the classification between 0.0 and 1.0.")
    summary: str = Field(description="A brief 1-2 sentence summary of what the prospect said.")
    next_action: str = Field(description="A short recommendation on what the human operator or system should do next.")

def classify_reply(reply_body: str, original_message_body: str) -> dict:
    """Uses LLM to classify an incoming reply contextually against the original message sent."""
    llm = get_llm()
    if not llm:
        return {}
        
    structured_llm = llm.with_structured_output(ReplyClassification)
    
    prompt = PromptTemplate(
        input_variables=["reply_body", "original_message_body"],
        template="""You are an expert sales operations AI. Your job is to classify incoming email replies.
        
Read the original email we sent to the prospect:
---
{original_message_body}
---

Now read the prospect's reply:
---
{reply_body}
---

Classify the prospect's reply strictly into one of the allowed categories. Provide a sentiment, confidence score, brief summary, and a recommended next action."""
    )
    
    chain = prompt | structured_llm
    
    callbacks = []
    handler = get_langfuse_handler()
    if handler:
        callbacks.append(handler)

    # Exceptions intentionally propagate: the calling Celery task declares
    # autoretry_for=(Exception,), and swallowing errors here used to leave
    # bounced/unsubscribed leads permanently unclassified and unsuppressed.
    result = chain.invoke(
        {
            "reply_body": reply_body,
            "original_message_body": original_message_body or "(original message unavailable)"
        },
        config={"callbacks": callbacks}
    )
    return result.dict() if result else {}
