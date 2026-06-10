from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from ai_engine.llm import get_llm, get_langfuse_handler

class EmailDraft(BaseModel):
    subject: str = Field(description="A catchy, short, and personalized email subject line.")
    body: str = Field(description="The body of the cold outreach email. Must be highly personalized and conversational.")

def generate_email_draft(lead_name: str, lead_title: str, company_name: str, company_vp: str, campaign_vp: str, message_angle: str, lead_magnet: str = None) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(EmailDraft)
    
    prompt = PromptTemplate.from_template(
        "You are an expert B2B copywriter writing a highly personalized cold email.\n"
        "Draft the email based on the following context. Keep it concise, engaging, and professional.\n\n"
        "Lead Name: {lead_name}\n"
        "Lead Title: {lead_title}\n"
        "Target Company Name: {company_name}\n"
        "Target Company Value Proposition: {company_vp}\n"
        "Our Campaign Value Proposition: {campaign_vp}\n"
        "Recommended Message Angle: {message_angle}\n"
        "Lead Magnet/Offer: {lead_magnet}\n"
    )
    
    chain = prompt | structured_llm
    
    handler = get_langfuse_handler()
    config = {"callbacks": [handler]} if handler else {}
    
    result = chain.invoke({
        "lead_name": lead_name or "there",
        "lead_title": lead_title or "Professional",
        "company_name": company_name or "your company",
        "company_vp": company_vp or "your business operations",
        "campaign_vp": campaign_vp or "our services",
        "message_angle": message_angle or "General introduction",
        "lead_magnet": lead_magnet or "None"
    }, config=config)
    
    return result.dict() if result else {}
