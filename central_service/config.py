import os

class Config:
    # Example: "mysql+pymysql://user:password@localhost:3306/central_db"
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///central.db")
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Shared API key for service-to-service calls
    SERVICE_API_KEY = os.getenv("SERVICE_API_KEY", "dev-service-key")

    # JWT settings for user authentication
    JWT_SECRET = os.getenv("JWT_SECRET", "jwt-dev-secret")
    JWT_ALGORITHM = "HS256"
    JWT_EXP_MINUTES = int(os.getenv("JWT_EXP_MINUTES", "60"))
