"""Deterministic adjudication. The money math lives here, not in a prompt.

An LLM is good at reading a discharge summary ("is this a complication of the declared diabetes?").
It is bad at applying a proportionate room-rent deduction to four bill lines and a 20% co-pay, and
an insurer must be able to explain every rupee. So: the model extracts facts, this module decides,
and every deduction carries the clause it comes from.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from .config import AUTO_APPROVE_LIMIT, SUBMISSION_WINDOW_DAYS

ASSOCIATED = {"room", "nursing", "surgeon", "ot"}   # clause 4.1: proportionate deduction applies to these
CATARACT_SUBLIMIT = 40000

# Keyword backstop for clause 3.2. If the model misses "cholelithiasis", code still catches it.
SPECIFIC_DISEASE_KEYWORDS = {
    "cataract": ["cataract", "phacoemulsification"],
    "hernia": ["hernia", "hernioplasty", "herniorrhaphy"],
    "gall bladder stones": ["cholelithiasis", "cholecystectomy", "gall bladder calculi", "gallstone"],
    "kidney or urinary stones": ["nephrolithiasis", "ureteric calculus", "renal calculus", "lithotripsy"],
    "haemorrhoids": ["haemorrhoid", "hemorrhoid", "piles"],
    "joint replacement": ["knee replacement", "hip replacement", "arthroplasty"],
    "benign prostatic hypertrophy": ["prostatic hypertrophy", "turp"],
    "hydrocele": ["hydrocele"], "sinusitis": ["sinusitis", "fess"], "tonsillitis": ["tonsillitis", "tonsillectomy"],
    "varicose veins": ["varicose"], "fistula or fissure": ["fistula", "fissure in ano"],
}


@dataclass
class Line:
    category: str
    description: str
    claimed: float
    payable: float
    reason: str = ""
    clause: str = ""


@dataclass
class Adjudication:
    decision: str                     # approve | partial | reject | refer
    claimed: float
    payable: float | None             # None when referred: a human decides
    provisional_payable: float        # what would be paid if the referral is cleared
    lines: list[Line] = field(default_factory=list)
    reasons: list[dict] = field(default_factory=list)   # [{"clause": "3.2", "text": "..."}]
    flags: list[str] = field(default_factory=list)
    route: str = "human_review"       # auto | human_review
    policy_months: int = 0


def months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month) - (1 if end.day < start.day else 0)


def specific_disease(facts: dict) -> str:
    if facts.get("specific_disease", "none") != "none":
        return facts["specific_disease"]
    text = (facts.get("primary_diagnosis", "") + " " + facts.get("procedure", "")).lower()
    for disease, words in SPECIFIC_DISEASE_KEYWORDS.items():
        if any(re.search(rf"\b{re.escape(w)}", text) for w in words):
            return disease
    return "none"


def adjudicate(claim: dict, facts: dict) -> Adjudication:
    pol = claim["policy"]
    si = pol["sum_insured"]
    admit = date.fromisoformat(claim["admission_date"])
    inception = date.fromisoformat(pol["inception_date"])
    days_cover, months_cover = (admit - inception).days, months_between(inception, admit)
    claimed = float(sum(i["amount"] for i in claim["bill"]))
    reasons, flags = [], []

    # ---- 1. Eligibility: waiting periods and exclusions --------------------------------
    rejections = []
    if days_cover < 30 and not facts["is_accident"]:
        rejections.append(("3.1", f"Admission {days_cover} days after inception, within the 30-day initial waiting period."))
    elif days_cover < 30:
        reasons.append({"clause": "3.1", "text": f"Within 30 days of inception ({days_cover} days) but caused by an accident, so the initial waiting period does not apply."})
    disease = specific_disease(facts)
    if disease != "none" and months_cover < 24 and not (disease == "joint replacement" and facts["is_accident"]):
        rejections.append(("3.2", f"'{disease}' has a 24-month waiting period; cover has run {months_cover} months."))
    if pol["declared_ped"] and months_cover < 36:
        if facts["related_to_declared_ped"] == "yes":
            rejections.append(("3.3", f"Related to declared PED ({', '.join(pol['declared_ped'])}); 36-month waiting period, cover has run {months_cover} months."))
        elif facts["related_to_declared_ped"] == "unclear":
            flags.append("ped_link_unclear")
            reasons.append({"clause": "3.3", "text": "Possible link to a declared PED within 36 months; medical review needed."})
    if facts["alcohol_or_substance_related"] == "yes":
        rejections.append(("5.3", "Alcohol or substance use documented as a cause."))
    elif facts["alcohol_or_substance_related"] == "unclear":
        flags.append("alcohol_link_unclear")
        reasons.append({"clause": "5.3", "text": "Alcohol documented as a possible cause; exclusion cannot be applied without medical review."})
    if facts["cosmetic"]:
        rejections.append(("5.1", "Cosmetic treatment."))
    if facts["dental"] and not facts["is_accident"]:
        rejections.append(("5.2", "Dental treatment not following an accident."))

    # ---- 2. Line-by-line payable amounts ----------------------------------------------
    lines = [Line(i["category"], i["description"], float(i["amount"]), float(i["amount"])) for i in claim["bill"]]
    for ln in lines:
        if ln.category == "non_medical":
            ln.payable, ln.reason, ln.clause = 0.0, "Non-medical item (Annexure I).", "5.5"

    room_amt = sum(l.claimed for l in lines if l.category == "room")
    if claim.get("room_days") and room_amt:
        actual_rate, eligible_rate = room_amt / claim["room_days"], 0.01 * si
        if actual_rate > eligible_rate:
            ratio = eligible_rate / actual_rate
            for ln in lines:
                if ln.category in ASSOCIATED:
                    ln.payable = round(ln.claimed * ratio, 2)
                    ln.reason = (f"Room rent {actual_rate:,.0f}/day exceeds eligible {eligible_rate:,.0f}/day (1% of SI); "
                                 f"associated expenses paid at {ratio:.1%}.")
                    ln.clause = "4.1"
            reasons.append({"clause": "4.1", "text": f"Proportionate deduction at {ratio:.1%} on room, nursing, surgeon and OT charges."})
    icu_amt = sum(l.claimed for l in lines if l.category == "icu")
    if claim.get("icu_days") and icu_amt and icu_amt / claim["icu_days"] > 0.02 * si:
        cap = 0.02 * si * claim["icu_days"]
        for ln in lines:
            if ln.category == "icu":
                ln.payable, ln.reason, ln.clause = cap, f"ICU capped at 2% of SI per day ({0.02 * si:,.0f}).", "4.1"

    payable = sum(l.payable for l in lines)
    if disease == "cataract" and payable > CATARACT_SUBLIMIT:
        reasons.append({"clause": "4.3", "text": f"Cataract sub-limit: {payable:,.0f} capped at {CATARACT_SUBLIMIT:,.0f}."})
        payable = CATARACT_SUBLIMIT
    if pol["age_at_inception"] >= 61:
        copay = round(payable * 0.20, 2)
        reasons.append({"clause": "4.2", "text": f"20% co-payment (age {pol['age_at_inception']} at inception): {copay:,.0f}."})
        payable -= copay
    if payable > pol["balance_sum_insured"]:
        reasons.append({"clause": "2.1", "text": f"Capped at balance sum insured {pol['balance_sum_insured']:,.0f}."})
        payable = float(pol["balance_sum_insured"])
    payable = round(payable, 2)
    if any(l.clause == "5.5" for l in lines):
        reasons.append({"clause": "5.5", "text": f"Non-medical items deducted: {sum(l.claimed for l in lines if l.clause == '5.5'):,.0f}."})

    if claim.get("submitted_days_after_discharge", 0) > SUBMISSION_WINDOW_DAYS:
        flags.append("late_submission")
        reasons.append({"clause": "6.1", "text": f"Submitted {claim['submitted_days_after_discharge']} days after discharge (limit {SUBMISSION_WINDOW_DAYS}); condonation decision needed."})

    # ---- 3. Decision and routing -------------------------------------------------------
    if rejections:
        reasons = [{"clause": c, "text": t} for c, t in rejections] + reasons
        decision, final = "reject", 0.0
    elif any(f.endswith("_unclear") for f in flags):
        decision, final = "refer", None
    else:
        only_non_medical = all(l.payable == l.claimed or l.clause == "5.5" for l in lines) and \
            not any(r["clause"] in ("4.2", "4.3", "2.1") for r in reasons)
        decision, final = ("approve" if only_non_medical else "partial"), payable
    if decision == "approve" and payable > AUTO_APPROVE_LIMIT:
        flags.append("high_value")
    route = "auto" if decision == "approve" and not flags else "human_review"
    return Adjudication(decision, claimed, final, payable, lines, reasons, flags, route, months_cover)
