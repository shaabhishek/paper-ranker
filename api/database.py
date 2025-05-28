"""Database connection and session management."""

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from api.config import settings
from api.models import Base

logger = logging.getLogger(__name__)

# Create database engine
engine = create_engine(
  settings.database_url,
  echo=settings.debug,  # Log SQL queries in debug mode
  pool_pre_ping=True,  # Verify connections before use
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
  """Create all database tables."""
  logger.info('Creating database tables...')
  Base.metadata.create_all(bind=engine)
  logger.info('Database tables created successfully')


def get_db() -> Session:
  """Get database session dependency for FastAPI."""
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()


async def init_db():
  """Initialize database on startup."""
  try:
    create_tables()
    logger.info('Database initialized successfully')
  except Exception as e:
    logger.error(f'Failed to initialize database: {e}')
    raise
