import logging
from typing import Optional

logger = logging.getLogger(__name__)

class CosmosRepo:
    """
    Data access layer for Azure Cosmos DB.
    All methods are stubs that log operations; replace with real Cosmos SDK calls.
    """
    def __init__(self):
        pass

    # ── User operations ──────────────────────────────────────────────────────

    async def get_user(self, user_id: str) -> dict:
        """Fetch a user document."""
        return {"id": user_id, "tier": "Free", "monthly_queries_used": 0}

    async def increment_user_usage(self, user_id: str):
        logger.info(f"Incremented usage for user: {user_id}")

    # ── Conversation operations ───────────────────────────────────────────────

    async def create_conversation(self, conversation_data: dict) -> str:
        """Create a new conversation document. Returns conversation id."""
        conv_id = conversation_data.get("id", "")
        logger.info(f"Conversation created in DB: {conv_id}")
        return conv_id

    async def save_conversation(self, conversation_data: dict):
        """Upsert a conversation/message log entry."""
        logger.info(f"Conversation saved to DB: {conversation_data.get('id')}")

    async def get_conversation(self, conversation_id: str) -> Optional[dict]:
        """Fetch a conversation document by id."""
        logger.info(f"Fetching conversation: {conversation_id}")
        # TODO: Implement actual Cosmos DB query
        return None

    async def update_conversation_title(self, conversation_id: str, title: str):
        """Update the title field of a conversation."""
        logger.info(f"Updated title for conversation {conversation_id}: {title}")
        # TODO: Cosmos DB partial update / patch

    async def append_message(self, conversation_id: str, message: dict):
        """Append a message to an existing conversation's messages array."""
        logger.info(f"Appended message {message.get('id')} to conversation {conversation_id}")
        # TODO: Cosmos DB array append via stored procedure or replace

    async def get_conversation_history(
        self,
        conversation_id: str,
        max_turns: int = 6,
        max_tokens: int = 1500,
    ) -> list:
        """
        Return last N turns (user+assistant pairs) from a conversation,
        trimmed to fit within max_tokens. Format: [{"role": ..., "content": ...}]
        """
        logger.info(f"Fetching history for conversation: {conversation_id}")
        # TODO: Implement real Cosmos DB query and token trimming
        return []

    # ── Message operations ────────────────────────────────────────────────────

    async def get_message(self, conversation_id: str, message_id: str) -> Optional[dict]:
        """Fetch a single message from a conversation."""
        logger.info(f"Fetching message {message_id} from conversation {conversation_id}")
        # TODO: Implement real Cosmos DB query
        return None

    async def update_message(self, conversation_id: str, message_id: str, updates: dict):
        """Apply partial updates to a message document."""
        logger.info(f"Updated message {message_id} in conversation {conversation_id}: {updates}")
        # TODO: Cosmos DB patch

    async def delete_messages_after(self, conversation_id: str, message_id: str):
        """Delete all messages in a conversation that come after the given message_id."""
        logger.info(f"Deleting messages after {message_id} in conversation {conversation_id}")
        # TODO: Implement Cosmos DB bulk delete

    # ── Feedback operations ───────────────────────────────────────────────────

    async def save_bookmark(self, bookmark_data: dict):
        """Upsert a bookmark record for an assistant message."""
        logger.info(f"Bookmark saved: msg={bookmark_data.get('message_id')} conv={bookmark_data.get('conversation_id')}")
        # TODO: Cosmos DB upsert into 'bookmarks' container keyed by message_id + user_id

    async def flag_message_for_review(self, message_id: str):
        """Set needs_review=true and increment dislike_count on a message."""
        logger.info(f"Flagging message for review: {message_id}")
        # TODO: Cosmos DB patch: needs_review=true, dislike_count += 1

    async def get_message_dislike_count(self, message_id: str) -> int:
        """Return the current dislike_count for a message."""
        logger.info(f"Fetching dislike count for message: {message_id}")
        # TODO: Implement real query
        return 0

    async def create_auto_review_task(self, message_id: str):
        """Create an auto-flagged teacher review task (not student-initiated, no quota impact)."""
        logger.info(f"Auto-review task created for message: {message_id}")
        # TODO: Insert lightweight ticket into review_tasks container

    async def add_to_cache_candidate(self, message_id: str):
        """Add a liked answer to the candidate_for_cache queue."""
        logger.info(f"Added message {message_id} to cache candidate queue")
        # TODO: Cosmos DB insert / INCR in candidate_cache container

    # ── Usage / analytics ────────────────────────────────────────────────────

    async def log_query_usage(self, usage: dict):
        """Log model usage and cost. Keys: timestamp, model, tokens_in, tokens_out, cost."""
        logger.info(f"Query usage logged: {usage}")
        # TODO: Write to 'usage_logs' container

    # ── Ticket operations ─────────────────────────────────────────────────────

    async def count_user_tickets_this_month(self, user_id: str) -> int:
        return 0

    async def create_ticket(self, ticket_data: dict):
        logger.info(f"Ticket created in DB: {ticket_data.get('ticket_id')}")

    async def get_tickets_by_user(self, user_id: str) -> list:
        return []

    async def get_open_tickets(self) -> list:
        return []

    async def get_ticket(self, ticket_id: str) -> dict:
        return {
            "ticket_id": ticket_id,
            "status": "OPEN",
            "user_id": "mock_user",
            "question": "stub question",
            "board": "CBSE",
            "class_level": 10,
            "subject": "Math",
        }

    async def assign_ticket(self, ticket_id: str, teacher_id: str):
        logger.info(f"Ticket {ticket_id} assigned to {teacher_id}")

    async def update_ticket_status(
        self,
        ticket_id: str,
        status: str,
        answer: str = None,
        teacher_id: str = None,
    ):
        logger.info(f"Ticket {ticket_id} resolved by {teacher_id}")
