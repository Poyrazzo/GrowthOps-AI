from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from ai_engine.llm import get_llm, get_langfuse_handler

class LeadScore(BaseModel):
    score: int = Field(description="An integer from 0 to 100 for how well this lead matches the target persona and campaign.")
    reasoning: str = Field(description="One or two sentences explaining the score.")
    persona: str = Field(description="A short persona label, e.g. 'HR Decision Maker', 'School Director', or 'Company Gateway Inbox' for a generic/role inbox.")
    recommended_message_angle: str = Field(description="A short recommended angle or hook for the outreach email.")
    recommended_lead_magnet: str = Field(
        default="",
        description="The name of the single most fitting lead magnet from the provided list, copied EXACTLY. Empty string if none fit."
    )

def score_lead(lead_title: str, company_vp: str, campaign_persona: str, available_lead_magnets: list = None,
               is_generic_email: bool = False, company_name: str = None) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(LeadScore)

    magnets_text = "None available"
    if available_lead_magnets:
        magnets_text = "\n".join(
            f"- {m['name']}: {m['description']} (target persona: {m['target_persona'] or 'any'})"
            for m in available_lead_magnets
        )

    # A generic/role inbox (info@, contact@) is NOT a person — but at a company
    # in the target sector it is still a legitimate gateway. Tell the model to
    # judge it as a company-level contact rather than penalize it for an unknown
    # title, so a relevant school's contact inbox doesn't get junk-scored.
    if is_generic_email:
        contact_context = (
            "CONTACT TYPE: This is a GENERIC/ROLE company inbox (e.g. info@, contact@), NOT an individual.\n"
            "Do NOT penalize it for an unknown personal title. Instead judge it as a company-level entry "
            "point: score on how well the COMPANY fits the campaign. If the company is a clear fit, a "
            "generic inbox is a reasonable score (around 55-75). Use the persona label 'Company Gateway Inbox'.\n"
        )
    else:
        contact_context = (
            "CONTACT TYPE: This is an individual person's address. Score on how well their role fits "
            "the target persona.\n"
        )

    prompt = PromptTemplate.from_template(
        "You are an expert B2B sales development representative qualifying an inbound scraped lead.\n\n"
        "{contact_context}\n"
        "Score the lead from 0 to 100 on overall fit, assign a persona label, recommend a concrete outreach "
        "angle, and pick the single best-fitting lead magnet from the list (copy its name EXACTLY, or empty "
        "string if none fit).\n\n"
        "Lead Job Title: {lead_title}\n"
        "Company Name: {company_name}\n"
        "Company Value Proposition: {company_vp}\n"
        "Campaign Target Persona: {campaign_persona}\n\n"
        "Available Lead Magnets:\n{available_lead_magnets}\n"
    )

    chain = prompt | structured_llm

    handler = get_langfuse_handler()
    config = {"callbacks": [handler]} if handler else {}

    result = chain.invoke({
        "contact_context": contact_context,
        "lead_title": lead_title or "Unknown",
        "company_name": company_name or "Unknown",
        "company_vp": company_vp or "Unknown",
        "campaign_persona": campaign_persona or "Any",
        "available_lead_magnets": magnets_text
    }, config=config)
    return result.dict() if result else {}
