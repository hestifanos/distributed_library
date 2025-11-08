import os
import json
from datetime import datetime, timedelta

import requests
from flask import Flask, jsonify, request, abort
from flask_cors import CORS
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from .config import Config
from .models import Base, Book, User, Loan, PendingSyncEvent

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# SQLAlchemy setup
engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"], future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Create tables
Base.metadata.create_all(engine)


# ----------------- helpers: API key, sync -----------------

def require_api_key(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        sent_key = request.headers.get("X-API-Key")
        expected = app.config.get("SERVICE_API_KEY")
        if not expected or sent_key != expected:
            abort(401, description="Invalid or missing service API key")
        return func(*args, **kwargs)

    return wrapper


def send_availability_event(book: Book, session):
    """
    Try to send availability update (with metadata) to central.
    If it fails, store in PendingSyncEvent for retry.
    """
    payload = {
        "isbn": book.isbn,
        "title": book.title,
        "author": book.author,
        "publisher": book.publisher,
        "year": book.year,
        "branch_code": app.config["BRANCH_CODE"],
        "total_copies": book.total_copies,
        "available_copies": book.available_copies,
        "timestamp": datetime.utcnow().isoformat(),
    }
    url = f'{app.config["CENTRAL_BASE_URL"].rstrip("/")}/api/global/sync/availability'

    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"X-API-Key": app.config["SERVICE_API_KEY"]},
            timeout=3,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Central returned {resp.status_code}")
    except Exception:
        # store for later retry
        evt = PendingSyncEvent(
            isbn=book.isbn,
            total_copies=book.total_copies,
            available_copies=book.available_copies,
            payload=json.dumps(payload),
        )
        session.add(evt)


def retry_pending_events():
    """
    Retry sending all pending sync events.
    Can be called manually or scheduled.
    """
    session = SessionLocal()
    try:
        events = session.execute(select(PendingSyncEvent)).scalars().all()
        for evt in events:
            try:
                payload = json.loads(evt.payload)
                url = f'{app.config["CENTRAL_BASE_URL"].rstrip("/")}/api/global/sync/availability'
                resp = requests.post(
                    url,
                    json=payload,
                    headers={"X-API-Key": app.config["SERVICE_API_KEY"]},
                    timeout=3,
                )
                if resp.status_code == 200:
                    session.delete(evt)
            except Exception:
                # leave for next retry
                pass
        session.commit()
    finally:
        session.close()


# ----------------- health -----------------

@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "branch": app.config["BRANCH_CODE"]})


# ----------------- user endpoints -----------------

@app.post("/api/users")
def create_user():
    data = request.get_json(force=True)
    external_id = data["external_id"]
    name = data["name"]
    email = data["email"]
    home_branch = data.get("home_branch")

    session = SessionLocal()
    try:
        q = select(User).where(User.external_id == external_id)
        existing = session.execute(q).scalar_one_or_none()
        if existing:
            return jsonify({"message": "User already exists"}), 200

        user = User(
            external_id=external_id,
            name=name,
            email=email,
            home_branch=home_branch,
        )
        session.add(user)
        session.commit()
        return jsonify({"id": user.id}), 201
    finally:
        session.close()


@app.get("/api/users/<external_id>")
def get_user(external_id):
    session = SessionLocal()
    try:
        q = select(User).where(User.external_id == external_id)
        user = session.execute(q).scalar_one_or_none()
        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify(
            {
                "external_id": user.external_id,
                "name": user.name,
                "email": user.email,
                "home_branch": user.home_branch,
            }
        )
    finally:
        session.close()


# ----------------- book endpoints -----------------

@app.post("/api/books")
@require_api_key
def create_or_update_book():
    """
    Librarian endpoint – upsert book by ISBN.
    """
    data = request.get_json(force=True)
    isbn = data["isbn"]
    title = data["title"]
    author = data.get("author")
    publisher = data.get("publisher")
    year = data.get("year")
    total_copies = data.get("total_copies", 1)

    session = SessionLocal()
    try:
        q = select(Book).where(Book.isbn == isbn).with_for_update()
        book = session.execute(q).scalar_one_or_none()

        if book:
            diff = total_copies - book.total_copies
            book.title = title
            book.author = author
            book.publisher = publisher
            book.year = year
            if diff != 0:
                book.total_copies = total_copies
                book.available_copies = max(0, book.available_copies + diff)
        else:
            book = Book(
                isbn=isbn,
                title=title,
                author=author,
                publisher=publisher,
                year=year,
                total_copies=total_copies,
                available_copies=total_copies,
            )
            session.add(book)

        session.commit()

        # Sync availability to central (with metadata)
        send_availability_event(book, session)
        session.commit()

        return jsonify({"isbn": book.isbn}), 201
    finally:
        session.close()


@app.get("/api/books")
def search_books():
    """
    Local search by title/author substring.
    """
    title = request.args.get("title")
    author = request.args.get("author")

    session = SessionLocal()
    try:
        q = select(Book)
        if title:
            q = q.where(Book.title.ilike(f"%{title}%"))
        if author:
            q = q.where(Book.author.ilike(f"%{author}%"))

        books = session.execute(q).scalars().all()
        return jsonify(
            [
                {
                    "isbn": b.isbn,
                    "title": b.title,
                    "author": b.author,
                    "total_copies": b.total_copies,
                    "available_copies": b.available_copies,
                }
                for b in books
            ]
        )
    finally:
        session.close()


@app.get("/api/books/<isbn>")
def get_book(isbn):
    session = SessionLocal()
    try:
        q = select(Book).where(Book.isbn == isbn)
        book = session.execute(q).scalar_one_or_none()
        if not book:
            return jsonify({"error": "Book not found"}), 404

        return jsonify(
            {
                "isbn": book.isbn,
                "title": book.title,
                "author": book.author,
                "publisher": book.publisher,
                "year": book.year,
                "total_copies": book.total_copies,
                "available_copies": book.available_copies,
            }
        )
    finally:
        session.close()


# ----------------- loan endpoints -----------------

@app.post("/api/loans")
@require_api_key
def borrow_book():
    data = request.get_json(force=True)
    isbn = data["isbn"]
    user_external_id = data["user_external_id"]
    days = int(data.get("days", 14))

    session = SessionLocal()
    try:
        user = session.execute(
            select(User).where(User.external_id == user_external_id).with_for_update()
        ).scalar_one_or_none()
        if not user:
            return jsonify({"error": "User not found in this branch"}), 404

        book = session.execute(
            select(Book).where(Book.isbn == isbn).with_for_update()
        ).scalar_one_or_none()
        if not book:
            return jsonify({"error": "Book not found in this branch"}), 404

        if book.available_copies <= 0:
            return jsonify({"error": "No copies available"}), 409

        book.available_copies -= 1
        loan = Loan(
            user_id=user.id,
            book_id=book.id,
            borrowed_at=datetime.utcnow(),
            due_at=datetime.utcnow() + timedelta(days=days),
            status="BORROWED",
        )
        session.add(loan)
        session.commit()

        # Sync availability
        send_availability_event(book, session)
        session.commit()

        return jsonify(
            {
                "loan_id": loan.id,
                "branch": app.config["BRANCH_CODE"],
                "due_at": loan.due_at.isoformat(),
            }
        ), 201
    finally:
        session.close()


@app.post("/api/loans/<int:loan_id>/return")
@require_api_key
def return_book(loan_id):
    session = SessionLocal()
    try:
        loan = session.execute(
            select(Loan).where(Loan.id == loan_id).with_for_update()
        ).scalar_one_or_none()
        if not loan:
            return jsonify({"error": "Loan not found"}), 404

        if loan.status == "RETURNED":
            return jsonify({"message": "Already returned"}), 200

        loan.status = "RETURNED"
        loan.returned_at = datetime.utcnow()

        # update book availability
        book = session.execute(
            select(Book).where(Book.id == loan.book_id).with_for_update()
        ).scalar_one()
        book.available_copies += 1

        session.commit()

        # Sync availability
        send_availability_event(book, session)
        session.commit()

        return jsonify({"message": "Returned"}), 200
    finally:
        session.close()


@app.get("/api/loans")
@require_api_key
def list_loans():
    """
    List all loans for a user_external_id for this branch.
    """
    user_external_id = request.args.get("user_external_id")
    if not user_external_id:
        return jsonify([])

    session = SessionLocal()
    try:
        user = session.execute(
            select(User).where(User.external_id == user_external_id)
        ).scalar_one_or_none()
        if not user:
            return jsonify([])

        loans = session.execute(select(Loan).where(Loan.user_id == user.id)).scalars().all()
        result = []
        for loan in loans:
            result.append(
                {
                    "loan_id": loan.id,
                    "isbn": loan.book.isbn,
                    "title": loan.book.title,
                    "status": loan.status,
                    "borrowed_at": loan.borrowed_at.isoformat(),
                    "due_at": loan.due_at.isoformat(),
                    "returned_at": loan.returned_at.isoformat()
                    if loan.returned_at
                    else None,
                    "branch": app.config["BRANCH_CODE"],
                }
            )
        return jsonify(result)
    finally:
        session.close()


# ----------------- sync endpoints -----------------

@app.get("/api/sync/availability")
@require_api_key
def availability_snapshot():
    """
    Central can call this for reconciliation.
    """
    session = SessionLocal()
    try:
        books = session.execute(select(Book)).scalars().all()
        data = []
        for b in books:
            data.append(
                {
                    "isbn": b.isbn,
                    "branch_code": app.config["BRANCH_CODE"],
                    "total_copies": b.total_copies,
                    "available_copies": b.available_copies,
                }
            )
        return jsonify(data)
    finally:
        session.close()


@app.post("/api/sync/retry")
@require_api_key
def retry_sync():
    retry_pending_events()
    return jsonify({"message": "Retry triggered"}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=True)
