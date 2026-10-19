from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import (
    Agent,
    AgentActivity,
    Artifact,
    Approval,
    KnowledgeDocument,
    Message,
    Task,
)
from app.schemas.tasks import (
    ActivityRead,
    AgentRead,
    ApprovalDecision,
    ArtifactRead,
    TaskCreate,
    TaskCreated,
    TaskDetail,
    TaskSummary,
    KnowledgeDocumentRead,
)
from app.services.orchestrator import run_task
from app.services.knowledge import index_upload, remove_document

router = APIRouter(prefix="/api")
MAX_ACTIVE_TASKS = 3

AGENT_DIRECTORY = [
    ("project_manager", "Project Manager", "Menyusun rencana dan merangkum hasil"),
    ("researcher", "Researcher", "Menganalisis kebutuhan dan informasi"),
    ("designer", "Designer", "Menyusun konsep dan spesifikasi UI/UX"),
    ("programmer", "Programmer", "Menyusun usulan implementasi dalam bentuk teks"),
]


@router.post("/tasks", response_model=TaskCreated, status_code=202)
@router.post("/chat", response_model=TaskCreated, status_code=202)
def create_task(
    request: TaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> TaskCreated:
    active_tasks = db.scalar(
        select(func.count())
        .select_from(Task)
        .where(Task.status.in_(("thinking", "working", "waiting", "waiting_approval")))
    )
    if active_tasks is not None and active_tasks >= MAX_ACTIVE_TASKS:
        raise HTTPException(
            status_code=429,
            detail="Terlalu banyak tugas aktif. Tunggu hingga tugas yang berjalan selesai.",
        )
    task = Task(instruction=request.instruction.strip(), status="thinking")
    db.add(task)
    db.flush()
    db.add(Message(task_id=task.id, sender="user", content=task.instruction))
    db.add(
        AgentActivity(
            task_id=task.id,
            agent_name="project_manager",
            status="thinking",
            message="Instruksi diterima, menunggu analisis.",
        )
    )
    db.commit()
    db.refresh(task)
    background_tasks.add_task(run_task, task.id)
    return TaskCreated(id=task.id, status=task.status)


@router.get("/tasks", response_model=list[TaskSummary])
def list_tasks(db: Session = Depends(get_db)) -> list[Task]:
    return list(db.scalars(select(Task).order_by(Task.created_at.desc()).limit(50)).all())


@router.get("/tasks/{task_id}", response_model=TaskDetail)
def get_task(task_id: int, db: Session = Depends(get_db)) -> Task:
    task = db.scalar(
        select(Task)
        .options(selectinload(Task.steps), selectinload(Task.messages))
        .where(Task.id == task_id)
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Tugas tidak ditemukan.")
    return task


@router.get("/agents", response_model=list[AgentRead])
def list_agents(db: Session = Depends(get_db)) -> list[AgentRead]:
    agents = {agent.name: agent for agent in db.scalars(select(Agent)).all()}
    return [
        AgentRead(
            name=name,
            display_name=display_name,
            role=role,
            status=agents[name].status if name in agents else "idle",
        )
        for name, display_name, role in AGENT_DIRECTORY
    ]


@router.get("/knowledge", response_model=list[KnowledgeDocumentRead])
def list_knowledge_documents(db: Session = Depends(get_db)) -> list[KnowledgeDocument]:
    return list(
        db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())).all()
    )


@router.post("/knowledge", response_model=KnowledgeDocumentRead, status_code=201)
async def upload_knowledge_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> KnowledgeDocument:
    return await index_upload(db, file)


@router.delete("/knowledge/{document_id}", status_code=204)
def delete_knowledge_document(
    document_id: int,
    db: Session = Depends(get_db),
) -> None:
    if not remove_document(db, document_id):
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan.")


@router.get("/tasks/{task_id}/activities", response_model=list[ActivityRead])
def list_activities(task_id: int, db: Session = Depends(get_db)) -> list[AgentActivity]:
    if db.get(Task, task_id) is None:
        raise HTTPException(status_code=404, detail="Tugas tidak ditemukan.")
    return list(
        db.scalars(
            select(AgentActivity)
            .where(AgentActivity.task_id == task_id)
            .order_by(AgentActivity.created_at, AgentActivity.id)
        ).all()
    )


@router.get("/tasks/{task_id}/artifacts", response_model=list[ArtifactRead])
def list_artifacts(task_id: int, db: Session = Depends(get_db)) -> list[Artifact]:
    if db.get(Task, task_id) is None:
        raise HTTPException(status_code=404, detail="Tugas tidak ditemukan.")
    return list(
        db.scalars(
            select(Artifact).where(Artifact.task_id == task_id).order_by(Artifact.created_at)
        ).all()
    )


@router.post("/approvals/{approval_id}/decision")
def decide_approval(
    approval_id: int,
    decision: ApprovalDecision,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    approval = db.get(Approval, approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Permintaan approval tidak ditemukan.")
    if approval.status != "waiting_approval":
        raise HTTPException(status_code=409, detail="Permintaan approval sudah diputuskan.")
    from datetime import datetime

    approval.status = "approved" if decision.decision == "approve" else "rejected"
    approval.decision_note = decision.note
    approval.decided_at = datetime.utcnow()
    db.commit()
    return {"status": approval.status}
