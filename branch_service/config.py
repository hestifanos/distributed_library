import os

class Config:
    # Example: "mysql+pymysql://user:password@localhost:3306/branch_a_db"
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///branch.db")
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    BRANCH_CODE = os.getenv("BRANCH_CODE", "BRANCH_A")
    CENTRAL_BASE_URL = os.getenv("CENTRAL_BASE_URL", "http://localhost:5000")

    # Shared API key with central
    SERVICE_API_KEY = os.getenv("SERVICE_API_KEY", "dev-service-key")
