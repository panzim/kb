#!/usr/bin/env python3
import os
import time
from typing import List, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from pydantic import BaseModel
from langchain_core.documents import Document
import openai

from utils.vector_database_facade import VectorDatabaseFacade
from utils.document_loader import DocumentLoader

import logging

logger = logging.getLogger("uvicorn")

formatter = logging.Formatter(
    fmt="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

logpath = os.path.join(os.path.curdir, 'logs', 'basic_rag_service.log')
file_handler = logging.FileHandler(logpath, mode="a")
file_handler.setFormatter(formatter)

# Root logger config
logging.basicConfig(level=logging.INFO, handlers=[console_handler, file_handler])

handler = logging.getLogger("uvicorn").handlers[0]
handler.setFormatter(formatter)
logging.getLogger("uvicorn").handlers.append(file_handler)

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = "gpt-4o-mini" # 'gpt-5-nano'
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found")
DATABASE_PATH = os.getenv('DATABASE_PATH', os.path.join(os.path.curdir, 'db'))

app = FastAPI()
openai_client = openai.Client(api_key=OPENAI_API_KEY)
logger.warning("RAG loading started")
document_loader = DocumentLoader()
vector_database_facade = VectorDatabaseFacade(
    database_directory=DATABASE_PATH,
    embedding_model=document_loader.model
)
vector_database_facade.load()
logger.warning("RAG is ready")

class Message(BaseModel):
    text: str
    sender: str

class ChatRequest(BaseModel):
    messages: List[Message]

def build_chat_messages(messages: List[Message], docs: List[Document]) -> List[Dict[str, object]]:
    """
    Build the OpenAI API messages array from chat history and retrieved docs.
    """
    openai_messages = []

    # Convert chat history
    for m in messages:
        role = "user" if m.sender == "user" else "assistant"
        openai_messages.append({"role": role, "content": m.text})

    # Add retrieved docs as context
    if docs:
        context_text = "\n\n".join(
            f"[Source: {doc.metadata.get('source', 'unknown')}]\n{doc.page_content}"
            for doc in docs
        )
        openai_messages.append({
            "role": "system",
            "content": f"Knowledge base context:\n{context_text}\n\nUse this to help answer the user."
        })

    return openai_messages


def chat_with_openai(messages: List[Message], docs: List[Document]) -> str:
    openai_messages = build_chat_messages(messages, docs)
    logger.info("[DEBUG] OpenAI messages: %s" % str(openai_messages))

    response = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=openai_messages,
        temperature=0.2,
    )

    return response.choices[0].message.content

@app.get("/")
async def read_index():
    return {"status": "ok"}

@app.post("/chat")
def chat(request: Request, chatRequest: ChatRequest):
    last_message = chatRequest.messages[-1].text
    logger.info("Chat request: %s" % last_message)
    docs_with_scores = vector_database_facade.query(last_message)
    logger.info("Documents retrieved from RAG: %d" % len(docs_with_scores))

    if docs_with_scores:
        docs = [d for d,_ in docs_with_scores]
        sources = []
        for d, score in docs_with_scores:
            logger.info("Documents %s scores: %.4f" % (d.metadata.get('source'), score))
            if d.metadata.get('source') and not (d.metadata.get('source')  in sources):
                sources.append(d.metadata.get('source') )
        logger.info("Documents length from RAG: %d" % sum([len(d.page_content) for d in docs]))
        t = time.time()
        reply: str = chat_with_openai(messages=chatRequest.messages, docs=docs)
        logger.info("[BENCHMARK] OpenAI request: %.2f" % (time.time() - t))
        return {"reply": reply, "sources": sources}
    else:
        return {}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("basic_rag_service:app", host="0.0.0.0", port=8044, reload=False, workers=1, loop='asyncio')