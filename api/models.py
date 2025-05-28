"""Database models for the application."""

from datetime import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import ARRAY
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Paper(Base):
  """Paper model for storing paper metadata."""

  __tablename__ = 'papers'

  paper_id = Column(String, primary_key=True)
  title = Column(Text, nullable=False)
  authors = Column(ARRAY(String), nullable=True)
  year = Column(Integer, nullable=True)
  venue = Column(String, nullable=True)
  keywords = Column(ARRAY(String), nullable=True)
  s3_key = Column(String, nullable=True)
  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())

  # Relationship to summaries
  summary = relationship('Summary', back_populates='paper', uselist=False)


class Summary(Base):
  """Summary model for storing cached paper summaries."""

  __tablename__ = 'summaries'

  paper_id = Column(String, ForeignKey('papers.paper_id'), primary_key=True)
  summary = Column(Text, nullable=False)
  generated_at = Column(DateTime(timezone=True), server_default=func.now())

  # Relationship to paper
  paper = relationship('Paper', back_populates='summary')


# Pydantic models for API serialization
class PaperBase(BaseModel):
  """Base paper model for API."""

  title: str
  authors: Optional[List[str]] = None
  year: Optional[int] = None
  venue: Optional[str] = None
  keywords: Optional[List[str]] = None
  s3_key: Optional[str] = None


class PaperCreate(PaperBase):
  """Paper creation model."""

  paper_id: str


class PaperResponse(PaperBase):
  """Paper response model."""

  paper_id: str
  created_at: datetime
  updated_at: Optional[datetime] = None

  class Config:
    from_attributes = True


class PaperRanked(PaperResponse):
  """Ranked paper response model with similarity score."""

  similarity_score: float


class SummaryBase(BaseModel):
  """Base summary model for API."""

  summary: str


class SummaryCreate(SummaryBase):
  """Summary creation model."""

  paper_id: str


class SummaryResponse(SummaryBase):
  """Summary response model."""

  paper_id: str
  generated_at: datetime

  class Config:
    from_attributes = True
