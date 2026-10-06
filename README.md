# Generative AI & Agentic AI — Training Notebooks

Course materials for a hands-on Generative AI and Agentic AI programme: Retrieval
Augmented Generation (RAG), LangChain / LangGraph / LangSmith, and end-to-end
projects, including four built from the use cases defined in the course use-case sheet.

Every notebook runs top to bottom in **Google Colab** with nothing but an OpenAI
API key. Each folder is a stage of the course — work through them in order.

---

## Quick start

1. Open any notebook below in Colab (click the file, then the **Open in Colab**
   badge, or use `File → Open notebook → GitHub` and paste this repo's URL).
2. Run the first cell — it installs the dependencies.
3. Paste your OpenAI API key when the `getpass` prompt appears.

```bash
git clone https://github.com/<your-username>/genai-agentic-ai-training.git
```

> **Never paste an API key into a notebook cell.** Every notebook here uses
> `getpass`, which keeps the key out of the saved file. A key committed to a
> public repo is compromised within minutes and must be revoked.

---

## 01 · RAG foundations

Start here. Build a RAG system from nothing, then learn the variants and how to
measure whether any of it actually works.

| Notebook | What it covers |
|---|---|
| [RAG_Live_Class.ipynb](01-rag-foundations/RAG_Live_Class.ipynb) | The system built live in class: documents → chunk → embed → ChromaDB → search → grounded answer. Kept as taught, warts and all. |
| [RAG_Simple.ipynb](01-rag-foundations/RAG_Simple.ipynb) | The same pipeline rewritten cleanly — one dictionary per chunk instead of four parallel lists, one `search()` that also filters. Read this after the live version to see what changed and why. |
| [RAG_Types_and_Evaluation.ipynb](01-rag-foundations/RAG_Types_and_Evaluation.ipynb) | The long one, in three parts. **Part 1**: the simple build. **Part 2**: ten types of RAG — naive, hybrid, reranking, query rewriting (multi-query and HyDE), self-query, parent-document, agentic, graph — with an honest guide to choosing. **Part 3**: evaluation — building a test set, retrieval metrics, LLM-as-judge, running experiments, reading a scorecard. |

**The idea to take away:** RAG is search plus a model that writes. Most RAG
problems are search problems, so run retrieval on its own before you touch the
prompt.

---

## 02 · LangChain, LangGraph & LangSmith

Moving from a single prompt to an orchestrated, observable agent.

| Notebook | What it covers |
|---|---|
| [LangChain_LangGraph_LangSmith_Live_Class.ipynb](02-langchain-langgraph-langsmith/LangChain_LangGraph_LangSmith_Live_Class.ipynb) | The live session: installs, `ChatOpenAI`, structured output with Pydantic, and the ShopBot state graph built step by step. |
| [LangGraph_Explained.ipynb](02-langchain-langgraph-langsmith/LangGraph_Explained.ipynb) | LangGraph properly: the four primitives, partial state updates, reducers and `add_messages`, checkpointers and `thread_id`, conditional edges, the ReAct agent as a graph, human-in-the-loop gates, streaming — then two full use cases (support triage with a critic loop and a refund gate; a research assistant with a plan → gather → check → write cycle). |
| [LangGraph_LangSmith_Terminology.ipynb](02-langchain-langgraph-langsmith/LangGraph_LangSmith_Terminology.ipynb) | Every term you will hear, each pointed at a real line of code in one small case study: graph, state, node, edge, reducer, cycle, recursion limit, checkpointer, thread, snapshot, interrupt — then the LangSmith half: tracing, runs and spans, projects, feedback, datasets, evaluators, experiments. Ends with two cheat-sheet tables. |

**The idea to take away:** a chain runs once in a straight line; a graph can
loop, branch and stop to ask a human. The moment you need a retry, a critic or an
approval step, you need the graph.

---

## 03 · Projects

### [MeetingMind](03-projects/meetingmind/MeetingMind_Chroma.ipynb)

Turn raw meeting transcripts into decisions, owners and searchable team memory.
A complete project in about an hour: structured extraction with LangChain, an
action register, persistent filterable memory in ChromaDB, a LangGraph router,
and a LangSmith scorecard over four metrics.

### [PlantMate — RAG over real Word documents](03-projects/plantmate-rag/)

A graded course project with a separate solution notebook. Learners build a Q&A
assistant over three realistic corporate `.docx` policy documents that must cite
its sources and refuse when the answer is not in the corpus.

| File | Purpose |
|---|---|
| [PlantMate_Problem_Statement.ipynb](03-projects/plantmate-rag/PlantMate_Problem_Statement.ipynb) | Brief, deliverables, 100-mark rubric, seven scaffolded tasks with `TODO` stubs |
| [PlantMate_SOLUTION.ipynb](03-projects/plantmate-rag/PlantMate_SOLUTION.ipynb) | Full reference solution with evaluation harness and ablation |
| [company_docs/](03-projects/plantmate-rag/company_docs/) | The three source Word documents |

See the [project README](03-projects/plantmate-rag/README.md) for details.

### [PromptLab — prompt engineering, measured](03-projects/prompt-engineering/)

A graded prompt-engineering project with a separate solution notebook. Learners
write **two prompts for every task** — a fair control and an engineered version —
run both over labelled data, and report the difference as a number rather than an
opinion.

| File | Purpose |
|---|---|
| [PromptLab_Problem_Statement.ipynb](03-projects/prompt-engineering/PromptLab_Problem_Statement.ipynb) | Brief, deliverables, 100-mark rubric, six tasks with `TODO` stubs |
| [PromptLab_SOLUTION.ipynb](03-projects/prompt-engineering/PromptLab_SOLUTION.ipynb) | Full reference solution with metrics, cost analysis and an injection test |

Covers zero-shot, few-shot, chain-of-thought, role prompting and technique
selection. Few-shot is measured by classification accuracy and a confusion matrix
over 24 labelled support tickets; chain-of-thought is measured against unit
economics ground truth computed in Python. See the
[project README](03-projects/prompt-engineering/README.md).

---

## 04 · Use-case projects

Four end-to-end projects built from the use cases defined in the course use-case sheet. Each one brings together
the concepts covered across the curriculum modules. Each is a Python package
with a LangGraph pipeline, a Streamlit app, a Colab-ready walkthrough notebook, an evaluation script with a golden
set, and a test suite that runs without an API key. See the [section README](04-use-case-projects/README.md) for
how the other use cases in the sheet map onto them.

| Project | Use case | Highlights |
|---|---|---|
| [OpsPilot](04-use-case-projects/opspilot-devops-copilot/) | DevOps: diagnose Kubernetes, Jenkins and Terraform failures from logs | Secret redaction, hybrid RAG with RRF, human approval via `interrupt()` |
| [TriageDesk](04-use-case-projects/triagedesk-support-triage/) | Customer support: is this ticket a known issue? | Custom **MCP server**, link-following retrieval, injection and safety guardrails |
| [PRDForge](04-use-case-projects/prdforge-transcripts-to-prd/) | Product: transcripts, Slack and feedback into a PRD | Map-reduce with `Send`, conflict detection, deterministic critic + revise loop |
| [ClaimSense](04-use-case-projects/claimsense-health-claims/) | Health insurance: claim adjudication | LLM reads, rules decide, guards check every rupee, humans sign off |

---

## Colab links

The original Colab notebooks for this course. They are listed in the order they
were shared and are **not yet labelled** — the titles could not be read
automatically, so match them to the notebooks above and rename as you go.

| # | Link |
|---|---|
| 1 | https://colab.research.google.com/drive/1IHRvDgJVi4xo7AV0mi6AViYKRPLz5q9J?usp=sharing |
| 2 | https://colab.research.google.com/drive/1wBSjLGgQ6CZYuwvWrL9ptpSYxGRQTE5A?usp=sharing |
| 3 | https://colab.research.google.com/drive/1VEyQvZPHN4iIy0z6F6QYiKObU_-DHvMi?usp=sharing |
| 4 | https://colab.research.google.com/drive/1CsWXNFt2LaLO9i7TeuPXPr7LFUDT_HmD?usp=sharing |
| 5 | https://colab.research.google.com/drive/1aXQvfnviOZ9GdtM16cK2C2cke9n3Cu8J?usp=sharing |
| 6 | https://colab.research.google.com/drive/1yAga12p03Ke_hbTc2_CNoakYJ3bnbJXp?usp=sharing |
| 7 | https://colab.research.google.com/drive/10VlJMNIjDBJmoS6DbkgtrhjbE9qaLZKY?usp=sharing |
| 8 | https://colab.research.google.com/drive/1UUOFnA1H0FRz3JHE5KuthAHlabW3EHri?usp=sharing |
| 9 | https://colab.research.google.com/drive/1dJ-IfkhlpYePQ-rDybPc4E3MY5XvtwkT?usp=sharing |
| 10 | https://colab.research.google.com/drive/1HczMm9Ml7tmYNBodOipjX2CCT5V_qme9?usp=sharing |
| 11 | https://colab.research.google.com/drive/1H71jQTMfLAUdtTN15ZG9i-eQMzm54bXI?usp=sharing |
| 12 | https://colab.research.google.com/drive/16q27NvtIIdg_SriEDapxGsUL-F68SVC7?usp=sharing |
| 13 | https://colab.research.google.com/drive/1LQ9a_9k-SNP7Y9vR-GYdOV6ZvGjsRck2?usp=sharing |
| 14 | https://colab.research.google.com/drive/1VAqsYdvoiHQf6a12jwz9OV5sdVkvP8pN?usp=sharing |
| 15 | https://colab.research.google.com/drive/1fcQ0olsiiwnMP-VKcpi_gaeCPS153yfj?usp=sharing |

> These are Google Drive links. Anyone with the link can open them — check the
> sharing settings on each before circulating this repo publicly, and confirm
> none of them still contains a hard-coded API key.

---

## File name changes

Files were renamed while being organised. Original names, for matching against
your Colab links:

| Repo path | Original filename |
|---|---|
| `01-rag-foundations/RAG_Live_Class.ipynb` | `RAG_TG_Live_Class_Updated_Code.ipynb` |
| `01-rag-foundations/RAG_Simple.ipynb` | `RAG_Simple (1).ipynb` |
| `01-rag-foundations/RAG_Types_and_Evaluation.ipynb` | `RAG_Types_and_Evaluation.ipynb` |
| `02-.../LangChain_LangGraph_LangSmith_Live_Class.ipynb` | `Langchain_Langragphs_Langsmith.ipynb` |
| `02-.../LangGraph_Explained.ipynb` | `2_LangGraph_Explained.ipynb` |
| `02-.../LangGraph_LangSmith_Terminology.ipynb` | `LangGraph_LangSmith_Demo (1).ipynb` |
| `03-projects/meetingmind/MeetingMind_Chroma.ipynb` | `MeetingMind_Chroma.ipynb` |
| `03-projects/plantmate-rag/PlantMate_Problem_Statement.ipynb` | `RAG_Project_PlantMate_Problem_Statement.ipynb` |
| `03-projects/plantmate-rag/PlantMate_SOLUTION.ipynb` | `RAG_Project_PlantMate_SOLUTION.ipynb` |

---

## Requirements

Python 3.10+. Each notebook installs what it needs in its first cell:

```
openai  chromadb  python-docx  tiktoken  numpy
langchain  langchain-openai  langgraph  langsmith
```

An OpenAI API key is required. The notebooks use `gpt-4o-mini` and
`text-embedding-3-small`, which keeps a full run inexpensive.
