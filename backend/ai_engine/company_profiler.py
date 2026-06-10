from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from ai_engine.llm import get_llm, get_langfuse_handler

class CompanyProfile(BaseModel):
    name: str = Field(description="The name of the company")
    sector: str = Field(description="The industry or sector the company operates in")
    size: str = Field(description="The estimated size of the company (e.g., '1-10', '11-50', 'Enterprise')")
    location: str = Field(description="The headquarters or main location of the company")
    value_proposition: str = Field(description="A concise summary of the company's core value proposition")

def extract_company_info(domain: str, body_text: str) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(CompanyProfile)
    
    prompt = PromptTemplate.from_template(
        "You are an expert B2B data researcher. Extract the company profile from the following website text.\n\n"
        "Domain: {domain}\n"
        "Website Text:\n{body_text}\n"
    )
    
    chain = prompt | structured_llm
    
    # Truncate to roughly fit in context window (e.g., ~15000 chars is ~3-4k tokens)
    truncated_text = body_text[:15000] if body_text else ""
    
    handler = get_langfuse_handler()
    config = {"callbacks": [handler]} if handler else {}
    
    result = chain.invoke({"domain": domain, "body_text": truncated_text}, config=config)
    return result.dict() if result else {}
