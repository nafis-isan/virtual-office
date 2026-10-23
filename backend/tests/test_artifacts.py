import io
import zipfile

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routes import download_task_artifacts
from app.db.base import Base
from app.models import Artifact, Task, TaskStep
from app.services import artifact_bundle, artifacts
from app.services import orchestrator
from app.services.orchestrator import (
    APPLICATION_DESIGNER_INSTRUCTIONS,
    _extract_generated_files,
    _generate_application_programmer_output,
    _previous_designer_specification,
    _validate_application_artifacts,
)


def test_extract_generated_files_reads_paths_and_preserves_file_content():
    output = (
        "File:\n```typescript path=src/app.ts\n"
        "export const app = true\n```\n"
    )

    assert _extract_generated_files(output) == [
        ("src/app.ts", "export const app = true\n")
    ]


def test_extract_generated_files_accepts_quoted_path_with_spacing():
    output = (
        "```php filename = \"app/Models/Employee.php\"\n"
        "<?php\n"
        "```\n"
    )

    assert _extract_generated_files(output) == [
        ("app/Models/Employee.php", "<?php\n")
    ]


def test_application_designer_can_provide_text_without_generated_files():
    _validate_application_artifacts("Buatkan aplikasi karyawan", "designer", [])


def test_application_designer_prompt_is_implementation_guidance_not_a_mockup():
    assert "Jangan membuat mockup, wireframe" in APPLICATION_DESIGNER_INSTRUCTIONS
    assert "warna utama dan aksen dalam HEX" in APPLICATION_DESIGNER_INSTRUCTIONS
    assert "selector CSS atau class" in APPLICATION_DESIGNER_INSTRUCTIONS
    assert "resources/css/app.css" in APPLICATION_DESIGNER_INSTRUCTIONS
    assert "Tailwind" in APPLICATION_DESIGNER_INSTRUCTIONS


def test_programmer_receives_completed_designer_specification():
    task = Task(instruction="Buatkan aplikasi Laravel CRUD")
    designer_step = TaskStep(
        position=1,
        agent_name="designer",
        title="Ide UI/UX",
        expected_output="Spesifikasi teks",
        status="completed",
        output="Gunakan tabel responsif dengan filter dan modal edit.",
    )
    programmer_step = TaskStep(
        position=2,
        agent_name="programmer",
        title="Buat aplikasi",
        expected_output="File proyek",
        status="working",
    )
    task.steps = [designer_step, programmer_step]

    context = _previous_designer_specification(task, programmer_step)

    assert "Gunakan tabel responsif dengan filter dan modal edit." in context
    assert "panduan implementasi" in context


def test_programmer_does_not_receive_pending_or_unrelated_designer_specification():
    task = Task(instruction="Buatkan aplikasi Laravel CRUD")
    designer_step = TaskStep(
        position=1,
        agent_name="designer",
        title="Ide UI/UX",
        expected_output="Spesifikasi teks",
        status="working",
        output="Belum selesai",
    )
    programmer_step = TaskStep(
        position=2,
        agent_name="programmer",
        title="Buat aplikasi",
        expected_output="File proyek",
        status="working",
    )
    task.steps = [designer_step, programmer_step]

    assert _previous_designer_specification(task, programmer_step) == ""


def test_application_programmer_requires_generated_project_files():
    with pytest.raises(ValueError, match="belum menghasilkan file kode proyek"):
        _validate_application_artifacts("Buatkan aplikasi karyawan", "programmer", [])

    _validate_application_artifacts(
        "Buatkan aplikasi karyawan",
        "programmer",
        [("app/Employee.php", "<?php")],
    )


def test_application_programmer_retries_when_first_response_has_no_file_fences(
    monkeypatch,
):
    responses = iter(
        [
            "Berikut penjelasan implementasinya.",
            "```html path=resources/views/home.blade.php\n<h1>Halo</h1>\n```",
        ]
    )
    prompts = []

    def fake_generate_text(prompt):
        prompts.append(prompt)
        return next(responses)

    monkeypatch.setattr(orchestrator, "generate_text", fake_generate_text)

    output, files, rejected_paths = _generate_application_programmer_output(
        "Buat aplikasi Laravel"
    )

    assert len(prompts) == 2
    assert "PERBAIKAN WAJIB" in prompts[1]
    assert output.startswith("```html path=")
    assert files == [("resources/views/home.blade.php", "<h1>Halo</h1>\n")]
    assert rejected_paths == []


def test_application_programmer_retry_keeps_protected_files_rejected(monkeypatch):
    responses = iter(
        [
            "Penjelasan tanpa file.",
            "```env path=.env\nSECRET=value\n```",
            "```env path=.env\nSECRET=value\n```",
        ]
    )
    monkeypatch.setattr(
        orchestrator, "generate_text", lambda *_args, **_kwargs: next(responses)
    )

    _output, files, rejected_paths = _generate_application_programmer_output(
        "Buat aplikasi Laravel"
    )

    assert files == []
    assert rejected_paths == [".env"]


def test_application_programmer_makes_two_format_correction_attempts(monkeypatch):
    prompts = []

    def fake_generate_text(prompt):
        prompts.append(prompt)
        return "Penjelasan saja."

    monkeypatch.setattr(orchestrator, "generate_text", fake_generate_text)

    _output, files, rejected_paths = _generate_application_programmer_output(
        "Buat aplikasi Laravel"
    )

    assert len(prompts) == 3
    assert "PERBAIKAN WAJIB (1/2)" in prompts[1]
    assert "PERBAIKAN WAJIB (2/2)" in prompts[2]
    assert files == []
    assert rejected_paths == []


def test_extract_generated_markdown_file_with_nested_code_fence():
    output = (
        "````markdown path=README.md\n"
        "# Petunjuk\n\n```bash\nnpm run dev\n```\n"
        "````"
    )

    assert _extract_generated_files(output) == [
        ("README.md", "# Petunjuk\n\n```bash\nnpm run dev\n```\n")
    ]


@pytest.mark.parametrize(
    "path",
    [
        "../outside.txt",
        "src/../../outside.txt",
        "C:\\outside.txt",
        ".env",
        "config/.env.local",
        ".git/config",
        "private.pem",
    ],
)
def test_workspace_rejects_paths_outside_or_protected(path, tmp_path, monkeypatch):
    monkeypatch.setattr(artifacts.settings, "workspace_root", str(tmp_path))

    with pytest.raises(ValueError):
        artifacts.validate_relative_path(path)


def test_workspace_file_must_be_compared_before_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(artifacts.settings, "workspace_root", str(tmp_path))
    artifacts.save_workspace_file("src/app.ts", "old\n", overwrite=False)

    with pytest.raises(HTTPException) as error:
        artifacts.save_workspace_file("src/app.ts", "new\n", overwrite=False)

    assert error.value.status_code == 409
    _, current_content, digest = artifacts.read_workspace_file("src/app.ts")
    assert current_content == "old\n"
    assert digest is not None
    with pytest.raises(HTTPException) as stale:
        artifacts.save_workspace_file(
            "src/app.ts",
            "new\n",
            overwrite=True,
            expected_sha256="0" * 64,
        )
    assert stale.value.status_code == 409
    artifacts.save_workspace_file(
        "src/app.ts",
        "new\n",
        overwrite=True,
        expected_sha256=digest,
    )
    assert artifacts.read_workspace_file("src/app.ts")[1] == "new\n"


def test_workspace_rejects_symlinked_parent_outside_root(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    try:
        (workspace / "linked").symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"Symbolic links are unavailable: {error}")
    monkeypatch.setattr(artifacts.settings, "workspace_root", str(workspace))

    with pytest.raises(HTTPException) as error:
        artifacts.save_workspace_file("linked/escape.txt", "nope", overwrite=False)

    assert error.value.status_code == 422
    assert not (outside / "escape.txt").exists()


def test_generated_file_path_rejects_traversal():
    output = "```python path=../secret.py\nprint('no')\n```"

    assert _extract_generated_files(output) == []


def test_protected_generated_file_does_not_discard_safe_project_files():
    output = (
        "```env path=.env\nWEATHER_API_KEY=secret\n```\n"
        "```python path=weather_app.py\nprint('weather')\n```"
    )
    rejected_paths = []

    files = _extract_generated_files(output, rejected_paths=rejected_paths)

    assert files == [("weather_app.py", "print('weather')\n")]
    assert rejected_paths == [".env"]


def test_invalid_generated_path_does_not_fail_when_collecting_safe_files():
    output = (
        "```python path=../outside.py\nprint('unsafe')\n```\n"
        "```python path=main.py\nprint('safe')\n```"
    )
    rejected_paths = []

    files = _extract_generated_files(output, rejected_paths=rejected_paths)

    assert files == [("main.py", "print('safe')\n")]
    assert rejected_paths == ["../outside.py"]


def test_project_archive_preserves_paths_and_uses_latest_duplicate():
    archive_bytes = artifact_bundle.build_project_archive(
        [
            ("src/weather.py", "old"),
            ("README.md", "# Weather app"),
            ("src/weather.py", "new"),
        ]
    )

    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        assert archive.namelist() == ["src/weather.py", "README.md"]
        assert archive.read("src/weather.py").decode() == "new"
        assert archive.read("README.md").decode() == "# Weather app"


def test_project_archive_excludes_protected_paths():
    archive_bytes = artifact_bundle.build_project_archive(
        [
            (".env", "SECRET=value"),
            ("main.py", "print('safe')"),
        ]
    )

    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        assert archive.namelist() == ["main.py"]


def test_project_archive_rejects_when_only_protected_files_are_available():
    with pytest.raises(ValueError, match="Tidak ada file proyek"):
        artifact_bundle.build_project_archive([(".env", "SECRET=value")])


def test_download_task_artifacts_returns_a_project_zip():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        task = Task(instruction="Buat aplikasi cuaca", status="completed")
        task.steps = [
            TaskStep(
                position=1,
                agent_name="programmer",
                title="Buat kode",
                expected_output="File aplikasi",
                status="completed",
            )
        ]
        db.add(task)
        db.flush()
        db.add_all(
            [
                Artifact(
                    task_id=task.id,
                    step_id=task.steps[0].id,
                    name="src/main.py",
                    kind="file",
                    content="print('weather')",
                ),
                Artifact(
                    task_id=task.id,
                    step_id=task.steps[0].id,
                    name=".env",
                    kind="file",
                    content="SECRET=value",
                ),
            ]
        )
        db.commit()

        response = download_task_artifacts(task.id, db)

    assert response.media_type == "application/zip"
    assert response.headers["content-disposition"] == (
        f'attachment; filename="nf-office-task-{task.id}.zip"'
    )
    with zipfile.ZipFile(io.BytesIO(response.body)) as archive:
        assert archive.namelist() == ["src/main.py"]
        assert archive.read("src/main.py").decode() == "print('weather')"
