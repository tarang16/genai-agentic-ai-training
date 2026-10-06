from typing import Literal

from pydantic import BaseModel, Field

EvidenceIds = Field(description="Evidence ids exactly as given in square brackets, e.g. ['M1-04', 'S-02'].")


# ---- step 1: per-source extraction ---------------------------------------------------
class Insight(BaseModel):
    type: Literal["pain_point", "request", "decision", "constraint", "metric", "open_question"]
    statement: str = Field(description="One sentence, in your own words, specific (numbers, roles, timings).")
    stakeholder: str = Field(description="Who holds this view, by role, e.g. 'Head of Sales', 'Sales Rep (West)'.")
    evidence_ids: list[str] = EvidenceIds


class SourceInsights(BaseModel):
    insights: list[Insight]


# ---- step 2: synthesis across sources ------------------------------------------------
class Theme(BaseModel):
    name: str
    summary: str
    evidence_ids: list[str] = EvidenceIds


class Position(BaseModel):
    stakeholder: str
    position: str
    evidence_ids: list[str] = EvidenceIds


class Conflict(BaseModel):
    id: str = Field(description="C1, C2, ...")
    topic: str
    positions: list[Position]


class Synthesis(BaseModel):
    themes: list[Theme]
    conflicts: list[Conflict] = Field(description="Places where stakeholders or sources disagree.")


# ---- step 3: the PRD -----------------------------------------------------------------
class AcceptanceCriterion(BaseModel):
    given: str
    when: str
    then: str = Field(description="Observable, testable outcome. Use numbers instead of words like 'fast'.")


class UserStory(BaseModel):
    id: str = Field(description="US-01, US-02, ...")
    as_a: str
    i_want: str
    so_that: str
    priority: Literal["Must", "Should", "Could", "Won't (v1)"]
    acceptance_criteria: list[AcceptanceCriterion]
    evidence_ids: list[str] = EvidenceIds


class Goal(BaseModel):
    goal: str
    metric: str = Field(description="How it is measured, with a numeric target and baseline if known.")
    evidence_ids: list[str] = EvidenceIds


class Decision(BaseModel):
    conflict_id: str
    decision: str
    rationale: str
    evidence_ids: list[str] = EvidenceIds


class OpenQuestion(BaseModel):
    question: str
    owner: str = Field(description="Role that must answer it.")
    conflict_id: str = Field(default="", description="Conflict id if this question comes from a conflict.")
    evidence_ids: list[str] = EvidenceIds


class Constraint(BaseModel):
    constraint: str
    category: Literal["compliance", "data", "technical", "operational"]
    evidence_ids: list[str] = EvidenceIds


class PRD(BaseModel):
    title: str
    problem_statement: str
    goals: list[Goal]
    non_goals: list[str]
    personas: list[str]
    user_stories: list[UserStory]
    constraints: list[Constraint]
    decisions: list[Decision] = Field(description="Conflicts the evidence actually resolves, with rationale.")
    open_questions: list[OpenQuestion] = Field(description="Every unresolved conflict must appear here.")
    risks: list[str]
