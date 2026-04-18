from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.models.schemas import TicketCreateRequest
from app.services.ticket_service import TicketService
from app.repositories.cosmos_repo import CosmosRepo

router = APIRouter()
ticket_service = TicketService()
cosmos_repo = CosmosRepo()

@router.post("/create")
async def create_ticket(request: TicketCreateRequest):
    """
    Create a teacher ticket. (PRO only)
    """
    user = await cosmos_repo.get_user(request.user_id)
    tier = user.get("tier", "Free")
    
    try:
        tkt_id = await ticket_service.create_ticket(request, tier)
        return {"status": "success", "ticket_id": tkt_id}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.get("/")
async def list_tickets(user_id: str):
    """
    List user's tickets.
    """
    tickets = await cosmos_repo.get_tickets_by_user(user_id)
    return {"tickets": tickets}

@router.get("/{ticket_id}")
async def get_ticket(ticket_id: str):
    """
    Get ticket status by ID.
    """
    ticket = await cosmos_repo.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"ticket": ticket}
