from pydantic import BaseModel, field_validator
from typing import List
from enum import Enum

class ComplianceState(str, Enum):
    fullyCompliant = "Fully Compliant"
    partiallyCompliant = "Partially Compliant"
    nonCompliant = "Non-Compliant"

class ComplianceResult(BaseModel):
    complianceQuestion: str
    complianceState: ComplianceState
    confidence: int  # 0-100
    relevantQuotes: List[str]
    rationale: str

    @field_validator("confidence")
    @classmethod
    def clampConfidence(cls, v):
        return max(0, min(100, v))
    
    @field_validator("complianceState", mode="before")
    @classmethod
    def normalizeState(cls, v):
        validStates = {
            "fully compliant": ComplianceState.fullyCompliant,
            "partially compliant": ComplianceState.partiallyCompliant,
            "non-compliant": ComplianceState.nonCompliant,
            "noncompliant": ComplianceState.nonCompliant,
        }
        normalized = v.strip().lower()
        if normalized not in validStates:
            return ComplianceState.nonCompliant
        return validStates[normalized]

class AnalysisResponse(BaseModel):
    sessionId: str = ""
    results: List[ComplianceResult]

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    sessionId: str
    message: str
    history: List[ChatMessage]

class ChatResponse(BaseModel):
    reply: str