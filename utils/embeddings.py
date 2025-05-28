"""Embedding utilities using OpenAI API."""

import asyncio
import logging
from typing import Any
from typing import Dict
from typing import List

import openai

from api.config import settings

logger = logging.getLogger(__name__)


class EmbeddingClient:
  """Client for generating embeddings using OpenAI API."""

  def __init__(self):
    """Initialize OpenAI client."""
    self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    self.model = settings.embedding_model
    self.dimensions = settings.embedding_dimensions
    self.max_retries = 3
    self.retry_delay = 1.0

  async def embed_text(self, text: str) -> List[float]:
    """Generate embedding for a single text."""
    logger.info(f'Generating embedding for text (length: {len(text)})')

    if not text.strip():
      logger.warning('Empty text provided for embedding')
      return [0.0] * self.dimensions

    for attempt in range(self.max_retries):
      try:
        response = await self.client.embeddings.create(
          model=self.model, input=text, dimensions=self.dimensions
        )

        embedding = response.data[0].embedding
        logger.debug(f'Generated embedding with {len(embedding)} dimensions')
        return embedding

      except openai.RateLimitError:
        wait_time = self.retry_delay * (2**attempt)
        logger.warning(
          f'Rate limit hit, waiting {wait_time}s before retry {attempt + 1}'
        )
        await asyncio.sleep(wait_time)

      except openai.APIError as e:
        logger.error(f'OpenAI API error on attempt {attempt + 1}: {e}')
        if attempt == self.max_retries - 1:
          raise
        await asyncio.sleep(self.retry_delay)

      except Exception as e:
        logger.error(f'Unexpected error generating embedding: {e}')
        if attempt == self.max_retries - 1:
          raise
        await asyncio.sleep(self.retry_delay)

    # If all retries failed, return zero vector
    logger.error('All embedding attempts failed, returning zero vector')
    return [0.0] * self.dimensions

  async def embed_batch(
    self, texts: List[str], batch_size: int = 100
  ) -> List[List[float]]:
    """Generate embeddings for a batch of texts."""
    logger.info(
      f'Generating embeddings for {len(texts)} texts in batches of {batch_size}'
    )

    if not texts:
      return []

    all_embeddings = []

    # Process in batches to respect API limits
    for i in range(0, len(texts), batch_size):
      batch = texts[i : i + batch_size]
      logger.info(
        f'Processing batch {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1}'
      )

      # Filter out empty texts
      non_empty_batch = [text for text in batch if text.strip()]

      if not non_empty_batch:
        # Add zero vectors for empty batch
        all_embeddings.extend([[0.0] * self.dimensions] * len(batch))
        continue

      for attempt in range(self.max_retries):
        try:
          response = await self.client.embeddings.create(
            model=self.model, input=non_empty_batch, dimensions=self.dimensions
          )

          batch_embeddings = [item.embedding for item in response.data]

          # Handle case where some texts in original batch were empty
          embedding_idx = 0
          for text in batch:
            if text.strip():
              all_embeddings.append(batch_embeddings[embedding_idx])
              embedding_idx += 1
            else:
              all_embeddings.append([0.0] * self.dimensions)

          break  # Success, break retry loop

        except openai.RateLimitError:
          wait_time = self.retry_delay * (2**attempt)
          logger.warning(
            f'Rate limit hit, waiting {wait_time}s before retry {attempt + 1}'
          )
          await asyncio.sleep(wait_time)

        except openai.APIError as e:
          logger.error(f'OpenAI API error on attempt {attempt + 1}: {e}')
          if attempt == self.max_retries - 1:
            # Add zero vectors for failed batch
            all_embeddings.extend([[0.0] * self.dimensions] * len(batch))
          else:
            await asyncio.sleep(self.retry_delay)

        except Exception as e:
          logger.error(f'Unexpected error in batch embedding: {e}')
          if attempt == self.max_retries - 1:
            # Add zero vectors for failed batch
            all_embeddings.extend([[0.0] * self.dimensions] * len(batch))
          else:
            await asyncio.sleep(self.retry_delay)

      # Small delay between batches to be respectful to API
      await asyncio.sleep(0.1)

    logger.info(f'Generated {len(all_embeddings)} embeddings')
    return all_embeddings

  async def embed_chunks(
    self, chunks: List[str], paper_id: str
  ) -> List[Dict[str, Any]]:
    """Generate embeddings for text chunks with metadata."""
    logger.info(
      f'Generating embeddings for {len(chunks)} chunks of paper {paper_id}'
    )

    if not chunks:
      return []

    # Generate embeddings for all chunks
    embeddings = await self.embed_batch(chunks)

    # Create vector objects with metadata
    vectors = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
      vector = {
        'id': f'{paper_id}_chunk_{i}',
        'values': embedding,
        'metadata': {
          'paper_id': paper_id,
          'chunk_index': i,
          'chunk_text': chunk[:500],  # Store first 500 chars for reference
          'chunk_length': len(chunk),
        },
      }
      vectors.append(vector)

    logger.info(f'Created {len(vectors)} vector objects for paper {paper_id}')
    return vectors

  async def generate_summary(self, text: str, max_tokens: int = 200) -> str:
    """Generate a summary of the paper using OpenAI Chat API."""
    logger.info(f'Generating summary for text (length: {len(text)})')

    # Truncate text if too long (keep first part which usually has abstract/intro)
    max_input_length = 8000  # Leave room for prompt
    if len(text) > max_input_length:
      text = text[:max_input_length] + '...'

    prompt = f"""
    Please provide a concise summary of the following academic paper in approximately {max_tokens} words. 
    Focus on the key contributions, methods, and findings:

    {text}

    Summary:
    """

    for attempt in range(self.max_retries):
      try:
        response = await self.client.chat.completions.create(
          model='gpt-3.5-turbo',
          messages=[
            {
              'role': 'system',
              'content': 'You are an expert at summarizing academic papers.',
            },
            {'role': 'user', 'content': prompt},
          ],
          max_tokens=max_tokens,
          temperature=0.3,
        )

        summary = response.choices[0].message.content.strip()
        logger.info(f'Generated summary of length: {len(summary)}')
        return summary

      except openai.RateLimitError:
        wait_time = self.retry_delay * (2**attempt)
        logger.warning(
          f'Rate limit hit, waiting {wait_time}s before retry {attempt + 1}'
        )
        await asyncio.sleep(wait_time)

      except openai.APIError as e:
        logger.error(
          f'OpenAI API error generating summary on attempt {attempt + 1}: {e}'
        )
        if attempt == self.max_retries - 1:
          return 'Summary generation failed due to API error.'
        await asyncio.sleep(self.retry_delay)

      except Exception as e:
        logger.error(f'Unexpected error generating summary: {e}')
        if attempt == self.max_retries - 1:
          return 'Summary generation failed due to unexpected error.'
        await asyncio.sleep(self.retry_delay)

    return 'Summary generation failed after multiple attempts.'
