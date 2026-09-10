from pydantic import BaseModel, Field


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class AssistantChatResponse(BaseModel):
    answer: str
    used_insufficient_data_fallback: bool
    source: str = "autonomous_financial_engine"
    suggested_followups: list[str] = []


class AssistantPromptsResponse(BaseModel):
    user_type: str
    prompts: list[str]
