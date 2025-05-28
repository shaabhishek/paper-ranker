"""Configuration management for the application."""

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
  """Application settings loaded from environment variables."""

  # Database
  database_url: str = os.getenv(
    'DATABASE_URL', 'postgresql://localhost/paper_ranker'
  )

  # OpenAI
  openai_api_key: str = os.getenv('OPENAI_API_KEY', '')

  # Pinecone
  pinecone_api_key: str = os.getenv('PINECONE_API_KEY', '')
  pinecone_environment: str = os.getenv('PINECONE_ENVIRONMENT', 'us-west1-gcp')
  pinecone_index_name: str = os.getenv('PINECONE_INDEX_NAME', 'papers')

  # AWS S3
  aws_access_key_id: str = os.getenv('AWS_ACCESS_KEY_ID', '')
  aws_secret_access_key: str = os.getenv('AWS_SECRET_ACCESS_KEY', '')
  aws_region: str = os.getenv('AWS_REGION', 'us-east-1')
  s3_bucket: str = os.getenv('S3_BUCKET', 'my-app-papers')

  # Application
  debug: bool = os.getenv('DEBUG', 'False').lower() == 'true'
  log_level: str = os.getenv('LOG_LEVEL', 'INFO')

  # Embedding settings
  embedding_model: str = 'text-embedding-3-large'
  embedding_dimensions: int = 3072
  chunk_size: int = 10000

  class Config:
    env_file = '.env'
    env_file_encoding = 'utf-8'


# Global settings instance
settings = Settings()
