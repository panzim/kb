import os
import logging
import time
import uuid
import sqlite3
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests


logger = logging.getLogger("uvicorn")
formatter = logging.Formatter(
    fmt="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

log_path = os.path.join(os.path.curdir, '.', 'logs', 'frontend.log')
file_handler = logging.FileHandler(log_path, mode="a")
file_handler.setFormatter(formatter)

logging.basicConfig(level=logging.INFO, handlers=[console_handler, file_handler])

handler = logging.getLogger("uvicorn").handlers[0]
handler.setFormatter(formatter)
logging.getLogger("uvicorn").handlers.append(file_handler)

app = FastAPI()

DB_FILE = os.getenv("DB_FILE", "chat.db")
BASIC_RAG_URL = os.getenv("BASIC_RAG_URL", "http://localhost:8044/chat")
SESSION_COOKIE = "pnzm-session"
ROLE_USER = "user"
ROLE_BOT = "bot"

# --- Database setup ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id VARCHAR PRIMARY KEY
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id VARCHAR,
            sender TEXT,
            text TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(session_id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

class UserMessageRequest(BaseModel):
    user_message: str

# --- Helpers ---
def session_exists(session_id: str) -> bool:
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists

def get_messages(session_id: str, limit: int = 100):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT sender, text FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?", (session_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [{"sender": r[0], "text": r[1]} for r in reversed(rows)]

def add_message(session_id: str, sender: str, text: str):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (session_id, sender, text) VALUES (?, ?, ?)",
        (session_id, sender, text)
    )
    conn.commit()
    conn.close()

# --- Endpoints ---

@app.get("/")
async def read_index():
    # Path to index.html in the same directory as app.py
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return FileResponse(os.path.join(base_dir, "index.html"))

@app.post("/session")
def create_session(request: Request, response: Response):
    sess_id: str | None = request.cookies.get(SESSION_COOKIE)
    if sess_id and session_exists(sess_id):
        return {"session": sess_id}
    session_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO sessions (session_id) VALUES (?)", (session_id,))
    conn.commit()
    conn.close()
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {"session": session_id}

@app.get("/history")
def get_history(request: Request):
    sess_id = request.cookies.get(SESSION_COOKIE)
    if not sess_id or not session_exists(sess_id):
        raise HTTPException(status_code=401, detail="No valid session")
    return get_messages(sess_id)

@app.post("/chat")
def chat(request: Request, user_message_request: UserMessageRequest):
    sess_id = request.cookies.get(SESSION_COOKIE)
    if not sess_id or not session_exists(sess_id):
        raise HTTPException(status_code=401, detail="No valid session")

    t1 = time.time()
    add_message(sess_id, ROLE_USER, user_message_request.user_message)
    chat_request = {"messages": get_messages(sess_id)}
    logger.info("[BENCHMARK] database read write: %.2f" % (time.time() - t1))

    t2 = time.time()
    try:
        response = requests.post(BASIC_RAG_URL, json=chat_request).json()
        logger.info("[BENCHMARK] Basic RAG response: %.2f" % (time.time() - t2))
        if 'reply' in response:
            add_message(sess_id, ROLE_BOT, response['reply'])
            sources = response.get('sources') or []
            return {"reply": response['reply'], "sources": sources}
        else:
            return {}
    except Exception as ex:
        error = str(ex)
        logger.info("[BENCHMARK] Basic RAG error: %.2f" % (time.time() - t2))
        if len(error) > 200:
            return {"error": "Server error: " + error[:200] + "..."}
        else:
            return {"error": "Server error: " + error}
