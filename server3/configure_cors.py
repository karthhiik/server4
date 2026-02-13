from azure.storage.blob import BlobServiceClient, CorsRule
from app.core.config import get_settings

settings = get_settings()

def configure_cors():
    print("🔌 Connecting to Azure Storage...")
    blob_service_client = BlobServiceClient.from_connection_string(settings.BLOB_STORAGE_CONNECTION_STRING)

    # Define CORS rule
    cors_rule = CorsRule(
        allowed_origins=["*"],  # For development. In prod, use ["http://localhost:3000", "https://your-domain.com"]
        allowed_methods=["GET", "PUT", "POST", "OPTIONS", "HEAD", "DELETE"],
        allowed_headers=["*"],
        exposed_headers=["*"],
        max_age_in_seconds=3600
    )

    print("⚙️ Setting CORS rules...")
    # Set properties
    blob_service_client.set_service_properties(cors=[cors_rule])
    
    print("✅ CORS configured successfully for all origins (*)")

if __name__ == "__main__":
    configure_cors()
