# Personalized Conference Paper Explorer — Design Doc

_A single-user web app to rank conference papers by semantic similarity to your own “seed” papers, with cached summaries, basic filters, and fortnightly re-ranking. Deployable on Heroku Eco plan._

---

## 1. Overview

- **Goal**: Ingest ~20 “seed” PDFs + ~100 conference PDFs, embed full text in 10 000-token chunks, rank corpus by average cosine similarity to seeds, display top-N with cached LLM summaries and basic filters (year, author, keywords).  
- **Cadence**  
  - **Monthly ingestion** (“full run”): parse + embed all seeds & corpus → upsert.  
  - **Fortnightly re-rank**: recompute similarity & ranking; reuse embeddings.  
- **Cost**: ≈ \$0.19/month (embeddings + summaries) + \$5–10 Heroku dynos + minimal S3 & Postgres.

---

## 2. Tech Stack

| Layer                | Technology                         |
|----------------------|------------------------------------|
| **Frontend**         | React (vite), Tailwind CSS         |
| **API & Backend**    | Python 3.11, FastAPI               |
| **PDF Parsing**      | PyMuPDF (fitz)                     |
| **Embeddings**       | OpenAI `text-embedding-3-large`    |
| **Vector Database**  | Pinecone Starter (free)            |
| **Relational Store** | Heroku Postgres (Hobby Dev)        |
| **Object Storage**   | AWS S3                              |
| **Scheduler**        | Heroku Scheduler                   |
| **Hosting**          | Heroku Eco Dynos                   |
| **CI/CD**            | GitHub Actions                     |
| **Logging/Monitor**  | Sentry (errors), LogDNA (logs)     |

---

## 3. High-Level Architecture

┌─────────────┐        ┌──────────────┐        ┌───────────────┐
│  React SPA  │ ◀────▶ │  FastAPI API │ ◀────▶ │    Backend    │
│ (Frontend)  │        │  (Heroku)     │        │  (Worker)     │
└───▲────▲────┘        └─────▲────────┘        └─────▲─────────┘
│    │                   │                       │
│    │                   │                       │
│    │                   │                       │
│    │    ┌───────────┐  │   ┌─────────────┐     │
└────┴───▶│ Pinecone  │◀─┴──▶│ OpenAI API  │     │
└───────────┘      └─────────────┘     │
┌───────────┐                          │
│ Postgres  │◀─────────────────────────┘
└───────────┘
┌───────────┐
│   S3      │
└───────────┘

---

## 4. Component Breakdown

### 4.1 Frontend (React + Tailwind)

- **Pages/Views**  
  1. **Upload** – drag/drop or “Select PDFs” for seeds & corpus.  
  2. **Dashboard** –  
     - Ranked list (sortable by score).  
     - Filters: text-search (title/author/venue), year range.  
     - “Regenerate summaries” button.  
- **State**  
  - Upload progress & status.  
  - Last-run timestamp.  
  - Filter & sort settings.  

### 4.2 API Layer (FastAPI)

- **Endpoints**  
  - `POST /api/ingest`  
    - Body: none (reads S3 bucket or local `/uploads/`).  
    - Action: parse + chunk + embed seeds & corpus; upsert Pinecone & Postgres tables.  
  - `GET  /api/rank?filters…`  
    - Query: `year_min`, `year_max`, `author`, `keywords`, `top_n` (default = 20).  
    - Action:  
      1. Fetch seed & corpus vectors from Pinecone.  
      2. Compute cosine(seeds,candidate) → average score.  
      3. Apply filters via Postgres metadata.  
      4. Return sorted list of `{ paperId, title, authors, year, venue, score }`.  
  - `GET  /api/summary/{paperId}`  
    - Action: lookup Postgres cache; if miss, call OpenAI chat API for ~200-token summary, store & return.  

- **Auth**: none (single-user). Optional API key check.

### 4.3 Background Worker / Tasks

- **tasks.py** (called by Heroku Scheduler)  
  - `ingest`: same logic as `/api/ingest` but headless, logs to Sentry.  
  - `rank`: pre-compute ranking & optionally pre-fetch summaries.  

### 4.4 Data Stores

- **Pinecone**  
  - **Index**: `papers`  
    - Vector dims = 3072  
    - Metadata: `paperId`  
- **Postgres**  
  - **Table: papers**  
    ```sql
    CREATE TABLE papers (
      paper_id    TEXT PRIMARY KEY,
      title       TEXT NOT NULL,
      authors     TEXT[],
      year        INT,
      venue       TEXT,
      keywords    TEXT[],
      s3_key      TEXT  -- PDF location
    );
    ```
  - **Table: summaries**  
    ```sql
    CREATE TABLE summaries (
      paper_id    TEXT PRIMARY KEY REFERENCES papers(paper_id),
      summary     TEXT NOT NULL,
      generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    ```
- **S3**  
  - Bucket: `my-app-papers`  
  - Folder structure:  
    ```
    seeds/   → 20 seed PDFs
    corpus/  → 100 conference PDFs
    ```

---

## 5. Data Flow

1. **Upload** PDF files via frontend → POST to S3 (`/seeds` or `/corpus`).  
2. **Monthly ingest** (Scheduler → `tasks.py ingest`):  
   - List S3 objects under `seeds/` & `corpus/`.  
   - For each PDF:  
     - Download → PyMuPDF extract full text.  
     - Split into 10 000-token chunks.  
     - Call OpenAI embed API per chunk → get 3072-d vector.  
     - Upsert each chunk into Pinecone with `paperId` metadata.  
   - Write/UPDATE Postgres `papers` rows.  
3. **Fortnightly rank** (Scheduler → `tasks.py rank` or user hits “Re-rank”):  
   - Fetch all seed & corpus vectors from Pinecone.  
   - Compute average cosine similarity per paper.  
   - Store last-run scores (optional) or return on-demand.  
4. **Summary on-demand** (`/api/summary/{paperId}`):  
   - Query Postgres `summaries`.  
   - If not found:  
     - Retrieve paper abstract or 2–3 chunks.  
     - Call OpenAI Chat API with prompt:  
       ```
       “Summarize the key contributions and methods of the following paper in ~200 words: …”
       ```  
     - Save to `summaries` table.  

---

## 6. Deployment on Heroku (Eco Plan)

### 6.1 Procfile

```text
web:   uvicorn api:app --host=0.0.0.0 --port=${PORT:-8000}

(No dedicated worker dyno: use Scheduler-run CLI.)

6.2 Heroku Add-ons & Config

heroku addons:create heroku-postgresql:hobby-dev
heroku addons:create scheduler:standard

Set Config Vars:

KEY	VALUE
OPENAI_API_KEY	(your OpenAI key)
PINECONE_API_KEY	(your Pinecone key)
PINECONE_ENV	(e.g. “us-west1-gcp”)
AWS_ACCESS_KEY_ID	(S3 IAM user)
AWS_SECRET_ACCESS_KEY	(S3 IAM user secret)
S3_BUCKET	my-app-papers

6.3 Scheduler Jobs

In Heroku Dashboard → Scheduler:

Frequency	Command
Daily	python tasks.py ingest (or monthly if preferred)
Every 2 weeks	python tasks.py rank


⸻

7. CI/CD & Testing
	•	GitHub Actions pipeline:
	1.	lint (flake8, isort)
	2.	unit tests (pytest, coverage)
	3.	build React (npm ci && npm run build)
	4.	deploy to Heroku on main branch
	•	Secrets: store Heroku API key, AWS creds, OpenAI & Pinecone keys in GitHub Secrets.

⸻

8. Monitoring & Logging
	•	Sentry (Python/JS SDK): capture API & background errors.
	•	LogDNA: aggregate Heroku logs (optional).
	•	Health check endpoint: GET /api/health → { status: "ok", uptime: … }

⸻

9. Next Steps
	1.	Write API OpenAPI spec and share with frontend team.
	2.	Scaffold directories:

/api/        ← FastAPI app
/frontend/   ← React SPA
/tasks.py    ← CLI for ingest & rank
/utils/      ← PDF parser, embed wrapper, Pinecone client


	3.	Provision S3 bucket & IAM.
	4.	Implement ingestion, ranking, summary caching.
	5.	Build minimal frontend: upload + list.
	6.	Iterate on filters & UI polish.

⸻