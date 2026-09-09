# PlantMate — a grounded Q&A assistant over real Word documents

A graded RAG project. Learners build an assistant that answers questions **only**
from a set of corporate `.docx` policy documents, **cites** the document and
section it used, and **refuses** when the answer is not in the corpus.

## The scenario

NorthWind Energy Services (fictitious) runs process plants and deputes engineers
to client sites. Its policies live in Word documents on a shared drive. The HSE
desk, HR helpdesk and maintenance planners answer the same questions by hand
every week:

- *"Is my hot work permit still valid after a shift change?"*
- *"How much per diem do I get in Mumbai?"*
- *"Can we add this job after scope freeze?"*

A plain LLM cannot answer these — the policies were never in its training data.
Asked anyway, it will either refuse or confidently invent a number. In a plant,
an invented safety limit is a serious problem.

## Files

| File | Purpose |
|---|---|
| `PlantMate_Problem_Statement.ipynb` | The brief handed to learners: business context, six deliverables, a 100-mark rubric, and seven scaffolded tasks with `TODO` stubs and checkpoints |
| `PlantMate_SOLUTION.ipynb` | Reference solution, section-for-section against the tasks |
| `company_docs/` | The three source Word documents |

## The corpus

Three `.docx` files written the way real corporate policy is written — document
numbers, revision dates, numbered sections and hard numeric limits:

| Document | Contains |
|---|---|
| `NorthWind_HSE_Policy_Manual.docx` | Permit to work, PPE, LOTO, incident reporting, emergency response, contractor management, environmental compliance |
| `NorthWind_Leave_and_Travel_Policy.docx` | Leave entitlements, application and approval, site deputation allowances, travel entitlements, per diem, expense claims, international deputation |
| `NorthWind_Turnaround_Maintenance_SOP.docx` | Turnaround phases, scope freeze, shutdown sequence, execution control, inspection and QC, PSSR and start-up, close-out |

The solution notebook regenerates these files in its own setup cell, so it runs
in Colab with no upload. Learners are encouraged to substitute their own `.docx`
files — drop them into `company_docs/` and everything downstream works unchanged,
provided the documents use real Word Heading styles.

## What the solution demonstrates

- Heading-aware `.docx` parsing with `python-docx` (including table content)
- Section-aware chunking with overlap, splitting on paragraph then sentence
  boundaries and never across a heading
- Batched embeddings and an idempotent ChromaDB collection in cosine space
- Retrieval with top-k, metadata filtering by document, and a score threshold
- A refusal that fires **before** the LLM is called when nothing clears the
  threshold — deterministic and free
- Grounded generation with mandatory citations at `temperature=0`
- An evaluation harness over 8 questions (6 answerable, 2 that must be refused)
  reporting retrieval hit rate, answer accuracy and refusal accuracy
- An ablation that re-runs the identical evaluation against the naive
  350-character no-overlap chunker, so the chunking argument rests on a number
- Bonus: hybrid keyword + vector retrieval, and query rewriting for follow-ups

## Grading

| Criterion | Marks |
|---|---|
| Ingestion: real `.docx` parsed, headings preserved, chunking sensible | 15 |
| Chunking quality: size and overlap justified, no mid-sentence damage | 15 |
| Vector store: correct embeddings, metadata, cosine space | 10 |
| Retrieval: top-k works, metadata filter works, scores inspected | 15 |
| Generation: grounded prompt, citations present, refusal behaviour correct | 20 |
| Evaluation: all 8 eval questions run, metrics reported honestly | 15 |
| Analysis and hygiene: no hard-coded API key, clear commentary | 10 |

## A note for instructors

The solution's threshold (`MIN_SCORE = 0.30`) is a **starting value**, not a
measured constant. The notebook prints in-scope and out-of-scope similarity
scores in a probe cell; the correct threshold sits in the gap between those two
groups and shifts with the corpus and the embedding model. Run the notebook once
with your own key before teaching it so you can quote the real numbers.
