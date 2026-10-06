"""CLI:  python -m opspilot data/incidents/01_payments_oomkilled.log [--approve | --reject] [--offline-retrieval]"""
import argparse
import uuid
from pathlib import Path

from langgraph.types import Command

from . import create_app, render


def main() -> None:
    ap = argparse.ArgumentParser(description="Diagnose an incident log against the runbooks.")
    ap.add_argument("log_file")
    decision = ap.add_mutually_exclusive_group()
    decision.add_argument("--approve", action="store_true", help="approve state-changing steps without prompting")
    decision.add_argument("--reject", action="store_true", help="reject state-changing steps without prompting")
    ap.add_argument("--offline-retrieval", action="store_true", help="BM25 only, no embedding calls")
    args = ap.parse_args()

    app = create_app(offline_retrieval=args.offline_retrieval)
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    state = app.invoke({"log": Path(args.log_file).read_text(encoding="utf-8")}, config)

    if "__interrupt__" in state:
        print(render(state))
        print("\nProposed state-changing commands:")
        for cmd in state["__interrupt__"][0].value["commands"]:
            print(f"  $ {cmd}")
        if args.approve or args.reject:
            ok = args.approve
        else:
            ok = input("\nApprove? [y/N] ").strip().lower() == "y"
        state = app.invoke(Command(resume={"approved": ok, "approver": "cli-user"}), config)

    print(render(state))


if __name__ == "__main__":
    main()
