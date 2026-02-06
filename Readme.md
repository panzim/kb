# Panzim: An AI-Powered Knowledge Base Chat App

This is a prototype of an AI-enabled chat application designed to interact with a knowledge base of corporate documents.

## Running Panzim
0. copy `sample.env` to `.env` and put your OpenAI API key there, or export that in the OPENAI_API_KEY environment variable
1. install dependencies: `pip -r requirements.txt`
2. run backend: `uvicorn utils.basic_rag_service:app  --port=8044 --workers=1 --loop=asyncio`
3. run frontend (new terminal): `uvicorn frontend.app:app --host 0.0.0.0`

Open http://localhost:8000

Steps 2-3 checked OK 2026-02-06 (Python 3.13)  See [doc/demo*.*](doc/)
