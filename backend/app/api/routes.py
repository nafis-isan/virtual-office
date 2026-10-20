from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, select, update
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
    TaskStep,
)
from app.schemas.tasks import (
    ActivityRead,
    AgentRead,
    ApprovalDecision,
    ArtifactRead,
    ArtifactSaveRequest,
    ArtifactSaved,
    ArtifactComparison,
    TaskCreate,
    TaskArchiveRequest,
    TaskCreated,
    TaskDetail,
    TaskSummary,
    KnowledgeDocumentRead,
)
from app.services.orchestrator import run_task
from app.services.knowledge import index_upload, remove_document
from app.services.artifacts import read_workspace_file, save_workspace_file
from app.services.artifact_bundle import build_project_archive

router = APIRouter(prefix="/api")
MAX_ACTIVE_TASKS = 3

AGENT_DIRECTORY = [
    ("project_manager", "Project Manager", "Menyusun rencana dan merangkum hasil"),
    ("researcher", "Researcher", "Menganalisis kebutuhan dan informasi"),
    ("designer", "Designer", "Menyusun konsep dan spesifikasi UI/UX"),
    ("programmer", "Programmer", "Membuat draft kode dan file kerja"),
]
ACTIVE_TASK_STATUSES = ("thinking", "working", "waiting", "waiting_approval")


def _create_task(instruction: str, background_tasks: BackgroundTasks, db: Session) -> TaskCreated:
    active_tasks = db.scalar(
        select(func.count())
        .select_from(Task)
        .where(Task.status.in_(ACTIVE_TASK_STATUSES))
    )
    if active_tasks is not None and active_tasks >= MAX_ACTIVE_TASKS:
        raise HTTPException(
            status_code=429,
            detail="Terlalu banyak tugas aktif. Tunggu hingga tugas yang berjalan selesai.",
        )
    task = Task(instruction=instruction, status="thinking")
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


@router.post("/tasks", response_model=TaskCreated, status_code=202)
@router.post("/chat", response_model=TaskCreated, status_code=202)
def create_task(
    request: TaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> TaskCreated:
    return _create_task(request.instruction, background_tasks, db)


@router.get("/tasks", response_model=list[TaskSummary])
def list_tasks(
    include_archived: bool = False,
    db: Session = Depends(get_db),
) -> list[Task]:
    statement = select(Task)
    if not include_archived:
        statement = statement.where(Task.archived.is_(False))
    return list(db.scalars(statement.order_by(Task.created_at.desc()).limit(50)).all())


@router.post("/tasks/{task_id}/retry", response_model=TaskCreated, status_code=202)
def retry_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> TaskCreated:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Tugas tidak ditemukan.")
    if task.status != "failed":
        raise HTTPException(status_code=409, detail="Hanya tugas yang gagal dapat dicoba kembali.")
    return _create_task(task.instruction, background_tasks, db)


@router.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    transition = db.execute(
        update(Task)
        .where(Task.id == task_id, Task.status.in_(ACTIVE_TASK_STATUSES))
        .values(status="cancelled")
    )
    if transition.rowcount != 1:
        db.rollback()
        if db.get(Task, task_id) is None:
            raise HTTPException(status_code=404, detail="Tugas tidak ditemukan.")
        raise HTTPException(status_code=409, detail="Tugas ini tidak sedang berjalan.")
    db.execute(
        update(TaskStep)
        .where(TaskStep.task_id == task_id, TaskStep.status.in_(("pending", "working")))
        .values(status="cancelled")
    )
    db.add(
        AgentActivity(
            task_id=task_id,
            agent_name="project_manager",
            status="cancelled",
            message="Tugas dibatalkan oleh pengguna.",
        )
    )
    db.commit()
    return {"status": "cancelled"}


@router.post("/tasks/{task_id}/archive")
def archive_task(
    task_id: int,
    request: TaskArchiveRequest,
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    statement = update(Task).where(Task.id == task_id).values(archived=request.archived)
    if request.archived:
        statement = statement.where(Task.status.not_in(ACTIVE_TASK_STATUSES))
    result = db.execute(statement)
    if result.rowcount != 1:
        db.rollback()
        if db.get(Task, task_id) is None:
            raise HTTPException(status_code=404, detail="Tugas tidak ditemukan.")
        raise HTTPException(status_code=409, detail="Batalkan atau tunggu tugas sebelum mengarsipkannya.")
    db.commit()
    return {"archived": request.archived}


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
            select(Artifact)
            .where(Artifact.task_id == task_id)
            .order_by(Artifact.created_at, Artifact.id)
        ).all()
    )


@router.get("/tasks/{task_id}/artifacts/download")
def download_task_artifacts(task_id: int, db: Session = Depends(get_db)) -> Response:
    if db.get(Task, task_id) is None:
        raise HTTPException(status_code=404, detail="Tugas tidak ditemukan.")
    files = db.execute(
        select(Artifact.name, Artifact.content)
        .where(Artifact.task_id == task_id, Artifact.kind == "file")
        .order_by(Artifact.created_at, Artifact.id)
    ).all()
    if not files:
        raise HTTPException(status_code=404, detail="Belum ada file hasil untuk diunduh.")
    try:
        archive = build_project_archive(files)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=archive,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="nf-office-task-{task_id}.zip"'},
    )


@router.post(
    "/tasks/{task_id}/artifacts/{artifact_id}/save",
    response_model=ArtifactSaved,
    status_code=201,
)
def save_artifact(
    task_id: int,
    artifact_id: int,
    request: ArtifactSaveRequest,
    db: Session = Depends(get_db),
) -> ArtifactSaved:
    artifact = db.scalar(
        select(Artifact).where(
            Artifact.id == artifact_id,
            Artifact.task_id == task_id,
            Artifact.kind == "file",
        )
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="File hasil agent tidak ditemukan.")
    saved_path = save_workspace_file(
        request.relative_path,
        artifact.content,
        overwrite=request.overwrite,
        expected_sha256=request.expected_sha256,
    )
    return ArtifactSaved(path=saved_path)


@router.post(
    "/tasks/{task_id}/artifacts/{artifact_id}/compare",
    response_model=ArtifactComparison,
)
def compare_artifact(
    task_id: int,
    artifact_id: int,
    request: ArtifactSaveRequest,
    db: Session = Depends(get_db),
) -> ArtifactComparison:
    artifact = db.scalar(
        select(Artifact).where(
            Artifact.id == artifact_id,
            Artifact.task_id == task_id,
            Artifact.kind == "file",
        )
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="File hasil agent tidak ditemukan.")
    path, current_content, current_sha256 = read_workspace_file(request.relative_path)
    return ArtifactComparison(
        path=path,
        exists=current_content is not None,
        current_content=current_content,
        current_sha256=current_sha256,
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
