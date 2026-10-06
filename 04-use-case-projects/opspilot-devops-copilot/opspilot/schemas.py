from typing import Literal

from pydantic import BaseModel, Field


class Step(BaseModel):
    description: str = Field(description="What this step does and why, in one sentence.")
    command: str = Field(default="", description="Exact shell command, or empty if the step is manual.")
    mutating: bool = Field(description="True if the command changes state (deploy, delete, scale, unlock, restart).")


class Diagnosis(BaseModel):
    root_cause: str = Field(description="Most likely root cause in one or two sentences.")
    confidence: Literal["high", "medium", "low"]
    evidence_lines: list[str] = Field(description="Exact log lines (copied verbatim) that support the root cause.")
    citations: list[str] = Field(description="Runbook section ids used, exactly as given, e.g. 'k8s-oomkilled.md#diagnosis'.")
    steps: list[Step] = Field(description="Ordered investigation and remediation steps, read-only steps first.")
    insufficient_evidence: bool = Field(description="True if the runbooks provided do not cover this failure.")
