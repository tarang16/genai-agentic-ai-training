"""Score a generated PRD against data/eval/expectations.json.

    python evaluate.py                     # generate a fresh PRD (needs OPENAI_API_KEY), then score it
    python evaluate.py --prd output/PRD.json --no-generate   # score an existing PRD JSON (no API key)

Scores
  conflicts_surfaced    expected disagreements appear as decisions or open questions
  constraints_captured  compliance/data constraints cited in the Constraints section
  out_of_scope          things the sources ruled out appear as non-goals or Won't stories
  story_topics          the user needs every source agreed on became stories
  critique_clean        no deterministic review issues remain
"""
import argparse
import json
from pathlib import Path

from prdforge import critique, generate
from prdforge.config import OUTPUT_DIR, ROOT, SOURCES_DIR
from prdforge.sources import evidence_index, load_sources

EXPECT = json.loads((ROOT / "data" / "eval" / "expectations.json").read_text(encoding="utf-8"))


def _has(text: str, keywords: list[str], need_all: bool = False) -> bool:
    text = text.lower()
    return (all if need_all else any)(k in text for k in keywords)


def score(prd: dict, issues: list[str]) -> dict[str, float]:
    handled = " ".join([q["question"] for q in prd["open_questions"]] +
                       [d["decision"] + " " + d["rationale"] for d in prd["decisions"]])
    constraint_ids = {e for c in prd["constraints"] for e in c["evidence_ids"]}
    out_scope = " ".join(prd["non_goals"] + [s["i_want"] for s in prd["user_stories"] if s["priority"].startswith("Won")])
    stories = [" ".join([s["i_want"], s["so_that"]] + [a["then"] for a in s["acceptance_criteria"]])
               for s in prd["user_stories"] if not s["priority"].startswith("Won")]

    def frac(hits):
        hits = list(hits)
        return sum(hits) / len(hits)

    return {
        "conflicts_surfaced": frac(_has(handled, c["keywords"], need_all=True) for c in EXPECT["conflicts"]),
        "constraints_captured": frac(bool(constraint_ids & set(c["evidence_ids"])) for c in EXPECT["must_capture_constraints"]),
        "out_of_scope": frac(_has(out_scope, c["keywords"]) for c in EXPECT["must_be_out_of_scope"]),
        "story_topics": frac(any(_has(s, t["keywords"]) for s in stories) for t in EXPECT["must_have_story_topics"]),
        "critique_clean": float(not issues),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prd", default=str(OUTPUT_DIR / "PRD.json"))
    ap.add_argument("--no-generate", action="store_true")
    args = ap.parse_args()

    if args.no_generate:
        prd = json.loads(Path(args.prd).read_text(encoding="utf-8"))
        issues = None
    else:
        state = generate(SOURCES_DIR)
        prd, issues = state["prd"], state["issues"]
        print(f"Critique issues per pass: {state['issue_history']}")
    if issues is None:  # re-run the deterministic critic; conflicts unknown without a synthesis
        issues = critique(prd, evidence_index(load_sources(SOURCES_DIR)), {"conflicts": []}, set())
    for name, value in score(prd, issues).items():
        print(f"{name:22} {value:.2f}")
    for i in issues:
        print(f"  issue: {i}")


if __name__ == "__main__":
    main()
