import os
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/friends_db"
)

logger.info("Connecting to database: %s", DATABASE_URL.split("@")[1] if "@" in DATABASE_URL else DATABASE_URL)

# Configure engine with SQLite-specific settings for testing
if "sqlite" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Use StaticPool for in-memory SQLite
    )
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependency injection for getting a database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
