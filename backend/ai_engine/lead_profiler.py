from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from ai_engine.llm import get_llm, get_langfuse_handler
from scraper.lead_quality import looks_like_clear_non_person_name


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
               is_generic_email: bool = False, company_name: str = None, lead_name: str = None) -> dict:
    if looks_like_clear_non_person_name(lead_name):
        return {
            "score": 0,
            "reasoning": f"'{lead_name}' is clearly not a human lead name.",
            "persona": "Non-Person / Bad Data",
            "recommended_message_angle": "",
            "recommended_lead_magnet": "",
        }

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
        name_note = (
            "\nIMPORTANT: Missing or partial lead names are common in scraped data. "
            "Do NOT score a lead 0 merely because the name is Unknown or incomplete. "
            "Use the job title, company, profile URL context, and target persona to judge fit. "
            "Reserve a 0 score only for confirmed non-person records or unusable bad data.\n"
        )
        if lead_name:
            name_note = (
                f"\nIMPORTANT: The lead's name is '{lead_name}'. "
                "If this clearly does NOT look like a real human name (e.g. it is an institution name, "
                "a product name, a city name, an acronym, or a generic English noun like "
                "'Teacher Workshops' or 'Want Take'), give a score of 0 and set persona to "
                "'Non-Person / Bad Data'. If it could plausibly be a real name from any culture, "
                "judge fit from the role and company instead of zeroing it.\n"
            )
        contact_context = (
            "CONTACT TYPE: This is an individual person's address. Score on how well their role fits "
            f"the target persona.{name_note}"
        )

    prompt = PromptTemplate.from_template(
        "You are an expert B2B sales development representative qualifying an inbound scraped lead.\n\n"
        "{contact_context}\n"
        "Score the lead from 0 to 100 on overall fit, assign a persona label, recommend a concrete outreach "
        "angle, and pick the single best-fitting lead magnet from the list (copy its name EXACTLY, or empty "
        "string if none fit).\n\n"
        "Lead Name: {lead_name}\n"
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
        "lead_name": lead_name or "Unknown",
        "lead_title": lead_title or "Unknown",
        "company_name": company_name or "Unknown",
        "company_vp": company_vp or "Unknown",
        "campaign_persona": campaign_persona or "Any",
        "available_lead_magnets": magnets_text
    }, config=config)
    if not result:
        return {}
    return result if isinstance(result, dict) else result.dict()
