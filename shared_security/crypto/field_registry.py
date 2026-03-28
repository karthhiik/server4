from dataclasses import dataclass, field


@dataclass(frozen=True)
class CollectionFieldPolicy:
    plaintext_fields: tuple[str, ...] = ()
    encrypted_fields: tuple[str, ...] = ()
    preview_fields: tuple[str, ...] = ()
    blind_index_fields: tuple[str, ...] = ()


COLLECTION_FIELD_REGISTRY: dict[str, CollectionFieldPolicy] = {
    "fastapi_community.idea_inputs": CollectionFieldPolicy(
        plaintext_fields=(
            "_id",
            "ideaId",
            "author",
            "inputType",
            "title",
            "rating",
            "isAnonymous",
            "helpfulCount",
            "replyCount",
            "createdAt",
            "updatedAt",
            "status",
        ),
        encrypted_fields=("content",),
    ),
    "fastapi_community.idea_input_replies": CollectionFieldPolicy(
        plaintext_fields=(
            "_id",
            "inputId",
            "ideaId",
            "author",
            "isAnonymous",
            "createdAt",
            "updatedAt",
            "status",
        ),
        encrypted_fields=("content",),
    ),
    "server2.feedback": CollectionFieldPolicy(
        plaintext_fields=("_id", "name", "createdAt"),
        encrypted_fields=("email", "feedback"),
    ),
    "server2.cold_mail_logs": CollectionFieldPolicy(
        plaintext_fields=(
            "_id",
            "sender_user_id",
            "sender_email",
            "sender_role",
            "recipient_id",
            "angle",
            "draft_meta",
            "status",
            "created_at",
            "updated_at",
            "sent_at",
            "failed_at",
            "error",
        ),
        encrypted_fields=(
            "recipient_email",
            "recipient_name",
            "subject",
            "body",
            "reply_to_email",
        ),
    ),
    "server2.gtm_plans": CollectionFieldPolicy(
        plaintext_fields=(
            "_id",
            "user_id",
            "created_at",
            "business_name",
            "industry",
            "original_industry",
            "generation_id",
            "pdf_path",
            "pdf_filename",
        ),
        encrypted_fields=(
            "gtm_plan",
            "market_intelligence",
            "strategic_nodes",
            "node_connections",
            "plan_inputs",
        ),
    ),
    "server2.swot_plans": CollectionFieldPolicy(
        plaintext_fields=("_id", "user_id", "request_id", "created_at", "business_name", "industry", "growth_rate"),
        encrypted_fields=(
            "business_description",
            "target_market",
            "strengths",
            "weaknesses",
            "opportunities",
            "threats",
            "swot_analysis",
        ),
    ),
    "server2.pitch_plans": CollectionFieldPolicy(
        plaintext_fields=(
            "_id",
            "user_id",
            "task_id",
            "created_at",
            "industry_or_technology",
            "file_path",
            "filename",
        ),
        encrypted_fields=("pitch_description", "analysis_results"),
    ),
    "server3.messages": CollectionFieldPolicy(
        plaintext_fields=(
            "_id",
            "conversation_id",
            "sender_id",
            "type",
            "metadata",
            "reply_to",
            "reply_to_data",
            "status",
            "timestamp",
            "updated_at",
            "is_edited",
        ),
        encrypted_fields=("content",),
    ),
}
