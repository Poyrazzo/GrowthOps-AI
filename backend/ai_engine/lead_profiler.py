from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from ai_engine.llm import get_llm, get_langfuse_handler

class LeadScore(BaseModel):
    score: int = Field(description="A score from 0 to 100 indicating how well this lead matches the target persona.")
    reasoning: str = Field(description="A brief explanation for the score assigned.")
    recommended_message_angle: str = Field(description="A short recommended angle or hook for the outreach email.")

def score_lead(lead_title: str, company_vp: str, campaign_persona: str) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(LeadScore)
    
    prompt = PromptTemplate.from_template(
        "You are an expert B2B sales development representative.\n"
        "Given the following lead and campaign details, score the lead from 0 to 100 based on how well they fit the target persona, and recommend an outreach angle.\n\n"
        "Lead Job Title: {lead_title}\n"
        "Company Value Proposition: {company_vp}\n"
        "Campaign Target Persona: {campaign_persona}\n"
    )
    
    chain = prompt | structured_llm
    
    handler = get_langfuse_handler()
    config = {"callbacks": [handler]} if handler else {}
    
    result = chain.invoke({
        "lead_title": lead_title or "Unknown",
        "company_vp": company_vp or "Unknown",
        "campaign_persona": campaign_persona or "Any"
    }, config=config)
    return result.dict() if result else {}
