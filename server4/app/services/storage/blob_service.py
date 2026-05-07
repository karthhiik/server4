"""Azure Blob Storage service for export file uploads with SAS-protected downloads."""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from azure.storage.blob import BlobSasPermissions, ContentSettings, generate_blob_sas
from azure.storage.blob.aio import BlobServiceClient, ContainerClient

from app.config import settings

import structlog

logger = structlog.get_logger()


def _parse_connection_string(conn_str: str) -> dict:
    """Extract account_name and account_key from Azure connection string."""
    parts = {}
    for segment in conn_str.split(";"):
        if "=" in segment:
            key, _, value = segment.partition("=")
            parts[key] = value
    return {
        "account_name": parts.get("AccountName", ""),
        "account_key": parts.get("AccountKey", ""),
    }


class BlobStorageService:
    """Azure Blob Storage wrapper with SAS-protected download URLs."""

    _instance: Optional["BlobStorageService"] = None

    def __init__(self):
        self._client: Optional[BlobServiceClient] = None
        self._container: Optional[ContainerClient] = None
        self._account_name: str = ""
        self._account_key: str = ""

    @classmethod
    def get_instance(cls) -> "BlobStorageService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def _get_container(self) -> ContainerClient:
        if self._container is None:
            conn_str = settings.BLOB_STORAGE_CONNECTION_STRING.strip().strip('"')
            if not conn_str:
                raise ConnectionError("Azure Blob Storage not configured")
            self._client = BlobServiceClient.from_connection_string(conn_str)
            self._container = self._client.get_container_client(
                settings.BLOB_CONTAINER_NAME
            )
            creds = _parse_connection_string(conn_str)
            self._account_name = creds["account_name"]
            self._account_key = creds["account_key"]
        return self._container

    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        folder: str = "exports",
    ) -> str:
        """Upload file to blob storage and return the blob name (not URL)."""
        container = await self._get_container()
        blob_name = f"{folder}/{uuid.uuid4().hex}_{filename}"

        blob_client = container.get_blob_client(blob_name)
        await blob_client.upload_blob(
            file_data,
            content_settings=ContentSettings(content_type=content_type),
            overwrite=True,
        )

        logger.info("blob_uploaded", blob_name=blob_name, size=len(file_data))
        return blob_name

    def generate_sas_download_url(self, blob_name: str, expiry_hours: int = 1) -> str:
        """Generate a SAS-protected download URL with configurable expiry."""
        if not self._account_name or not self._account_key:
            conn_str = settings.BLOB_STORAGE_CONNECTION_STRING.strip().strip('"')
            creds = _parse_connection_string(conn_str)
            self._account_name = creds["account_name"]
            self._account_key = creds["account_key"]

        sas_token = generate_blob_sas(
            account_name=self._account_name,
            container_name=settings.BLOB_CONTAINER_NAME,
            blob_name=blob_name,
            account_key=self._account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=expiry_hours),
        )
        return (
            f"https://{self._account_name}.blob.core.windows.net/"
            f"{settings.BLOB_CONTAINER_NAME}/{blob_name}?{sas_token}"
        )

    async def delete_file(self, blob_name: str) -> None:
        """Delete a blob by name."""
        container = await self._get_container()
        blob_client = container.get_blob_client(blob_name)
        await blob_client.delete_blob()

    async def close(self) -> None:
        if self._client:
            await self._client.close()
