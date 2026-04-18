from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_subjects():
    """
    Browse available subjects and boards.
    """
    # TODO: Implement subject listing via CosmosDB or Search
    return {"subjects": []}

@router.get("/{subject_id}/chapters")
async def list_chapters(subject_id: str):
    """
    Browse chapters for a specific subject.
    """
    # TODO: Implement chapter listing
    return {"chapters": []}
