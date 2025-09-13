import uuid
import sqlite3
from fastapi import FastAPI, Request, Response, Cookie, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from onnx.reference.ops.op_optional import Optional
from pydantic import BaseModel
import os
import requests

app = FastAPI()

DB_FILE = os.getenv("DB_FILE", "chat.db")
BASIC_RAG_URL = os.getenv("BASIC_RAG_URL", "http://localhost:8044/chat")
KRISP_SESSION = "krisp-session"
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
    krisp_session = request.cookies.get(KRISP_SESSION)
    if krisp_session and session_exists(krisp_session):
        return {"session": krisp_session}
    session_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO sessions (session_id) VALUES (?)", (session_id,))
    conn.commit()
    conn.close()
    response.set_cookie(key="krisp-session", value=session_id, httponly=True)
    return {"session": session_id}

@app.get("/history")
def get_history(request: Request):
    krisp_session = request.cookies.get(KRISP_SESSION)
    if not krisp_session or not session_exists(krisp_session):
        raise HTTPException(status_code=401, detail="No valid session")
    return get_messages(krisp_session)

@app.post("/chat")
def chat(request: Request, userMessageRequest: UserMessageRequest):
    krisp_session = request.cookies.get(KRISP_SESSION)
    if not krisp_session or not session_exists(krisp_session):
        raise HTTPException(status_code=401, detail="No valid session")

    add_message(krisp_session, ROLE_USER, userMessageRequest.user_message)
    chat_request = {"messages": get_messages(krisp_session)}
    reply = requests.post(BASIC_RAG_URL, json=chat_request).json()['reply']
    add_message(krisp_session, ROLE_BOT, reply)
    return {"reply": reply}