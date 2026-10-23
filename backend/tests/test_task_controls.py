import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api.routes import archive_task, cancel_task, create_task, list_tasks, retry_task
from app.db.base import Base
from app.models import AgentActivity, Task, TaskStep
from app.schemas.tasks import TaskArchiveRequest, TaskCreate
from app.services import gemini


@pytest.fixture
def db_session(monkeypatch):
    monkeypatch.setattr(gemini.settings, "ai_provider", "openrouter")
    monkeypatch.setattr(gemini.settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(
        gemini.settings, "openrouter_model", "nvidia/nemotron-3.5-super-vl:free"
    )
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def test_task_creation_rejects_stale_minimax_configuration(db_session, monkeypatch):
    monkeypatch.setattr(
        gemini.settings,
        "openrouter_model",
        "minimax/minimax-m3.1-flash:free",
    )
    background_tasks = BackgroundTasks()

    with pytest.raises(HTTPException) as error:
        create_task(
            TaskCreate(instruction="Buat proyek"),
            background_tasks,
            db_session,
        )

    assert error.value.status_code == 503
    assert "environment proses" in error.value.detail
    assert db_session.scalar(select(Task)) is None
    assert not background_tasks.tasks


def test_retry_creates_a_new_task_with_same_instruction(db_session):
    failed = Task(instruction="Buat README", status="failed")
    db_session.add(failed)
    db_session.commit()
    background_tasks = BackgroundTasks()

    retried = retry_task(failed.id, background_tasks, db_session)

    new_task = db_session.get(Task, retried.id)
    assert retried.id != failed.id
    assert new_task is not None
    assert new_task.instruction == failed.instruction
    assert new_task.status == "thinking"
    assert len(background_tasks.tasks) == 1


def test_cancel_marks_task_and_unfinished_steps_cancelled(db_session):
    task = Task(instruction="Buat komponen", status="working")
    task.steps = [
        TaskStep(position=1, agent_name="programmer", title="Komponen", expected_output="Kode", status="working"),
        TaskStep(position=2, agent_name="researcher", title="Riset", expected_output="Ringkasan", status="pending"),
        TaskStep(position=3, agent_name="designer", title="Selesai", expected_output="Spesifikasi", status="completed"),
    ]
    db_session.add(task)
    db_session.commit()

    result = cancel_task(task.id, db_session)

    db_session.refresh(task)
    assert result == {"status": "cancelled"}
    assert task.status == "cancelled"
    assert [step.status for step in task.steps] == ["cancelled", "cancelled", "completed"]
    assert db_session.scalar(
        select(AgentActivity).where(AgentActivity.task_id == task.id)
    ).status == "cancelled"


def test_active_task_cannot_be_archived_and_archived_tasks_can_be_filtered(db_session):
    task = Task(instruction="Task berjalan", status="working")
    db_session.add(task)
    db_session.commit()

    with pytest.raises(HTTPException) as error:
        archive_task(task.id, TaskArchiveRequest(archived=True), db_session)
    assert error.value.status_code == 409

    task.status = "completed"
    db_session.commit()
    assert archive_task(task.id, TaskArchiveRequest(archived=True), db_session) == {"archived": True}
    assert list_tasks(False, db_session) == []
    assert list_tasks(True, db_session)[0].archived is True
