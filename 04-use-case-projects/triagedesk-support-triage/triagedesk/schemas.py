from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["no_display", "connectivity", "flicker_or_artifacts", "audio", "power", "touch",
                   "firmware", "dead_pixel_or_panel", "warranty_or_billing", "other"]
Action = Literal["reply_with_fix", "reply_with_workaround", "start_rma", "request_info", "escalate_l2"]


class Classification(BaseModel):
    category: Category
    severity: Literal["low", "medium", "high", "critical"] = Field(
        description="critical = safety risk or business outage; high = product unusable; medium = degraded; low = question.")
    sentiment: Literal["positive", "neutral", "frustrated", "angry"]
    search_queries: list[str] = Field(
        description="2-3 short search queries to find similar past tickets, KB articles and known bugs. "
                    "Use symptom words and any model, firmware or OS versions mentioned.")


class TriageDecision(BaseModel):
    verdict: Literal["known_issue", "known_bug", "new_issue"] = Field(
        description="known_issue = a KB article or past ticket resolves it; known_bug = matches a Jira issue; "
                    "new_issue = nothing in the evidence clearly matches.")
    matched_refs: list[str] = Field(description="Ids from the evidence that match this ticket, e.g. KB-1004, FD-20602, DISP-430.")
    confidence: Literal["high", "medium", "low"]
    reasoning: str = Field(description="One or two sentences: why these references match (or why nothing does).")
    action: Action
    customer_reply: str = Field(description="Draft reply to the customer. Use only steps from the evidence. Address them as 'Hi there'.")
    internal_note: str = Field(description="Short note for the support agent: what was matched, what to check next.")
