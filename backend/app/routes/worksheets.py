from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.dependencies.auth import require_teacher
from app.models.worksheet import WorksheetConfig
from app.repositories.cosmos_repo import CosmosRepo
from app.services.worksheet_service import WorksheetService

router = APIRouter()
_worksheet_service = WorksheetService()
_cosmos_repo = CosmosRepo()


@router.post("/generate", dependencies=[Depends(require_teacher)])
async def generate_worksheet(
    config: WorksheetConfig,
    background_tasks: BackgroundTasks,
    request: Request,
):
    """Start async worksheet generation. Returns immediately with worksheet_id."""
    teacher_id: str = request.state.user_id
    ws_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    doc = {
        "id": ws_id,
        "teacher_id": teacher_id,
        "config": config.model_dump(mode="json"),
        "theory_summary": "",
        "questions": [],
        "worksheet_html": "",
        "answer_key_html": "",
        "status": "generating",
        "created_at": now,
        "updated_at": now,
        "deleted": False,
        # Quick-access fields for list view
        "topic": config.topic,
        "subject": config.subject,
        "class_level": config.class_level,
        "board": config.board,
        "worksheet_type": config.worksheet_type.value,
        "num_questions": config.num_questions,
        "chapter": config.chapter,
    }
    await _cosmos_repo.create_worksheet(doc)
    background_tasks.add_task(
        _worksheet_service.generate_worksheet, config, teacher_id, ws_id
    )
    return {"worksheet_id": ws_id, "status": "generating"}


@router.get("/", dependencies=[Depends(require_teacher)])
async def list_worksheets(request: Request):
    teacher_id: str = request.state.user_id
    worksheets = await _cosmos_repo.list_worksheets(teacher_id)
    return {"worksheets": worksheets}


@router.get("/{ws_id}", dependencies=[Depends(require_teacher)])
async def get_worksheet(ws_id: str, request: Request):
    teacher_id: str = request.state.user_id
    ws = await _cosmos_repo.get_worksheet(ws_id, teacher_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Worksheet not found")
    return ws


@router.get("/{ws_id}/download", dependencies=[Depends(require_teacher)])
async def download_worksheet(
    ws_id: str,
    request: Request,
    type: str = "worksheet",
):
    teacher_id: str = request.state.user_id
    ws = await _cosmos_repo.get_worksheet(ws_id, teacher_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Worksheet not found")
    if ws.get("status") != "ready":
        raise HTTPException(status_code=409, detail="Worksheet is not ready yet")

    html_map = {
        "worksheet": ws.get("worksheet_html", ""),
        "answer_key": ws.get("answer_key_html", ""),
    }
    html_content = html_map.get(type)
    if html_content is None:
        raise HTTPException(status_code=400, detail="type must be worksheet or answer_key")

    topic_slug = ws.get("topic", "worksheet").replace(" ", "_").lower()
    filename = f"{topic_slug}_{type}.html"
    return HTMLResponse(
        content=html_content,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{ws_id}", dependencies=[Depends(require_teacher)])
async def delete_worksheet(ws_id: str, request: Request):
    teacher_id: str = request.state.user_id
    ws = await _cosmos_repo.get_worksheet(ws_id, teacher_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Worksheet not found")
    await _cosmos_repo.soft_delete_worksheet(ws_id, teacher_id)
    return {"status": "deleted"}
