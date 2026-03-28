import asyncio
import sys
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER3_ROOT = REPO_ROOT / "server3"

if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))
if str(SERVER3_ROOT) not in sys.path:
    sys.path.append(str(SERVER3_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.core.content_crypto import decrypt_reply_preview, resolve_message_content  # noqa: E402


async def verify_messages() -> None:
    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.DATABASE_NAME]
    messages = db.messages

    try:
        total = await messages.count_documents({})
        encrypted = await messages.count_documents({"content_encrypted": {"$exists": True}})
        plaintext = await messages.count_documents(
            {"content_encrypted": {"$exists": False}, "content": {"$type": "string"}}
        )
        reply_preview_plain = await messages.count_documents({"reply_to_data.content": {"$exists": True}})
        reply_preview_encrypted = await messages.count_documents(
            {"reply_to_data.content_encrypted": {"$exists": True}}
        )

        # print(
            # "message_encryption_summary "
            # f"total={total} encrypted={encrypted} plaintext={plaintext} "
            # f"reply_preview_plain={reply_preview_plain} reply_preview_encrypted={reply_preview_encrypted}"
        # )

        sample_encrypted = await messages.find_one({"content_encrypted": {"$exists": True}}, sort=[("_id", -1)])
        if sample_encrypted:
            preview = resolve_message_content(sample_encrypted, route="verify.encrypted_sample")
            # print(
                # f"encrypted_sample id={sample_encrypted['_id']} "
                # f"content_preview={preview[:80]!r}"
            # )
            reply_to_data = sample_encrypted.get("reply_to_data")
            if isinstance(reply_to_data, dict) and "content_encrypted" in reply_to_data:
                reply_preview = decrypt_reply_preview(
                    reply_to_data["content_encrypted"],
                    parent_document={**sample_encrypted, "_id": str(sample_encrypted["_id"])},
                    route="verify.reply_preview",
                )
                # print(
                    # f"encrypted_reply_preview_sample id={sample_encrypted['_id']} "
                    # f"reply_preview={reply_preview[:80]!r}"
                # )

        sample_plaintext = await messages.find_one(
            {"content_encrypted": {"$exists": False}, "content": {"$type": "string"}},
            sort=[("_id", -1)],
        )
        if sample_plaintext:
            preview = resolve_message_content(sample_plaintext, route="verify.plaintext_sample")
            # print(
                # f"plaintext_sample id={sample_plaintext['_id']} "
                # f"content_preview={preview[:80]!r}"
            # )
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(verify_messages())
