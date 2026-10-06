from typing import Literal

from pydantic import BaseModel, Field

SpecificDisease = Literal[
    "none", "cataract", "benign prostatic hypertrophy", "hernia", "hydrocele", "fistula or fissure", "haemorrhoids",
    "sinusitis", "tonsillitis", "gall bladder stones", "kidney or urinary stones", "joint replacement", "varicose veins",
]
YesNoUnclear = Literal["yes", "no", "unclear"]


class ClinicalFacts(BaseModel):
    """What the model reads out of the free-text discharge summary. Numbers and dates are NOT
    asked for here: they come from the structured claim, so the model cannot get them wrong."""
    primary_diagnosis: str
    procedure: str = Field(description="Main procedure or treatment; 'conservative management' if none.")
    is_accident: bool = Field(description="True only if the summary documents an accident/injury as the cause.")
    specific_disease: SpecificDisease = Field(description="Matching condition from the specific-disease list, else 'none'.")
    related_to_declared_ped: YesNoUnclear = Field(
        description="Is this admission caused by, or a direct complication of, any declared pre-existing disease?")
    alcohol_or_substance_related: YesNoUnclear = Field(
        description="'yes' only if documented as a cause; 'unclear' if documented as a possible cause; 'no' otherwise.")
    cosmetic: bool
    dental: bool
    evidence_quotes: list[str] = Field(description="Short verbatim quotes from the summary supporting each finding.")


class Memo(BaseModel):
    assessor_summary: str = Field(description="3-5 sentences for the claims assessor: facts, decision, clauses, what to verify.")
    customer_letter: str = Field(description="Plain-language letter to the policyholder. Use the amounts given, no others.")
    clauses_cited: list[str] = Field(description="Clause ids relied upon, e.g. ['3.2', '4.1'].")
