from functools import lru_cache
from typing import Optional

import boto3
from botocore.client import Config

from ..config import get_config


@lru_cache(maxsize=1)
def get_minio_client():
    """
    Returns a singleton MinIO (S3) client.

    Uses lru_cache to ensure the client is created only once.

    Returns:
        Boto3 S3 client configured for MinIO
    """
    config = get_config()
    # Remove trailing slash from endpoint URL to avoid signature issues
    endpoint = config.minio_endpoint.rstrip('/')
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=config.minio_access_key,
        aws_secret_access_key=config.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1"  # MinIO ignores region, but Boto3 requires it
    )


def wipe_bucket(bucket_name: str) -> None:
    """
    Deletes all objects in a bucket.

    Args:
        bucket_name: Name of the bucket to wipe
    """
    s3 = get_minio_client()
    try:
        # List all objects in the bucket
        response = s3.list_objects_v2(Bucket=bucket_name)

        if 'Contents' not in response:
            print(f"Bucket '{bucket_name}' ja esta vazio.")
            return

        # Delete each object
        objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]

        if objects_to_delete:
            s3.delete_objects(
                Bucket=bucket_name,
                Delete={'Objects': objects_to_delete}
            )
            print(f"Bucket '{bucket_name}' limpo: {len(objects_to_delete)} objetos removidos.")
    except Exception as e:
        print(f"Erro ao limpar bucket '{bucket_name}': {e}")


def garantir_bucket(bucket_name: str) -> None:
    """
    Ensures a bucket exists, creating it if necessary.

    Args:
        bucket_name: Name of the bucket to ensure exists
    """
    s3 = get_minio_client()
    buckets = s3.list_buckets()["Buckets"]
    if not any(b["Name"] == bucket_name for b in buckets):
        s3.create_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' criado com sucesso.")


def upload_to_minio(
    bucket_name: str,
    key: str,
    content: str,
    content_type: str = 'text/markdown'
) -> bool:
    """
    Uploads content to MinIO bucket.

    Args:
        bucket_name: Target bucket name
        key: Object key (file name in bucket)
        content: Content to upload
        content_type: MIME type of the content

    Returns:
        True if upload succeeded, False otherwise
    """
    try:
        s3 = get_minio_client()
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=content.encode('utf-8'),
            ContentType=content_type
        )
        return True
    except Exception as e:
        print(f"Erro ao salvar no MinIO: {e}")
        return False


def upload_file_to_minio(
    bucket_name: str,
    file_path: str,
    key: str,
    content_type: Optional[str] = None
) -> bool:
    """
    Uploads a local file to MinIO bucket.

    Args:
        bucket_name: Target bucket name
        file_path: Path to local file
        key: Object key (file name in bucket)
        content_type: Optional MIME type

    Returns:
        True if upload succeeded, False otherwise
    """
    try:
        s3 = get_minio_client()
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type

        s3.upload_file(
            file_path,
            bucket_name,
            key,
            ExtraArgs=extra_args if extra_args else None
        )
        return True
    except Exception as e:
        print(f"Erro ao subir arquivo para MinIO: {e}")
        return False
