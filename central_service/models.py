# central_service/models.py
from datetime import datetime

from sqlalchemy.orm import declarative_base
from sqlalchemy import (
    Column,
    Integer,          # <— use Integer for autoincrement PKs in SQLite
    String,
    DateTime,
    Boolean,
)

Base = declarative_base()


class Branch(Base):
    __tablename__ = "branch"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    base_url = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BookGlobal(Base):
    __tablename__ = "book_global"

    id = Column(Integer, primary_key=True, autoincrement=True)
    isbn = Column(String(20), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    author = Column(String(255))
    publisher = Column(String(255))
    year = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class BookAvailability(Base):
    __tablename__ = "book_availability"

    id = Column(Integer, primary_key=True, autoincrement=True)
    isbn = Column(String(20), nullable=False)
    branch_code = Column(String(50), nullable=False)
    total_copies = Column(Integer, nullable=False)
    available_copies = Column(Integer, nullable=False)
    last_sync_at = Column(DateTime, default=datetime.utcnow)


class UserCentral(Base):
    """
    Central record of a library patron. One record per external_id.
    Created the first time they log in (demo flow).
    """
    __tablename__ = "user_central"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    home_branch = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
