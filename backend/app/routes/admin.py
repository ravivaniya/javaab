from fastapi import APIRouter, HTTPException

from app.models.schemas import TicketResponseRequest
from app.services.ticket_service import TicketService
from app.repositories.cosmos_repo import CosmosRepo

router = APIRouter()
ticket_service = TicketService()
cosmos_repo = CosmosRepo()

@router.get("/tickets")
async def list_open_tickets(status: str = "OPEN"):
    """
    Teacher portal: get overview of open tickets sorted automatically by time.
    """
    if status != "OPEN":
        return {"tickets": []}
        
    open_tkts = await cosmos_repo.get_open_tickets()
    return {"tickets": open_tkts}

@router.post("/tickets/{ticket_id}/assign")
async def assign_ticket(ticket_id: str, teacher_id: str):
    """
    Teacher explicitly locks an open ticket.
    """
    ticket = await cosmos_repo.get_ticket(ticket_id)
    if not ticket or ticket.get("status") != "OPEN":
        raise HTTPException(status_code=400, detail="Ticket is either invalid or already assigned.")
        
    await cosmos_repo.assign_ticket(ticket_id, teacher_id)
    return {"status": "assigned"}

@router.post("/tickets/{ticket_id}/respond")
async def resolve_ticket(ticket_id: str, request: TicketResponseRequest):
    """
    Teacher portal: resolve a student ticket, trigger Push notifications, 
    and securely append logic natively to Cache abstractions!
    """
    try:
        await ticket_service.resolve_ticket(ticket_id, request)
        return {"status": "resolved and added to global cache mapping"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
