"""AWS S3 client utilities for file operations."""

import logging
import os
import tempfile
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from botocore.exceptions import NoCredentialsError

from api.config import settings

logger = logging.getLogger(__name__)


class S3Client:
  """Client for interacting with AWS S3."""

  def __init__(self):
    """Initialize S3 client."""
    try:
      self.s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
      )
      self.bucket = settings.s3_bucket

      # Test connection
      self._test_connection()

    except NoCredentialsError:
      logger.error('AWS credentials not found')
      raise
    except Exception as e:
      logger.error(f'Failed to initialize S3 client: {e}')
      raise

  def _test_connection(self):
    """Test S3 connection and bucket access."""
    try:
      self.s3_client.head_bucket(Bucket=self.bucket)
      logger.info(f'Successfully connected to S3 bucket: {self.bucket}')
    except ClientError as e:
      error_code = e.response['Error']['Code']
      if error_code == '404':
        logger.error(f'Bucket {self.bucket} does not exist')
      elif error_code == '403':
        logger.error(f'Access denied to bucket {self.bucket}')
      else:
        logger.error(f'Error accessing bucket {self.bucket}: {e}')
      raise

  async def list_objects(self, prefix: str) -> List[str]:
    """List objects in S3 bucket with given prefix."""
    logger.info(f'Listing objects with prefix: {prefix}')

    try:
      response = self.s3_client.list_objects_v2(
        Bucket=self.bucket, Prefix=prefix
      )

      objects = []
      if 'Contents' in response:
        for obj in response['Contents']:
          # Only include PDF files
          if obj['Key'].lower().endswith('.pdf'):
            objects.append(obj['Key'])

      logger.info(f'Found {len(objects)} PDF objects with prefix {prefix}')
      return objects

    except ClientError as e:
      logger.error(f'Failed to list objects with prefix {prefix}: {e}')
      return []

  async def download_file(self, s3_key: str, local_path: str) -> bool:
    """Download file from S3 to local path."""
    logger.info(f'Downloading {s3_key} to {local_path}')

    try:
      # Create directory if it doesn't exist
      os.makedirs(os.path.dirname(local_path), exist_ok=True)

      self.s3_client.download_file(self.bucket, s3_key, local_path)

      # Verify file was downloaded
      if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        logger.info(f'Successfully downloaded {s3_key}')
        return True
      else:
        logger.error(f'Downloaded file {local_path} is empty or missing')
        return False

    except ClientError as e:
      logger.error(f'Failed to download {s3_key}: {e}')
      return False
    except Exception as e:
      logger.error(f'Unexpected error downloading {s3_key}: {e}')
      return False

  async def upload_file(self, local_path: str, s3_key: str) -> bool:
    """Upload file from local path to S3."""
    logger.info(f'Uploading {local_path} to {s3_key}')

    try:
      # Check if local file exists
      if not os.path.exists(local_path):
        logger.error(f'Local file {local_path} does not exist')
        return False

      # Upload file
      self.s3_client.upload_file(local_path, self.bucket, s3_key)

      # Verify upload by checking if object exists
      try:
        self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
        logger.info(f'Successfully uploaded {s3_key}')
        return True
      except ClientError:
        logger.error(f'Upload verification failed for {s3_key}')
        return False

    except ClientError as e:
      logger.error(f'Failed to upload {local_path}: {e}')
      return False
    except Exception as e:
      logger.error(f'Unexpected error uploading {local_path}: {e}')
      return False

  async def generate_presigned_url(
    self, s3_key: str, expiration: int = 3600
  ) -> str:
    """Generate presigned URL for file upload."""
    logger.info(f'Generating presigned URL for {s3_key}')

    try:
      url = self.s3_client.generate_presigned_url(
        'put_object',
        Params={'Bucket': self.bucket, 'Key': s3_key},
        ExpiresIn=expiration,
      )

      logger.info(
        f'Generated presigned URL for {s3_key} (expires in {expiration}s)'
      )
      return url

    except ClientError as e:
      logger.error(f'Failed to generate presigned URL for {s3_key}: {e}')
      return ''
    except Exception as e:
      logger.error(f'Unexpected error generating presigned URL: {e}')
      return ''

  async def delete_file(self, s3_key: str) -> bool:
    """Delete file from S3."""
    logger.info(f'Deleting {s3_key}')

    try:
      self.s3_client.delete_object(Bucket=self.bucket, Key=s3_key)

      # Verify deletion
      try:
        self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
        logger.error(f'File {s3_key} still exists after deletion attempt')
        return False
      except ClientError as e:
        if e.response['Error']['Code'] == '404':
          logger.info(f'Successfully deleted {s3_key}')
          return True
        else:
          logger.error(f'Error verifying deletion of {s3_key}: {e}')
          return False

    except ClientError as e:
      logger.error(f'Failed to delete {s3_key}: {e}')
      return False
    except Exception as e:
      logger.error(f'Unexpected error deleting {s3_key}: {e}')
      return False

  async def download_to_temp(self, s3_key: str) -> Optional[str]:
    """Download file to temporary location and return path."""
    logger.info(f'Downloading {s3_key} to temporary file')

    try:
      # Create temporary file
      temp_file = tempfile.NamedTemporaryFile(
        delete=False, suffix='.pdf', prefix='paper_'
      )
      temp_path = temp_file.name
      temp_file.close()

      # Download to temp file
      success = await self.download_file(s3_key, temp_path)

      if success:
        logger.info(f'Downloaded {s3_key} to {temp_path}')
        return temp_path
      else:
        # Clean up failed download
        if os.path.exists(temp_path):
          os.unlink(temp_path)
        return None

    except Exception as e:
      logger.error(f'Failed to download {s3_key} to temp file: {e}')
      return None

  def cleanup_temp_file(self, temp_path: str):
    """Clean up temporary file."""
    try:
      if os.path.exists(temp_path):
        os.unlink(temp_path)
        logger.debug(f'Cleaned up temporary file: {temp_path}')
    except Exception as e:
      logger.warning(f'Failed to clean up temp file {temp_path}: {e}')

  async def get_file_info(self, s3_key: str) -> Optional[Dict[str, Any]]:
    """Get file metadata from S3."""
    logger.info(f'Getting file info for {s3_key}')

    try:
      response = self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)

      file_info = {
        'key': s3_key,
        'size': response['ContentLength'],
        'last_modified': response['LastModified'],
        'etag': response['ETag'].strip('"'),
        'content_type': response.get('ContentType', 'application/pdf'),
      }

      logger.info(f'Retrieved file info for {s3_key}')
      return file_info

    except ClientError as e:
      if e.response['Error']['Code'] == '404':
        logger.warning(f'File {s3_key} not found')
      else:
        logger.error(f'Failed to get file info for {s3_key}: {e}')
      return None
    except Exception as e:
      logger.error(f'Unexpected error getting file info for {s3_key}: {e}')
      return None

  async def list_seed_papers(self) -> List[str]:
    """List all seed papers in the seeds/ folder."""
    return await self.list_objects('seeds/')

  async def list_corpus_papers(self) -> List[str]:
    """List all corpus papers in the corpus/ folder."""
    return await self.list_objects('corpus/')

  def get_bucket_name(self) -> str:
    """Get the configured bucket name."""
    return self.bucket
