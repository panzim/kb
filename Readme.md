# Panzim: An AI-Powered Knowledge Base Chat App

This is a prototype of an AI-enabled chat application designed to interact with a knowledge base of corporate documents.

## Running Panzim
0. copy `sample.env` to `.env` and put your OpenAI API key there, or `export OPENAI_API_KEY=<your-OpenAI-key>`
1. install dependencies: `pip  install -r requirements.txt`
2. run backend: `uvicorn backend.rag:app  --port=8044 --workers=1 --loop=asyncio`
3. run frontend (new terminal): `uvicorn frontend.app:app`

Open http://localhost:8000

Checked OK 2026-02-07 (Python 3.13/3.14)  See [doc/demo*.*](doc/)
