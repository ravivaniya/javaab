import uuid
from datetime import datetime
import logging

from app.models.schemas import TicketCreateRequest, TicketResponseRequest
from app.repositories.cosmos_repo import CosmosRepo
from app.services.cache_service import CacheService, VerifiedAnswer

logger = logging.getLogger(__name__)

class TicketService:
    """
    Central business logic for Teacher Ticket Escalation & Native Cache Sinking.
    """
    def __init__(self):
        self.cosmos_repo = CosmosRepo()
        self.cache_service = CacheService()

    async def create_ticket(self, request: TicketCreateRequest, user_tier: str) -> str:
        """Enforces limits, formats DB entries, triggers auto-assigns."""
        if user_tier.upper() != "PRO":
            raise ValueError("Only Pro users can escalate to a teacher.")
            
        count = await self.cosmos_repo.count_user_tickets_this_month(request.user_id)
        if count >= 3:
            raise ValueError("You have reached your limit of 3 teacher tickets this month.")
            
        date_str = datetime.now().strftime("%Y%m%d")
        ticket_id = f"TKT-{date_str}-{str(uuid.uuid4())[:8]}"
        
        ticket_data = {
            "ticket_id": ticket_id,
            "user_id": request.user_id,
            "status": "OPEN",
            "question": request.question,
            "image_base64": request.image_base64,
            "board": request.board,
            "class_level": request.class_level,
            "subject": request.subject,
            "ai_attempts": request.ai_attempts,
            "created_at": datetime.utcnow().isoformat()
        }
        
        await self.cosmos_repo.create_ticket(ticket_data)
        
        # Trigger internal round robin task background
        await self.auto_assign_ticket(ticket_id, request.subject)
        return ticket_id

    async def auto_assign_ticket(self, ticket_id: str, subject: str):
        """Stubs out internal subject-based round-robin balancing."""
        logger.info(f"System evaluating round-robin limits for {subject} teachers matching ticket {ticket_id}.")

    async def resolve_ticket(self, ticket_id: str, request: TicketResponseRequest):
        """Resolves the DB node + Pipes directly into the RAG Pipeline."""
        ticket = await self.cosmos_repo.get_ticket(ticket_id)
        if not ticket:
            raise ValueError("Ticket not found")
            
        # 1. Update CosmosDB Record
        await self.cosmos_repo.update_ticket_status(
            ticket_id, 
            status="RESOLVED", 
            answer=request.answer, 
            teacher_id=request.teacher_id
        )
        
        # 2. Native RAG Pipeline Synthesis
        verified_cache = VerifiedAnswer(
            cache_id=f"VER-{ticket_id}",
            question=ticket.get("question"),
            answers={"en": request.answer}, # Hardcoding EN for demo bounds
            board=ticket.get("board"),
            class_level=ticket.get("class_level"),
            subject=ticket.get("subject"),
            verified_by=request.teacher_id,
            verified_at=datetime.utcnow().isoformat(),
            source_citation=request.source_citation
        )
        
        # Pushes via CacheService into Redis AND Azure AI Search seamlessly
        await self.cache_service.store_verified_answer(verified_cache)
        logger.info(f"Cache organically expanded via Ticket Resolution: VER-{ticket_id}")
        
        # 3. Simulate Push Notification Event Emitters
        logger.info(f">>> [PUSH_NOTIFICATION] Alerting User {ticket.get('user_id')}: Your ticket {ticket_id} has been answered! >>>")
