"""Pinecone vector database client utilities."""

import asyncio
import logging
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pinecone import Pinecone
from pinecone import ServerlessSpec

from api.config import settings

logger = logging.getLogger(__name__)


class PineconeClient:
  """Client for interacting with Pinecone vector database."""

  def __init__(self):
    """Initialize Pinecone client."""
    self.pc = Pinecone(api_key=settings.pinecone_api_key)
    self.index_name = settings.pinecone_index_name
    self.index = None
    self.dimensions = settings.embedding_dimensions

  def connect(self):
    """Connect to Pinecone index."""
    logger.info(f'Connecting to Pinecone index: {self.index_name}')

    try:
      # Check if index exists
      existing_indexes = self.pc.list_indexes()
      index_names = [idx.name for idx in existing_indexes]

      if self.index_name not in index_names:
        logger.info(f'Index {self.index_name} does not exist, creating it...')
        self._create_index()

      # Connect to the index
      self.index = self.pc.Index(self.index_name)

      # Get index stats
      stats = self.index.describe_index_stats()
      logger.info(
        f'Connected to index {self.index_name}. Total vectors: {stats.total_vector_count}'
      )

    except Exception as e:
      logger.error(f'Failed to connect to Pinecone: {e}')
      raise

  def _create_index(self):
    """Create a new Pinecone index."""
    logger.info(f'Creating Pinecone index: {self.index_name}')

    try:
      self.pc.create_index(
        name=self.index_name,
        dimension=self.dimensions,
        metric='cosine',
        spec=ServerlessSpec(cloud='aws', region='us-east-1'),
      )

      # Wait for index to be ready
      import time

      while not self.pc.describe_index(self.index_name).status['ready']:
        logger.info('Waiting for index to be ready...')
        time.sleep(1)

      logger.info(f'Index {self.index_name} created successfully')

    except Exception as e:
      logger.error(f'Failed to create index: {e}')
      raise

  async def upsert_vectors(
    self, vectors: List[Dict[str, Any]], batch_size: int = 100
  ) -> bool:
    """Upsert vectors to Pinecone index."""
    logger.info(f'Upserting {len(vectors)} vectors to Pinecone')

    if not self.index:
      self.connect()

    if not vectors:
      logger.warning('No vectors to upsert')
      return True

    try:
      # Process in batches
      for i in range(0, len(vectors), batch_size):
        batch = vectors[i : i + batch_size]
        logger.info(
          f'Upserting batch {i // batch_size + 1}/{(len(vectors) - 1) // batch_size + 1}'
        )

        # Convert to Pinecone format
        pinecone_vectors = []
        for vector in batch:
          pinecone_vector = {
            'id': vector['id'],
            'values': vector['values'],
            'metadata': vector['metadata'],
          }
          pinecone_vectors.append(pinecone_vector)

        # Upsert batch
        self.index.upsert(vectors=pinecone_vectors)

        # Small delay between batches
        await asyncio.sleep(0.1)

      logger.info(f'Successfully upserted {len(vectors)} vectors')
      return True

    except Exception as e:
      logger.error(f'Failed to upsert vectors: {e}')
      return False

  async def query_similar(
    self,
    vector: List[float],
    top_k: int = 10,
    filter_dict: Optional[Dict] = None,
  ) -> List[Dict[str, Any]]:
    """Query for similar vectors."""
    logger.info(f'Querying for {top_k} similar vectors')

    if not self.index:
      self.connect()

    try:
      response = self.index.query(
        vector=vector, top_k=top_k, include_metadata=True, filter=filter_dict
      )

      results = []
      for match in response.matches:
        result = {
          'id': match.id,
          'score': match.score,
          'metadata': match.metadata,
        }
        results.append(result)

      logger.info(f'Found {len(results)} similar vectors')
      return results

    except Exception as e:
      logger.error(f'Failed to query similar vectors: {e}')
      return []

  async def fetch_vectors(self, paper_ids: List[str]) -> Dict[str, List[float]]:
    """Fetch vectors for specific paper IDs."""
    logger.info(f'Fetching vectors for {len(paper_ids)} papers')

    if not self.index:
      self.connect()

    if not paper_ids:
      return {}

    try:
      # Get all vector IDs for these papers
      all_vector_ids = []
      for paper_id in paper_ids:
        # Query to find all chunks for this paper
        query_response = self.index.query(
          vector=[0.0] * self.dimensions,  # Dummy vector
          top_k=10000,  # Large number to get all chunks
          include_metadata=True,
          filter={'paper_id': paper_id},
        )

        for match in query_response.matches:
          all_vector_ids.append(match.id)

      if not all_vector_ids:
        logger.warning('No vectors found for the specified paper IDs')
        return {}

      # Fetch vectors in batches
      batch_size = 1000
      all_vectors = {}

      for i in range(0, len(all_vector_ids), batch_size):
        batch_ids = all_vector_ids[i : i + batch_size]

        fetch_response = self.index.fetch(ids=batch_ids)

        for vector_id, vector_data in fetch_response.vectors.items():
          paper_id = vector_data.metadata.get('paper_id')
          if paper_id:
            if paper_id not in all_vectors:
              all_vectors[paper_id] = []
            all_vectors[paper_id].append(vector_data.values)

      logger.info(f'Fetched vectors for {len(all_vectors)} papers')
      return all_vectors

    except Exception as e:
      logger.error(f'Failed to fetch vectors: {e}')
      return {}

  async def get_paper_vectors(self, paper_id: str) -> List[List[float]]:
    """Get all vectors for a specific paper."""
    logger.info(f'Getting vectors for paper: {paper_id}')

    if not self.index:
      self.connect()

    try:
      # Query for all chunks of this paper
      response = self.index.query(
        vector=[0.0] * self.dimensions,  # Dummy vector
        top_k=10000,  # Large number to get all chunks
        include_metadata=True,
        filter={'paper_id': paper_id},
      )

      # Extract vector IDs and sort by chunk index
      vector_data = []
      for match in response.matches:
        chunk_index = match.metadata.get('chunk_index', 0)
        vector_data.append((chunk_index, match.id))

      # Sort by chunk index to maintain order
      vector_data.sort(key=lambda x: x[0])
      vector_ids = [vid for _, vid in vector_data]

      if not vector_ids:
        logger.warning(f'No vectors found for paper: {paper_id}')
        return []

      # Fetch the actual vectors
      fetch_response = self.index.fetch(ids=vector_ids)

      vectors = []
      for vector_id in vector_ids:
        if vector_id in fetch_response.vectors:
          vectors.append(fetch_response.vectors[vector_id].values)

      logger.info(f'Retrieved {len(vectors)} vectors for paper {paper_id}')
      return vectors

    except Exception as e:
      logger.error(f'Failed to get vectors for paper {paper_id}: {e}')
      return []

  async def delete_vectors(self, paper_ids: List[str]) -> bool:
    """Delete vectors for specific paper IDs."""
    logger.info(f'Deleting vectors for {len(paper_ids)} papers')

    if not self.index:
      self.connect()

    if not paper_ids:
      return True

    try:
      # Get all vector IDs for these papers
      all_vector_ids = []
      for paper_id in paper_ids:
        # Query to find all chunks for this paper
        query_response = self.index.query(
          vector=[0.0] * self.dimensions,  # Dummy vector
          top_k=10000,  # Large number to get all chunks
          include_metadata=True,
          filter={'paper_id': paper_id},
        )

        for match in query_response.matches:
          all_vector_ids.append(match.id)

      if not all_vector_ids:
        logger.warning('No vectors found to delete')
        return True

      # Delete in batches
      batch_size = 1000
      for i in range(0, len(all_vector_ids), batch_size):
        batch_ids = all_vector_ids[i : i + batch_size]
        self.index.delete(ids=batch_ids)
        await asyncio.sleep(0.1)  # Small delay between batches

      logger.info(f'Successfully deleted {len(all_vector_ids)} vectors')
      return True

    except Exception as e:
      logger.error(f'Failed to delete vectors: {e}')
      return False

  def get_index_stats(self) -> Dict[str, Any]:
    """Get index statistics."""
    if not self.index:
      self.connect()

    try:
      stats = self.index.describe_index_stats()
      return {
        'total_vector_count': stats.total_vector_count,
        'dimension': stats.dimension,
        'index_fullness': stats.index_fullness,
      }
    except Exception as e:
      logger.error(f'Failed to get index stats: {e}')
      return {}
