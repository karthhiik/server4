import base64
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions, ContentSettings
from datetime import datetime, timedelta
from app.core.config import get_settings

settings = get_settings()

class AzureBlobManager:
    def __init__(self):
        self.connection_string = settings.BLOB_STORAGE_CONNECTION_STRING
        self.container_name = settings.BLOB_CONTAINER_NAME
        self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)

    def generate_upload_sas(self, blob_name: str, expiry_minutes: int = 60) -> str:
        """
        Generates a SAS token for a specific blob that allows writing (uploading).
        """
        sas_token = generate_blob_sas(
            account_name=self.blob_service_client.account_name,
            container_name=self.container_name,
            blob_name=blob_name,
            account_key=self.blob_service_client.credential.account_key,
            permission=BlobSasPermissions(write=True),
            expiry=datetime.utcnow() + timedelta(minutes=expiry_minutes)
        )
        
        # Construct the full SAS URL
        # Format: https://<account>.blob.core.windows.net/<container>/<blob>?<sas_token>
        blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)
        sas_url = f"{blob_client.url}?{sas_token}"
        
        return sas_url

    def generate_read_sas(self, blob_name: str, filename: str = None, expiry_minutes: int = 60) -> str:
        """
        Generates a SAS token for reading (downloading) a specific blob.
        """
        content_disposition = None
        if filename:
            content_disposition = f'attachment; filename="{filename}"'

        sas_token = generate_blob_sas(
            account_name=self.blob_service_client.account_name,
            container_name=self.container_name,
            blob_name=blob_name,
            account_key=self.blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(minutes=expiry_minutes),
            content_disposition=content_disposition
        )
        
        blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)
        sas_url = f"{blob_client.url}?{sas_token}"
        
        return sas_url

    async def commit_block_list(self, blob_name: str, block_ids: list[str], content_type: str):
        """
        Commits the list of blocks to finalize the blob.
        """
        # Note: This is a synchronous call in the Azure SDK, so we wrap it or run it directly.
        # For high-concurrency, run in executor. But here it's fine.
        container_client = self.blob_service_client.get_container_client(self.container_name)
        blob_client = container_client.get_blob_client(blob_name)
        
        # Convert Base64 Block IDs to BlockList objects if needed, 
        # but commit_block_list usually takes a list of BlobBlock or dicts.
        # Actually, it takes a list of StandardBlobTier or just the IDs?
        # SDK v12: commit_block_list(block_list: list[BlobBlock | str | dict])
        
        from azure.storage.blob import BlobBlock
        # Fix for Azure SDK double-encoding issue:
        # The frontend sends Base64-encoded IDs (e.g., "MDAwMDA=").
        # The Azure SDK re-encodes them if we pass them as-is.
        # So we must decode them back to raw strings (e.g., "00000") before passing to BlobBlock.
        decoded_blocks = []
        for bid in block_ids:
            try:
                # Add padding if needed (though usually frontend handles it)
                missing_padding = len(bid) % 4
                if missing_padding:
                    bid += '=' * (4 - missing_padding)
                decoded_id = base64.b64decode(bid).decode('utf-8')
                decoded_blocks.append(BlobBlock(block_id=decoded_id))
            except Exception as e:
                print(f"Error decoding block ID {bid}: {e}")
                # Fallback: try using original ID if decoding fails
                decoded_blocks.append(BlobBlock(block_id=bid))

        blob_client.commit_block_list(decoded_blocks, content_settings=ContentSettings(content_type=content_type))
        
        return blob_client.url

azure_manager = AzureBlobManager()
