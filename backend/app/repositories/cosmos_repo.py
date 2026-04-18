import logging

logger = logging.getLogger(__name__)

class CosmosRepo:
    """
    Data access layer for Azure Cosmos DB.
    """
    def __init__(self):
        pass

    async def get_user(self, user_id: str) -> dict:
        """
        Fetch a user document.
        """
        # Stub: Return a mock user object representing CosmosDB data.
        return {
            "id": user_id, 
            "tier": "Free", 
            "monthly_queries_used": 0
        }

    async def increment_user_usage(self, user_id: str):
        pass

    async def save_conversation(self, conversation_data: dict):
        logger.info(f"Conversation saved to DB: {conversation_data.get('id')}")

    async def save_feedback(self, feedback_data: dict):
        logger.info(f"Feedback saved to DB: {feedback_data}")

    async def log_query_usage(self, usage: dict):
        """
        Log usage and cost of a query to Cosmos DB.
        Expected keys in dict: timestamp, model, tokens_in, tokens_out, cost.
        """
        # TODO: Implement write to 'usage_logs' container
        logger.info(f"Query usage logged: {usage}")

    # --- Ticket Operations Stub ---
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
            "subject": "Math"
        }

    async def assign_ticket(self, ticket_id: str, teacher_id: str):
        logger.info(f"Ticket {ticket_id} assigned to {teacher_id}")

    async def update_ticket_status(self, ticket_id: str, status: str, answer: str = None, teacher_id: str = None):
        logger.info(f"Ticket {ticket_id} resolved by {teacher_id}")
