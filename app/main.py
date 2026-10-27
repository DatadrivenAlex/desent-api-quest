"""
Desent API Quest — FastAPI implementation.
In-memory store; clear junior/mid backend style.
"""

from __future__ import annotations

import os
import secrets
import threading
from typing import Any, Optional

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(
    title="Desent API Quest",
    description="REST API for Desent Solutions backend coding challenge",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_lock = threading.Lock()
_books: dict[str, dict[str, Any]] = {}
_next_id = 1
_tokens: set[str] = set()
# Progressive auth: off until Level 5. Override with AUTH_REQUIRED=1 at boot.
_auth_required = os.getenv("AUTH_REQUIRED", "0").strip().lower() in {"1", "true", "yes"}

ADMIN_USER = "admin"
ADMIN_PASS = "password"


class BookIn(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None


class TokenIn(BaseModel):
    username: str
    password: str


def _new_id() -> str:
    global _next_id
    with _lock:
        bid = str(_next_id)
        _next_id += 1
        return bid


def _require_auth(authorization: Optional[str]) -> None:
    if not _auth_required:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.removeprefix("Bearer ").strip()
    if token not in _tokens:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "desent-api-quest",
        "auth_required": _auth_required,
        "hint": "Before Desent Level 5: POST /quest/enable-auth",
    }


@app.post("/quest/enable-auth")
def enable_auth() -> dict[str, Any]:
    global _auth_required
    _auth_required = True
    return {"auth_required": True}


@app.post("/quest/disable-auth")
def disable_auth() -> dict[str, Any]:
    global _auth_required
    _auth_required = False
    return {"auth_required": False}


@app.get("/quest/status")
def quest_status() -> dict[str, Any]:
    return {"auth_required": _auth_required, "books": len(_books), "tokens": len(_tokens)}


@app.get("/ping")
def ping() -> dict[str, bool]:
    return {"success": True}


@app.post("/echo")
async def echo(request: Request) -> Any:
    try:
        body = await request.json()
    except Exception:
        body = {}
    if body is None:
        body = {}
    return JSONResponse(content=body, status_code=200)


@app.post("/auth/token")
def auth_token(payload: TokenIn) -> dict[str, str]:
    if payload.username == ADMIN_USER and payload.password == ADMIN_PASS:
        token = secrets.token_urlsafe(24)
        with _lock:
            _tokens.add(token)
        return {"token": token}
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/books", status_code=201)
def create_book(
    book: BookIn,
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    _require_auth(authorization)
    if book.title is None or book.title == "":
        raise HTTPException(status_code=400, detail="title is required")
    if book.author is None or book.author == "":
        raise HTTPException(status_code=400, detail="author is required")
    bid = _new_id()
    row = {"id": bid, "title": book.title, "author": book.author, "year": book.year}
    with _lock:
        _books[bid] = row
    return row


@app.get("/books")
def list_books(
    author: Optional[str] = Query(default=None),
    page: Optional[int] = Query(default=None),
    limit: Optional[int] = Query(default=None),
    authorization: Optional[str] = Header(default=None),
) -> list[dict[str, Any]]:
    _require_auth(authorization)
    with _lock:
        items = list(_books.values())
    if author is not None:
        items = [b for b in items if b.get("author") == author]
    items.sort(key=lambda b: int(b["id"]) if str(b["id"]).isdigit() else str(b["id"]))
    if page is not None or limit is not None:
        p = page if page is not None and page > 0 else 1
        lim = limit if limit is not None and limit > 0 else 10
        start = (p - 1) * lim
        items = items[start : start + lim]
    return items


@app.get("/books/{book_id}")
def get_book(
    book_id: str,
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    _require_auth(authorization)
    with _lock:
        book = _books.get(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.put("/books/{book_id}")
def update_book(
    book_id: str,
    book: BookIn,
    authorization: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    _require_auth(authorization)
    with _lock:
        if book_id not in _books:
            raise HTTPException(status_code=404, detail="Book not found")
        if book.title is None or book.title == "":
            raise HTTPException(status_code=400, detail="title is required")
        if book.author is None or book.author == "":
            raise HTTPException(status_code=400, detail="author is required")
        row = {
            "id": book_id,
            "title": book.title,
            "author": book.author,
            "year": book.year,
        }
        _books[book_id] = row
        return row


@app.delete("/books/{book_id}")
def delete_book(
    book_id: str,
    authorization: Optional[str] = Header(default=None),
) -> Response:
    _require_auth(authorization)
    with _lock:
        if book_id not in _books:
            raise HTTPException(status_code=404, detail="Book not found")
        del _books[book_id]
    return Response(status_code=204)
