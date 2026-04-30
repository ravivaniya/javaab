from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.dependencies.auth import require_teacher
from app.models.paper import PaperConfig
from app.repositories.cosmos_repo import CosmosRepo
from app.services.paper_service import PaperService

router = APIRouter()
_paper_service = PaperService()
_cosmos_repo = CosmosRepo()


@router.post("/generate", dependencies=[Depends(require_teacher)])
async def generate_paper(
    config: PaperConfig,
    background_tasks: BackgroundTasks,
    request: Request,
):
    """Start async paper generation. Returns immediately with paper_id."""
    teacher_id: str = request.state.user_id
    paper_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    doc = {
        "id": paper_id,
        "teacher_id": teacher_id,
        "config": config.model_dump(mode="json"),
        "variants": [],
        "status": "generating",
        "created_at": now,
        "updated_at": now,
        "deleted": False,
        # Quick-access fields for list view
        "exam_title": config.exam_title,
        "subject": config.subject,
        "class_level": config.class_level,
        "board": config.board,
        "total_marks": config.total_marks,
        "duration_minutes": config.duration_minutes,
        "num_variants": config.num_variants,
        "chapters_count": len(config.chapters),
    }
    await _cosmos_repo.create_paper(doc)
    background_tasks.add_task(
        _paper_service.generate_paper, config, teacher_id, paper_id
    )
    return {"paper_id": paper_id, "status": "generating"}


@router.get("/", dependencies=[Depends(require_teacher)])
async def list_papers(request: Request):
    """List all papers created by this teacher."""
    teacher_id: str = request.state.user_id
    papers = await _cosmos_repo.list_papers(teacher_id)
    return {"papers": papers}


@router.get("/{paper_id}", dependencies=[Depends(require_teacher)])
async def get_paper(paper_id: str, request: Request):
    """Get a single paper with all variants."""
    teacher_id: str = request.state.user_id
    paper = await _cosmos_repo.get_paper(paper_id, teacher_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.get("/{paper_id}/download", dependencies=[Depends(require_teacher)])
async def download_paper(
    paper_id: str,
    request: Request,
    variant: str = "A",
    type: str = "paper",
):
    """Return the rendered HTML for a specific variant/type."""
    teacher_id: str = request.state.user_id
    paper = await _cosmos_repo.get_paper(paper_id, teacher_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    if paper.get("status") != "ready":
        raise HTTPException(status_code=409, detail="Paper is not ready yet")

    variant_label = f"Set {variant.upper()}"
    variant_data = next(
        (v for v in paper.get("variants", []) if v.get("variant_label") == variant_label),
        None,
    )
    if not variant_data:
        raise HTTPException(status_code=404, detail=f"Variant {variant} not found")

    html_map = {
        "paper": variant_data.get("paper_html", ""),
        "answer_key": variant_data.get("answer_key_html", ""),
        "marking_scheme": variant_data.get("marking_scheme_html", ""),
    }
    html_content = html_map.get(type)
    if html_content is None:
        raise HTTPException(status_code=400, detail="type must be paper, answer_key, or marking_scheme")

    subject_slug = paper.get("subject", "paper").replace(" ", "_").lower()
    filename = f"{subject_slug}_set{variant.upper()}_{type}.html"
    return HTMLResponse(
        content=html_content,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{paper_id}", dependencies=[Depends(require_teacher)])
async def delete_paper(paper_id: str, request: Request):
    """Soft-delete a paper."""
    teacher_id: str = request.state.user_id
    paper = await _cosmos_repo.get_paper(paper_id, teacher_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    await _cosmos_repo.soft_delete_paper(paper_id, teacher_id)
    return {"status": "deleted"}
