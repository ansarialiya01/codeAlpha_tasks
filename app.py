"""Simple URL shortener: Flask + SQLite."""
import os
import secrets
import sqlite3
import string
from urllib.parse import urlparse

from flask import Flask, g, jsonify, redirect, render_template, request

DB_PATH = os.environ.get("DB_PATH", "urls.db")
ALPHABET = string.ascii_letters + string.digits  # base62
CODE_LENGTH = 6

app = Flask(__name__)


# ---------- database ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS urls (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                code         TEXT NOT NULL UNIQUE,
                original_url TEXT NOT NULL,
                clicks       INTEGER NOT NULL DEFAULT 0,
                created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


# ---------- helpers ----------
def is_valid_url(value):
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    if any(ch.isspace() for ch in value):
        return False
    host = parsed.hostname
    return "." in host or host == "localhost"


def generate_code(db):
    """Random base62 code; retry on the (unlikely) collision."""
    for _ in range(10):
        code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
        if not db.execute("SELECT 1 FROM urls WHERE code = ?", (code,)).fetchone():
            return code
    raise RuntimeError("Could not generate a unique code")


# ---------- routes ----------
@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/shorten")
def shorten():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()

    if not url:
        return jsonify(error="Please enter a URL."), 400
    if "://" not in url:
        url = "https://" + url
    if not is_valid_url(url):
        return jsonify(error="That doesn't look like a valid http(s) URL."), 400
    if len(url) > 2048:
        return jsonify(error="URL is too long (max 2048 characters)."), 400

    db = get_db()
    code = generate_code(db)
    db.execute("INSERT INTO urls (code, original_url) VALUES (?, ?)", (code, url))
    db.commit()

    return jsonify(
        code=code,
        original_url=url,
        short_url=request.host_url + code,
    ), 201


@app.get("/api/stats/<code>")
def stats(code):
    row = get_db().execute(
        "SELECT code, original_url, clicks, created_at FROM urls WHERE code = ?",
        (code,),
    ).fetchone()
    if row is None:
        return jsonify(error="Short link not found."), 404
    return jsonify(dict(row))


@app.get("/<code>")
def follow(code):
    db = get_db()
    row = db.execute("SELECT original_url FROM urls WHERE code = ?", (code,)).fetchone()
    if row is None:
        return render_template("index.html", not_found=code), 404
    db.execute("UPDATE urls SET clicks = clicks + 1 WHERE code = ?", (code,))
    db.commit()
    return redirect(row["original_url"], code=302)


init_db()

if __name__ == "__main__":
    app.run(debug=True)
