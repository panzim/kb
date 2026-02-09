# Basic RAG template/demo

## Project Overview
This is a very basic RAG with chat web-interface, and a backend serving ChatGPT responses using pre-built vector DB on
a fixed set of PDF documents: PDFs in `raw-db/`, and the indexed corresponding Markdown files in `text-db/` .

## Project history and status
This project was built to address Krisp Hackathon 2025 challenge, deployed on a cloud VM, and demoed on September 14, 2025.
Later, the project repo pushed to GitHub that day was found not working (primarily for missing DB files, and failure
to rebuild those).

Around 2025-09-23 the first attempt to revive / tidy up the project was a success (after adding pre-built DB, 
most probably commit e90e82c is a good one). At that moment the project ran from a working directory,
backend started manually, frontend served from a newly added Dockerfile.

This is the second attempt to bring this project in order. The overall goal is to "land" the project: keep only
useful parts in a good working state.

## Project structure
```
.
├── uv.lock
├── pyproject.toml
├── compose.yaml
├── backend/
│  ├── Dockerfile
│  ├── serve.sh
│  ├── pyproject.toml
│  ├── basic_rag_service.py
│  ├── document_loader.py
│  ├── vector_database_facade.py
│  ├── db/
│  │  ├── documents.pkl
│  │  ├── document.vectors.faiss
│  │  └── ms-marco-TinyBERT-L-2-v2/
│  │      ├── config.json
│  │      ├── flashrank-TinyBERT-L-2-v2.onnx
│  │      ├── special_tokens_map.json
│  │      ├── tokenizer_config.json
│  │      └── tokenizer.json
│  ├── docker-run.sh
│  ├── hf.cache/
│  ├── logs/
│  └── pre-load.py
├── build-backend.sh
├── frontend
│  ├── app.py
│  ├── Dockerfile
│  ├── index.html
│  ├── pyproject.toml
│  ├── run.sh
│  └── serve.sh
├── ingest
│  ├── pdf2md.py
│  └── pdf2md-requirements.txt
├── raw-kb
│  ├── 2022_Q1_Earnings_Transcript.pdf
│  ...
│  └── Google's statement on Sept 2025 Search DOJ decision.pdf
├── text-kb
│  ├── 2022_Q1_Earnings_Transcript.md
│  ...
│  └── Google's statement on Sept 2025 Search DOJ decision.md
├── doc/
├── sample.env
├── AGENTS.md
└── Readme.md
```
### Dependency management
* The project uses `uv` for Python version and dependency management with two _workspaces_: `backend` and `frontend`
  ```toml
  # <project-root>/pyproject.toml fragment
  [tool.uv.workspace]
  members = ["backend", "frontend"]
  ```
* dependencies in `backend/pyproject.toml` and `frontend/pytproject` are believed to be OK
  (and already installed in the working directory)
* Python version is 3.13 (`flashrank` dependency in turn
  depends on `onnxruntime` for which (v1.24.0.dev20251031003) no wheels with tag `cp314` were found 2026-02-05.)

### Backend
Only relevant parts shown below:
```
backend/
   ├── serve.sh
   ├── pyproject.toml
   ├── basic_rag_service.py
   ├── document_loader.py
   ├── vector_database_facade.py
   └── db/
      ├── documents.pkl
      ├── document.vectors.faiss
      └── ms-marco-TinyBERT-L-2-v2/
```
* Backend is started with `serve.sh` script: `uvicorn basic_rag_service:app  --port=8044 --workers=1 --loop=asyncio`
* Pre-built database - `backend/db/document.vectors.faiss` (4.6 MB)
* When started backend downloaded the tokenizer model to  `ms-marco-TinyBERT-L-2-v2/`


