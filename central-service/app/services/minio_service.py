from io import BytesIO

from minio import Minio

from app.core.config import settings


class MinioService:
    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.bucket = settings.MINIO_BUCKET

    def ensure_bucket(self):
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def upload_bytes(self, object_key: str, payload: bytes, content_type: str):
        data = BytesIO(payload)

        self.client.put_object(
            bucket_name=self.bucket,
            object_name=object_key,
            data=data,
            length=len(payload),
            content_type=content_type,
        )

    def get_object(self, object_key: str):
        return self.client.get_object(self.bucket, object_key)