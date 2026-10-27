#!/usr/bin/env python3
"""Local mirror of Desent API Quest checks (from coding-test-backend JS)."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")


def call(path: str, method: str = "GET", body=None, headers=None):
    data = None
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    if body is not None:
        data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers=hdrs, method=method)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            status = resp.status
            try:
                parsed = json.loads(raw.decode() or "null")
            except Exception:
                parsed = raw.decode() if raw else None
    except urllib.error.HTTPError as e:
        status = e.code
        raw = e.read()
        try:
            parsed = json.loads(raw.decode() or "null")
        except Exception:
            parsed = raw.decode() if raw else None
    ms = int((time.time() - t0) * 1000)
    return status, parsed, ms


def check(name, passed, msg=""):
    mark = "PASS" if passed else "FAIL"
    print(f"  [{mark}] {name}" + (f" — {msg}" if msg else ""))
    return passed


def main():
    state = {"bookIds": [], "authToken": None}
    all_ok = True

    print("Level 1 Ping")
    st, data, ms = call("/ping")
    all_ok &= check("GET /ping 200", st == 200, str(st))
    all_ok &= check("success true", isinstance(data, dict) and data.get("success") is True, str(data))

    print("Level 2 Echo")
    payload = {"message": "hello", "number": 42, "nested": {"key": "val"}}
    st, data, ms = call("/echo", "POST", payload)
    all_ok &= check("POST /echo 200", st == 200)
    all_ok &= check("body match", data == payload, str(data)[:80])
    st, data, ms = call("/echo", "POST", {})
    all_ok &= check("empty {}", st == 200 and data == {})

    print("Level 3 CRUD create/read")
    st, data, ms = call("/books", "POST", {"title": "Dune", "author": "Frank Herbert", "year": 1965})
    all_ok &= check("POST 201", st == 201, str(st))
    bid = data.get("id") if isinstance(data, dict) else None
    if bid:
        state["bookIds"].append(str(bid))
    all_ok &= check("has id", bool(bid), str(data))
    call("/books", "POST", {"title": "Neuromancer", "author": "William Gibson", "year": 1984})
    st, data, ms = call("/books")
    all_ok &= check("GET array", isinstance(data, list), type(data).__name__)
    st, data, ms = call(f"/books/{bid}")
    all_ok &= check("GET by id Dune", st == 200 and isinstance(data, dict) and data.get("title") == "Dune")

    print("Level 4 update/delete")
    d = state["bookIds"][0]
    st, data, ms = call(
        f"/books/{d}", "PUT", {"title": "Dune (Updated)", "author": "Frank Herbert", "year": 1965}
    )
    all_ok &= check(
        "PUT 200", st == 200 and isinstance(data, dict) and data.get("title") == "Dune (Updated)"
    )
    st, data, ms = call(f"/books/{d}")
    all_ok &= check("persisted", isinstance(data, dict) and data.get("title") == "Dune (Updated)")
    st, data, ms = call(f"/books/{d}", "DELETE")
    all_ok &= check("DELETE 200/204", st in (200, 204), str(st))
    st, data, ms = call(f"/books/{d}")
    all_ok &= check("GET deleted 404", st == 404)

    print("Enable auth (before Level 5)")
    call("/quest/enable-auth", "POST", {})

    print("Level 5 Auth")
    st, data, ms = call("/books")
    all_ok &= check("no token 401", st == 401, str(st))
    st, data, ms = call("/auth/token", "POST", {"username": "admin", "password": "password"})
    all_ok &= check("token 200", st == 200 and isinstance(data, dict) and bool(data.get("token")))
    token = data.get("token") if isinstance(data, dict) else None
    state["authToken"] = token
    auth = {"Authorization": f"Bearer {token}"}
    st, data, ms = call("/books", headers=auth)
    all_ok &= check("with token 200", st == 200, str(st))
    st, data, ms = call("/auth/token", "POST", {"username": "admin", "password": "wrong"})
    all_ok &= check("wrong 401", st == 401)

    print("Level 6 search/paginate")
    for body in [
        {"title": "1984", "author": "George Orwell", "year": 1949},
        {"title": "Animal Farm", "author": "George Orwell", "year": 1945},
        {"title": "Brave New World", "author": "Aldous Huxley", "year": 1932},
    ]:
        call("/books", "POST", body, auth)
    st, data, ms = call("/books?author=George%20Orwell", headers=auth)
    all_ok &= check("author filter array", isinstance(data, list) and len(data) >= 2)
    all_ok &= check(
        "all Orwell",
        isinstance(data, list) and all(b.get("author") == "George Orwell" for b in data),
    )
    st, p1, ms = call("/books?page=1&limit=2", headers=auth)
    all_ok &= check("page1 <=2", isinstance(p1, list) and len(p1) <= 2)
    st, p2, ms = call("/books?page=2&limit=2", headers=auth)
    all_ok &= check(
        "page2 differs",
        isinstance(p2, list) and isinstance(p1, list) and json.dumps(p1) != json.dumps(p2),
    )

    print("Level 7 errors")
    st, data, ms = call("/books", "POST", {"author": "Nobody", "year": 2000}, auth)
    all_ok &= check("no title 400", st == 400)
    st, data, ms = call("/books", "POST", {"title": "No Author Book", "year": 2000}, auth)
    all_ok &= check("no author 400", st == 400)
    st, data, ms = call("/books/nonexistent-id-99999", headers=auth)
    all_ok &= check("GET missing 404", st == 404)
    st, data, ms = call(
        "/books/nonexistent-id-99999",
        "PUT",
        {"title": "Ghost", "author": "Nobody", "year": 2000},
        auth,
    )
    all_ok &= check("PUT missing 404", st == 404)

    print("Level 8 speed <500ms")
    tests = [
        ("ping", "/ping", "GET", None, None, 200),
        ("echo", "/echo", "POST", {"speed": True}, None, 200),
        (
            "post books",
            "/books",
            "POST",
            {"title": "Speed Book", "author": "Fast Author", "year": 2024},
            auth,
            201,
        ),
        ("get books", "/books", "GET", None, auth, 200),
        (
            "token",
            "/auth/token",
            "POST",
            {"username": "admin", "password": "password"},
            None,
            200,
        ),
    ]
    for name, path, method, body, hdrs, expect in tests:
        st, data, ms = call(path, method, body, hdrs)
        all_ok &= check(f"{name} {expect} <500ms", st == expect and ms < 500, f"{st} {ms}ms")

    print("\nALL OK" if all_ok else "\nSOME FAILED")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
