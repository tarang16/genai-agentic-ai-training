# 04 · Use-case projects

These four projects are built from the use cases defined in the course use-case sheet. Each one is a complete,
runnable reference implementation of a real business problem, and each brings together the concepts covered across
the curriculum modules: prompt engineering, structured output, RAG, LangChain and LangGraph, guardrails, MCP and
evaluation.

| Project | Use case | What it does | Key techniques |
|---|---|---|---|
| [**OpsPilot**](opspilot-devops-copilot/) | Cloud & DevOps troubleshooting assistant; Jenkins pipeline failure diagnosis | Diagnoses Kubernetes, Jenkins and Terraform failures from logs against your runbooks; any state-changing fix waits for human approval | Secret redaction, hybrid BM25 + vector RAG with RRF, small-to-big retrieval, LangGraph `interrupt()` |
| [**TriageDesk**](triagedesk-support-triage/) | Customer-support triage over Freshdesk, Jira and KB articles | Decides whether a new ticket is a known issue, a known bug or new; drafts a grounded reply | **Custom MCP server**, query rewriting, link-following retrieval, injection and safety guardrails |
| [**PRDForge**](prdforge-transcripts-to-prd/) | Meeting transcripts, Slack threads and feedback into a PRD | Produces a PRD with user stories, Given/When/Then criteria and full traceability | LangGraph map-reduce (`Send`), conflict detection, deterministic critic + revise loop |
| [**ClaimSense**](claimsense-health-claims/) | Health insurance and claims processing | Adjudicates health claims: the LLM reads the discharge summary, rules compute every rupee with a clause, guards check the letter, a human signs off | PII redaction, clause-level RAG, LLM + rules hybrid, risk-based routing |

Each project folder has the same shape:

```
README.md                 problem, architecture, design decisions, how to adapt it
<package>/                the code (LangGraph graph, schemas, guardrails, retrieval)
app.py                    Streamlit UI            ->  streamlit run app.py
<Name>_Walkthrough.ipynb  step-by-step notebook (Colab-ready; cells marked LIVE need an API key)
evaluate.py               metrics on a labelled golden set (--offline mode needs no key)
tests/                    pytest suite with fake LLMs: runs with no API key
data/                     realistic synthetic data, including the hard cases
```

## Running any project

```bash
cd 04-use-case-projects/<project>
pip install -r requirements.txt
pytest -q                     # no API key needed
python evaluate.py --offline  # (OpsPilot, TriageDesk, ClaimSense)
export OPENAI_API_KEY=...     # or copy .env.example to .env
streamlit run app.py
```

All projects default to `gpt-4o-mini` (and `text-embedding-3-small` in OpsPilot). A full evaluation run of any
project costs a few cents.

## What every project has in common

These are the habits the curriculum builds, applied four different ways:

1. **Deterministic first.** Regex, rules and arithmetic run as code. The model handles what only a model can:
   reading messy text and writing for humans.
2. **Grounded or nothing.** Every model claim cites an id (runbook section, ticket, evidence line, policy clause) and
   code checks that the id exists. Ungrounded answers are dropped or escalated.
3. **Sensitive data never leaves unredacted.** Secrets in logs, customer PII in tickets, names in transcripts,
   patient identifiers in discharge summaries.
4. **The model proposes, code and humans dispose.** Safety gates are graph edges and Python checks, not sentences in
   a prompt.
5. **Measured, not eyeballed.** Each project ships a golden set and an `evaluate.py`.

## Other use cases in the sheet

Several other use cases in the sheet are close to one of these four, and can start from it:

| Use case | Start from | What to change |
|---|---|---|
| Find the latest OpenJDK / JBoss patch, download it and trigger Ansible automation | OpsPilot | Replace runbook RAG with tools that query the vendor errata API; keep the approval gate before any download or Ansible run |
| Log analyser integrated with Salesforce, Confluence and Jira | OpsPilot + TriageDesk | OpsPilot's log parsing, TriageDesk's MCP server pattern for each system |
| Shift-handover chatbot over bug-tracker and change-list data (telecom packet core) | TriageDesk | MCP tools over the bug tracker; a nightly job that summarises the shift with PRDForge-style evidence ids |
| Secure enterprise assistant over Microsoft 365, Entra ID and Intune | TriageDesk | MCP server over Microsoft Graph with read-only scopes; write tools behind approval |
| HLD / LLD drafting for VMware VCF, Nutanix and PowerFlex | PRDForge | Sources become requirement workshops and vendor sizing guides; the schema becomes an HLD; the critic checks every component has sizing, HA and a cited source |
| CI/CD pipeline automation via Git (Azure DevOps, Bitbucket, Jenkins) | OpsPilot | Add GitHub Actions / Azure Pipelines signatures and runbooks |
| Pharma and crop-science use cases | PRDForge or ClaimSense | PRDForge for requirements work; ClaimSense's "LLM reads, rules decide" pattern for regulatory checks |
| ERP-style assistant for site material, billing and store data | PRDForge (schemas) | Structured extraction from field-team messages into tables; add a text-to-SQL agent over the store data |
| Playwright / Selenium test automation | PRDForge | Generate Playwright tests from the Given/When/Then acceptance criteria PRDForge produces |
| Autonomous networks (zero touch, zero wait, zero trouble) | OpsPilot | Same detect -> diagnose -> approve -> act loop, with network telemetry instead of logs |
| GRC / cyber security and cloud application operations | OpsPilot / ClaimSense | Control checks as deterministic rules with clause citations, LLM for reading evidence |
