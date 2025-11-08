import os
import logging
from datetime import datetime

import requests
from flask import Flask, jsonify, send_from_directory, request, abort
from flask_cors import CORS
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from .config import Config
from .models import Base, Branch, BookGlobal, BookAvailability, UserCentral

# ---------------------------------------------------------
# Logging (so you can see sync calls in the terminal)
# ---------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Flask + DB setup
# ---------------------------------------------------------

app = Flask(__name__, static_folder=None)
app.config.from_object(Config)
CORS(app)

engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"], future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Create tables if not present
Base.metadata.create_all(engine)

# ---------------------------------------------------------
# Frontend serving
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(FRONTEND_DIR, path)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def require_api_key(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        expected = app.config.get("SERVICE_API_KEY")
        sent = request.headers.get("X-API-Key")
        if expected and sent != expected:
            logger.warning("Invalid API key on %s", request.path)
            abort(401, description="Invalid or missing service API key")
        return func(*args, **kwargs)

    return wrapper


# ---------------------------------------------------------
# Health
# ---------------------------------------------------------

@app.get("/api/health")
def health_check():
    return jsonify({"status": "ok", "service": "central_service"}), 200

@app.post("/api/users")
def create_user_central():
    """
    Create or update a user in the central DB and fan out to all branches.

    Request JSON:
      {
        "external_id": "123",
        "name": "Alice Example",
        "email": "alice@example.com",
        "home_branch": "DOWNTOWN_TORONTO"  # optional
      }
    """
    data = request.get_json(force=True)
    external_id = data.get("external_id")
    name = data.get("name")
    email = data.get("email")
    home_branch = data.get("home_branch")

    if not external_id or not name or not email:
        abort(400, description="external_id, name, email are required")

    # 1) Upsert into central user table
    session = SessionLocal()
    try:
        q = select(UserCentral).where(UserCentral.external_id == external_id)
        user = session.execute(q).scalar_one_or_none()

        if user:
            user.name = name
            user.email = email
            if home_branch:
                user.home_branch = home_branch
            created = False
            logger.info("Updated central user %s", external_id)
        else:
            user = UserCentral(
                external_id=external_id,
                name=name,
                email=email,
                home_branch=home_branch,
                created_at=datetime.utcnow(),
            )
            session.add(user)
            created = True
            logger.info("Created central user %s", external_id)

        session.commit()
    finally:
        session.close()

    # 2) Fan out to every registered branch
    session = SessionLocal()
    try:
        branches = session.execute(select(Branch)).scalars().all()
    finally:
        session.close()

    payload = {
        "external_id": external_id,
        "name": name,
        "email": email,
        "home_branch": home_branch,
    }

    branch_results = []
    for b in branches:
        try:
            url = f"{b.base_url.rstrip('/')}/api/users"
            resp = requests.post(url, json=payload, timeout=5)
            branch_results.append(
                {
                    "branch_code": b.code,
                    "status": resp.status_code,
                    "ok": resp.ok,
                }
            )
            logger.info(
                "Synced user %s to %s -> %s",
                external_id,
                b.code,
                resp.status_code,
            )
        except Exception as e:
            logger.warning("Failed to sync user %s to %s: %s", external_id, b.code, e)
            branch_results.append(
                {
                    "branch_code": b.code,
                    "status": "error",
                    "ok": False,
                    "error": str(e),
                }
            )

    return (
        jsonify(
            {
                "external_id": external_id,
                "created": created,
                "branches": branch_results,
            }
        ),
        201 if created else 200,
    )




@app.post("/api/login")
def login_user():
    """
    Simple login:
    - expects JSON: {"user_external_id": "..."}
    - checks UserCentral
    - returns a demo "access_token" plus basic user info
    """
    data = request.get_json(force=True)
    external_id = data.get("user_external_id")

    if not external_id:
        return jsonify({"error": "Please enter your library ID."}), 400

    session = SessionLocal()
    try:
        user = (
            session.execute(
                select(UserCentral).where(UserCentral.external_id == external_id)
            )
            .scalar_one_or_none()
        )

        if not user:
            return jsonify(
                {
                    "error": (
                        "We couldn't find that library ID. "
                        "Ask a librarian to register you first."
                    )
                }
            ), 404

        # For the demo, the token is just a string derived from the ID.
        # (If you want real JWTs later, we can wire that up.)
        token = f"demo-{external_id}"

        return jsonify(
            {
                "access_token": token,
                "user": {
                    "external_id": user.external_id,
                    "name": user.name,
                    "home_branch": user.home_branch,
                },
            }
        )
    finally:
        session.close()





# ---------------------------------------------------------
# Branch registration & listing
# ---------------------------------------------------------

@app.post("/api/branches")
def register_branch():
    data = request.get_json(force=True)
    code = data.get("code")
    name = data.get("name")
    base_url = data.get("base_url")

    if not code or not name or not base_url:
        abort(400, description="code, name, base_url required")

    session = SessionLocal()
    try:
        q = select(Branch).where(Branch.code == code)
        existing = session.execute(q).scalar_one_or_none()
        if existing:
            existing.name = name
            existing.base_url = base_url
            existing.is_active = True
            logger.info("Updated branch %s", code)
        else:
            b = Branch(
                code=code,
                name=name,
                base_url=base_url,
                is_active=True,
                created_at=datetime.utcnow(),
            )
            session.add(b)
            logger.info("Registered new branch %s", code)

        session.commit()
        return jsonify({"message": "ok"}), 200
    finally:
        session.close()


@app.get("/api/branches")
def list_branches():
    session = SessionLocal()
    try:
        branches = session.execute(select(Branch)).scalars().all()
        return jsonify(
            [
                {
                    "code": b.code,
                    "name": b.name,
                    "base_url": b.base_url,
                    "is_active": b.is_active,
                }
                for b in branches
            ]
        )
    finally:
        session.close()


# ---------------------------------------------------------
# Sync availability FROM branches
# ---------------------------------------------------------

@app.post("/api/global/sync/availability")
@require_api_key
def sync_availability():
    """
    Branches call this whenever availability changes.
    """
    data = request.get_json(force=True)
    isbn = data.get("isbn")
    branch_code = data.get("branch_code")
    total = data.get("total_copies")
    available = data.get("available_copies")

    if not isbn or not branch_code or total is None or available is None:
        abort(400, description="isbn, branch_code, total_copies, available_copies required")

    logger.info(
        "SYNC RECEIVED isbn=%s branch=%s total=%s avail=%s",
        isbn,
        branch_code,
        total,
        available,
    )

    session = SessionLocal()
    try:
        # Upsert BookGlobal (we keep minimal metadata here)
        q_bg = select(BookGlobal).where(BookGlobal.isbn == isbn)
        bg = session.execute(q_bg).scalar_one_or_none()
        if not bg:
            bg = BookGlobal(
                isbn=isbn,
                title=data.get("title") or isbn,
                author=data.get("author"),
                publisher=data.get("publisher"),
                year=data.get("year"),
                created_at=datetime.utcnow(),
            )
            session.add(bg)
        else:
            # If new metadata arrives, update it (useful when first sync
            # had only ISBN, later ones include title/author).
            if data.get("title"):
                bg.title = data["title"]
            if data.get("author"):
                bg.author = data["author"]
            if data.get("publisher"):
                bg.publisher = data["publisher"]
            if data.get("year") is not None:
                bg.year = data["year"]

        # Upsert BookAvailability per branch
        q_av = select(BookAvailability).where(
            (BookAvailability.isbn == isbn)
            & (BookAvailability.branch_code == branch_code)
        )
        av = session.execute(q_av).scalar_one_or_none()
        if av:
            av.total_copies = int(total)
            av.available_copies = int(available)
            av.last_sync_at = datetime.utcnow()
        else:
            av = BookAvailability(
                isbn=isbn,
                branch_code=branch_code,
                total_copies=int(total),
                available_copies=int(available),
                last_sync_at=datetime.utcnow(),
            )
            session.add(av)

        session.commit()
        return jsonify({"message": "synced"}), 200
    finally:
        session.close()


# ---------------------------------------------------------
# Global catalog search
# ---------------------------------------------------------

@app.get("/api/global/books")
def global_search():
    """
    Search across BookGlobal and join availability.
    - ?query=...  matches title/author/isbn (case-insensitive)
    - ?isbn=...   exact ISBN match
    - no params   returns all titles
    """
    query = request.args.get("query")
    isbn = request.args.get("isbn")

    session = SessionLocal()
    try:
        q = select(BookGlobal)
        if isbn:
            q = q.where(BookGlobal.isbn == isbn)
        elif query:
            like = f"%{query}%"
            q = q.where(
                (BookGlobal.title.ilike(like))
                | (BookGlobal.author.ilike(like))
                | (BookGlobal.isbn.ilike(like))
            )
        # else: no filter → return all books

        books = session.execute(q).scalars().all()
        results = []

        for bg in books:
            q_av = select(BookAvailability).where(BookAvailability.isbn == bg.isbn)
            av_list = session.execute(q_av).scalars().all()

            branches = [
                {
                    "branch_code": av.branch_code,
                    "total_copies": av.total_copies,
                    "available_copies": av.available_copies,
                }
                for av in av_list
            ]

            results.append(
                {
                    "isbn": bg.isbn,
                    "title": bg.title,
                    "author": bg.author,
                    "publisher": bg.publisher,
                    "year": bg.year,
                    "branches": branches,
                }
            )

        return jsonify(results)
    finally:
        session.close()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
