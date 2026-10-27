/**
 * Desent API Quest — Node http mirror of FastAPI app (for Windows deploy).
 * Same routes/behavior as app/main.py.
 */
"use strict";

const http = require("http");
const { URL } = require("url");
const crypto = require("crypto");

const PORT = Number(process.env.PORT || 8000);
let authRequired = ["1", "true", "yes"].includes(
  String(process.env.AUTH_REQUIRED || "0").toLowerCase()
);
const books = new Map();
let nextId = 1;
const tokens = new Set();

function json(res, status, body) {
  const raw = body === undefined ? "" : JSON.stringify(body);
  res.writeHead(status, {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "*",
  });
  res.end(raw);
}

function noContent(res) {
  res.writeHead(204, {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "*",
  });
  res.end();
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => {
      const raw = Buffer.concat(chunks).toString("utf8").trim();
      if (!raw) return resolve({});
      try {
        resolve(JSON.parse(raw));
      } catch (e) {
        resolve({});
      }
    });
    req.on("error", reject);
  });
}

function requireAuth(req) {
  if (!authRequired) return true;
  const h = req.headers.authorization || "";
  if (!h.startsWith("Bearer ")) return false;
  const token = h.slice(7).trim();
  return tokens.has(token);
}

function listBooksFiltered(query) {
  let items = Array.from(books.values());
  if (query.author != null) {
    items = items.filter((b) => b.author === query.author);
  }
  items.sort((a, b) => {
    const ai = Number(a.id);
    const bi = Number(b.id);
    if (!Number.isNaN(ai) && !Number.isNaN(bi)) return ai - bi;
    return String(a.id).localeCompare(String(b.id));
  });
  if (query.page != null || query.limit != null) {
    const p = query.page != null && Number(query.page) > 0 ? Number(query.page) : 1;
    const lim =
      query.limit != null && Number(query.limit) > 0 ? Number(query.limit) : 10;
    const start = (p - 1) * lim;
    items = items.slice(start, start + lim);
  }
  return items;
}

const server = http.createServer(async (req, res) => {
  if (req.method === "OPTIONS") {
    res.writeHead(204, {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
      "Access-Control-Allow-Headers": "*",
    });
    return res.end();
  }

  const u = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);
  const path = u.pathname.replace(/\/$/, "") || "/";
  const q = Object.fromEntries(u.searchParams.entries());

  try {
    if (req.method === "GET" && path === "/") {
      return json(res, 200, {
        service: "desent-api-quest",
        auth_required: authRequired,
        hint: "Before Desent Level 5: POST /quest/enable-auth",
      });
    }
    if (req.method === "POST" && path === "/quest/enable-auth") {
      authRequired = true;
      return json(res, 200, { auth_required: true });
    }
    if (req.method === "POST" && path === "/quest/disable-auth") {
      authRequired = false;
      return json(res, 200, { auth_required: false });
    }
    if (req.method === "GET" && path === "/quest/status") {
      return json(res, 200, {
        auth_required: authRequired,
        books: books.size,
        tokens: tokens.size,
      });
    }
    if (req.method === "GET" && path === "/ping") {
      return json(res, 200, { success: true });
    }
    if (req.method === "POST" && path === "/echo") {
      const body = await readBody(req);
      return json(res, 200, body);
    }
    if (req.method === "POST" && path === "/auth/token") {
      const body = await readBody(req);
      if (body.username === "admin" && body.password === "password") {
        const token = crypto.randomBytes(18).toString("base64url");
        tokens.add(token);
        return json(res, 200, { token });
      }
      return json(res, 401, { detail: "Invalid credentials" });
    }

    if (req.method === "POST" && path === "/books") {
      if (!requireAuth(req)) return json(res, 401, { detail: "Unauthorized" });
      const body = await readBody(req);
      if (body.title == null || body.title === "")
        return json(res, 400, { detail: "title is required" });
      if (body.author == null || body.author === "")
        return json(res, 400, { detail: "author is required" });
      const id = String(nextId++);
      const row = {
        id,
        title: body.title,
        author: body.author,
        year: body.year ?? null,
      };
      books.set(id, row);
      return json(res, 201, row);
    }

    if (req.method === "GET" && path === "/books") {
      if (!requireAuth(req)) return json(res, 401, { detail: "Unauthorized" });
      return json(res, 200, listBooksFiltered(q));
    }

    const bookMatch = path.match(/^\/books\/([^/]+)$/);
    if (bookMatch) {
      const bookId = decodeURIComponent(bookMatch[1]);
      if (req.method === "GET") {
        if (!requireAuth(req)) return json(res, 401, { detail: "Unauthorized" });
        const book = books.get(bookId);
        if (!book) return json(res, 404, { detail: "Book not found" });
        return json(res, 200, book);
      }
      if (req.method === "PUT") {
        if (!requireAuth(req)) return json(res, 401, { detail: "Unauthorized" });
        if (!books.has(bookId))
          return json(res, 404, { detail: "Book not found" });
        const body = await readBody(req);
        if (body.title == null || body.title === "")
          return json(res, 400, { detail: "title is required" });
        if (body.author == null || body.author === "")
          return json(res, 400, { detail: "author is required" });
        const row = {
          id: bookId,
          title: body.title,
          author: body.author,
          year: body.year ?? null,
        };
        books.set(bookId, row);
        return json(res, 200, row);
      }
      if (req.method === "DELETE") {
        if (!requireAuth(req)) return json(res, 401, { detail: "Unauthorized" });
        if (!books.has(bookId))
          return json(res, 404, { detail: "Book not found" });
        books.delete(bookId);
        return noContent(res);
      }
    }

    return json(res, 404, { detail: "Not found" });
  } catch (err) {
    console.error(err);
    return json(res, 500, { detail: "Internal error" });
  }
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`desent-api-quest listening on http://0.0.0.0:${PORT}`);
});
