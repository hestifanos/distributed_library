from datetime import datetime

from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum,
    ForeignKey,
    Text,
)

Base = declarative_base()


class Book(Base):
    __tablename__ = "book"

    # PK as Integer autoincrement so SQLite happily generates IDs
    id = Column(Integer, primary_key=True, autoincrement=True)
    isbn = Column(String(20), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    author = Column(String(255))
    publisher = Column(String(255))
    year = Column(Integer)
    total_copies = Column(Integer, nullable=False, default=1)
    available_copies = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    home_branch = Column(String(50))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Loan(Base):
    __tablename__ = "loan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("book.id"), nullable=False)
    borrowed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    due_at = Column(DateTime, nullable=False)
    returned_at = Column(DateTime)
    status = Column(
        Enum("BORROWED", "RETURNED", "OVERDUE", name="loan_status"),
        nullable=False,
        default="BORROWED",
    )

    user = relationship("User")
    book = relationship("Book")


class PendingSyncEvent(Base):
    """
    Outgoing availability updates that couldn't reach central.
    """
    __tablename__ = "pending_sync_event"

    id = Column(Integer, primary_key=True, autoincrement=True)
    isbn = Column(String(20), nullable=False)
    total_copies = Column(Integer, nullable=False)
    available_copies = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    payload = Column(Text)  # JSON blob
