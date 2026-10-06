"""CLI:  python -m prdforge [source_dir] [-o output/PRD.md] [--context "..."]"""
import argparse
import json
from pathlib import Path

from . import coverage, generate, render
from .config import DEFAULT_CONTEXT, OUTPUT_DIR, SOURCES_DIR


def main() -> None:
    ap = argparse.ArgumentParser(description="Turn transcripts, Slack exports and feedback into a PRD.")
    ap.add_argument("source_dir", nargs="?", default=str(SOURCES_DIR))
    ap.add_argument("-o", "--output", default=str(OUTPUT_DIR / "PRD.md"))
    ap.add_argument("--context", default=DEFAULT_CONTEXT, help="one-paragraph product context")
    ap.add_argument("--max-revisions", type=int, default=2)
    args = ap.parse_args()

    state = generate(args.source_dir, args.context, max_revisions=args.max_revisions)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(state), encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(state["prd"], indent=2), encoding="utf-8")
    print(f"Wrote {out} and {out.with_suffix('.json')}")
    print(f"Insights: {len(state['insights'])} | conflicts: {len(state['synthesis']['conflicts'])} | "
          f"stories: {len(state['prd']['user_stories'])} | evidence coverage: {coverage(state['prd'], state['evidence']):.0%}")
    print(f"Critique issues per pass: {state['issue_history']} (revisions: {state['revisions']})")


if __name__ == "__main__":
    main()
