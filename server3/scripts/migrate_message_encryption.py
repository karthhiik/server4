import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER3_ROOT = REPO_ROOT / "server3"

if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))
if str(SERVER3_ROOT) not in sys.path:
    sys.path.append(str(SERVER3_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.core.content_crypto import encrypt_message_document, encrypt_reply_preview  # noqa: E402


def build_message_query() -> dict:
    return {
        "$or": [
            {"content_encrypted": {"$exists": False}, "content": {"$type": "string"}},
            {"reply_to_data.content": {"$exists": True, "$type": "string"}},
        ]
    }


def build_update_payload(document: dict, *, key_version: str) -> tuple[dict, dict]:
    working = {**document, "_id": str(document["_id"])}
    encrypted_document = encrypt_message_document(working, route="migration.server3.messages")

    set_fields: dict = {
        "encryption_status": "migrated",
        "encryption_version": key_version,
        "migrated_at": datetime.utcnow(),
    }
    unset_fields: dict = {}

    if "content_encrypted" in encrypted_document:
        set_fields["content_encrypted"] = encrypted_document["content_encrypted"]
        unset_fields["content"] = ""

    reply_to_data = document.get("reply_to_data")
    if isinstance(reply_to_data, dict) and isinstance(reply_to_data.get("content"), str):
        updated_reply_to_data = dict(reply_to_data)
        updated_reply_to_data["content_encrypted"] = encrypt_reply_preview(
            updated_reply_to_data["content"],
            parent_document=working,
            route="migration.server3.reply_preview",
        )
        updated_reply_to_data.pop("content", None)
        set_fields["reply_to_data"] = updated_reply_to_data

    return set_fields, unset_fields


async def migrate_messages(*, batch_size: int, limit: int | None, dry_run: bool) -> None:
    settings = get_settings()
    if not settings.ENCRYPTION_ENABLED:
        raise RuntimeError(
            "ENCRYPTION_ENABLED=false. Enable encryption in server3 env before running the migration."
        )

    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.DATABASE_NAME]
    messages = db.messages

    processed = 0
    updated = 0
    query = build_message_query()

    try:
        cursor = messages.find(query).sort("_id", 1).batch_size(batch_size)
        async for document in cursor:
            processed += 1
            set_fields, unset_fields = build_update_payload(
                document,
                key_version=settings.ENCRYPTION_KEY_VERSION,
            )

            if dry_run:
                # print(
                    # f"[dry-run] would migrate message_id={document['_id']} "
                    # f"set={list(set_fields.keys())} unset={list(unset_fields.keys())}"
                # )
            else:
                update_doc = {"$set": set_fields}
                if unset_fields:
                    update_doc["$unset"] = unset_fields
                result = await messages.update_one({"_id": document["_id"]}, update_doc)
                if result.modified_count:
                    updated += 1

            if limit is not None and processed >= limit:
                break
    finally:
        client.close()

    # print(
        # f"migration_complete processed={processed} updated={updated} "
        # f"dry_run={str(dry_run).lower()} batch_size={batch_size}"
    # )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate legacy server3 chat messages to encrypted content storage.")
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        migrate_messages(
            batch_size=args.batch_size,
            limit=args.limit,
            dry_run=args.dry_run,
        )
    )
