#!/bin/sh
PATH=../.venv/bin
uvicorn basic_rag_service:app  --port=8044 --workers=1 --loop=asyncio
