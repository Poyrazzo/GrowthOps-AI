from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from ai_engine.llm import get_llm, get_langfuse_handler

class EmailDraft(BaseModel):
    subject: str = Field(description="A short, specific, personalized subject line (no spammy words, under 60 chars).")
    body: str = Field(description="The full cold email body, ready to send AS-IS with no placeholders to fill in.")

# Shared rules so every draft is send-ready and never contains [bracketed] gaps.
_STYLE_RULES = (
    "STRICT RULES:\n"
    "1. Output must be 100% ready to send. NEVER include bracketed placeholders like "
    "[Your Name], [Company], [link], or [Your Position]. If you don't know a detail, omit it.\n"
    "2. Sign off simply as 'The {sender_name} Team' — do NOT invent a personal name.\n"
    "3. Keep the body under 120 words. Be specific and conversational, not generic or salesy.\n"
    "4. One clear, low-friction call to action (a short reply or quick call).\n"
    "5. Plain text only. No markdown, no subject line inside the body.\n"
)

def generate_email_draft(lead_name: str, lead_title: str, company_name: str, company_vp: str, campaign_vp: str, message_angle: str, lead_magnet: str = None, is_generic_email: bool = False, sender_name: str = "Konuşarak Öğren") -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(EmailDraft)

    if is_generic_email:
        # A role inbox (info@, contact@) is usually read by an intermediary.
        # Write a short note that asks to be forwarded.
        audience_block = (
            "AUDIENCE: This email goes to a GENERIC company inbox (e.g. info@/contact@), "
            "read by a gatekeeper, not the decision-maker. Do NOT address a named person. "
            "Open with a polite line asking them to forward this to the right person "
            f"(the {message_angle or 'relevant decision-maker'}). Keep it brief and respectful.\n"
        )
        greeting_hint = "Use a neutral greeting like 'Hello,' (no personal name)."
    else:
        audience_block = (
            "AUDIENCE: This email goes directly to the named individual below. "
            "Address them by first name and reference their role.\n"
        )
        greeting_hint = "Greet the lead by their first name."

    prompt = PromptTemplate.from_template(
        "You are an expert B2B copywriter writing a highly personalized cold email.\n\n"
        "{audience_block}\n"
        "{style_rules}\n"
        "{greeting_hint}\n\n"
        "CONTEXT:\n"
        "Lead Name: {lead_name}\n"
        "Lead Title: {lead_title}\n"
        "Target Company Name: {company_name}\n"
        "Target Company Value Proposition: {company_vp}\n"
        "Our Value Proposition (what we offer): {campaign_vp}\n"
        "Recommended Message Angle: {message_angle}\n"
        "Lead Magnet/Offer to include: {lead_magnet}\n"
    )

    chain = prompt | structured_llm

    handler = get_langfuse_handler()
    config = {"callbacks": [handler]} if handler else {}

    result = chain.invoke({
        "audience_block": audience_block,
        "style_rules": _STYLE_RULES.format(sender_name=sender_name),
        "greeting_hint": greeting_hint,
        "lead_name": lead_name or "there",
        "lead_title": lead_title or "Professional",
        "company_name": company_name or "your company",
        "company_vp": company_vp or "your business operations",
        "campaign_vp": campaign_vp or "our services",
        "message_angle": message_angle or "General introduction",
        "lead_magnet": lead_magnet or "None"
    }, config=config)
    if not result:
        return {}
    return result if isinstance(result, dict) else result.dict()

def generate_followup_draft(lead_name: str, company_name: str, previous_emails: str, message_angle: str) -> dict:
    llm = get_llm()
    if not llm:
        return {}
    structured_llm = llm.with_structured_output(EmailDraft)
    
    prompt = PromptTemplate.from_template(
        "You are an expert B2B copywriter writing a follow-up cold email.\n"
        "Read the previous emails we have sent to this prospect:\n"
        "---\n{previous_emails}\n---\n\n"
        "Draft a short, polite, and bump-style follow-up email. Do not repeat the exact same pitch, just bump the thread and provide new value.\n"
        "Lead Name: {lead_name}\n"
        "Target Company Name: {company_name}\n"
        "Message Angle: {message_angle}\n"
    )
    
    chain = prompt | structured_llm
    
    handler = get_langfuse_handler()
    config = {"callbacks": [handler]} if handler else {}
    
    try:
        result = chain.invoke({
            "lead_name": lead_name or "there",
            "company_name": company_name or "your company",
            "previous_emails": previous_emails,
            "message_angle": message_angle or "General follow-up"
        }, config=config)
        if not result:
            return {}
        return result if isinstance(result, dict) else result.dict()
    except Exception as e:
        print(f"Failed to generate follow-up: {e}")
        return {}
