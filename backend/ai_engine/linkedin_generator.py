from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from ai_engine.llm import get_llm, get_langfuse_handler

class ConnectionRequestDraft(BaseModel):
    connection_message: str = Field(description="A personalized LinkedIn connection request note. MUST be under 280 characters (LinkedIn's limit is 300).")

class DirectMessageDraft(BaseModel):
    dm_message: str = Field(description="A short, conversational LinkedIn direct message to send after the connection is accepted. No hard selling.")

def generate_connection_request(lead_name: str, lead_title: str, company_name: str, campaign_vp: str, message_angle: str) -> dict:
    """Drafts the connection request note a human operator will send manually (SRS 3.14)."""
    llm = get_llm()
    structured_llm = llm.with_structured_output(ConnectionRequestDraft)

    prompt = PromptTemplate.from_template(
        "You are an expert B2B social seller. Write a short, warm LinkedIn connection request note.\n"
        "It must be under 280 characters, mention something relevant to the prospect, and must NOT pitch or sell.\n\n"
        "Prospect Name: {lead_name}\n"
        "Prospect Title: {lead_title}\n"
        "Prospect Company: {company_name}\n"
        "Our Value Proposition (context only, do not pitch): {campaign_vp}\n"
        "Recommended Angle: {message_angle}\n"
    )

    chain = prompt | structured_llm

    handler = get_langfuse_handler()
    config = {"callbacks": [handler]} if handler else {}

    result = chain.invoke({
        "lead_name": lead_name or "there",
        "lead_title": lead_title or "Professional",
        "company_name": company_name or "their company",
        "campaign_vp": campaign_vp or "our services",
        "message_angle": message_angle or "General introduction"
    }, config=config)
    return result.dict() if result else {}

def generate_dm_draft(lead_name: str, lead_title: str, company_name: str, campaign_vp: str, message_angle: str, lead_magnet: str = None) -> dict:
    """Drafts the follow-up DM sent manually after a connection is accepted (SRS 3.14)."""
    llm = get_llm()
    structured_llm = llm.with_structured_output(DirectMessageDraft)

    prompt = PromptTemplate.from_template(
        "You are an expert B2B social seller. The prospect just accepted our LinkedIn connection request.\n"
        "Write a short, friendly direct message that opens a conversation and softly offers value.\n"
        "Keep it under 500 characters, conversational, and never pushy.\n\n"
        "Prospect Name: {lead_name}\n"
        "Prospect Title: {lead_title}\n"
        "Prospect Company: {company_name}\n"
        "Our Value Proposition: {campaign_vp}\n"
        "Recommended Angle: {message_angle}\n"
        "Lead Magnet/Offer we can share: {lead_magnet}\n"
    )

    chain = prompt | structured_llm

    handler = get_langfuse_handler()
    config = {"callbacks": [handler]} if handler else {}

    result = chain.invoke({
        "lead_name": lead_name or "there",
        "lead_title": lead_title or "Professional",
        "company_name": company_name or "their company",
        "campaign_vp": campaign_vp or "our services",
        "message_angle": message_angle or "General introduction",
        "lead_magnet": lead_magnet or "None"
    }, config=config)
    return result.dict() if result else {}
