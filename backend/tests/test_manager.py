import pytest
from pydantic import ValidationError

from app.agents import manager
from app.schemas.tasks import TaskCreate


def test_task_instruction_is_trimmed_and_cannot_be_blank():
    assert TaskCreate(instruction="  Buat rencana  ").instruction == "Buat rencana"
    with pytest.raises(ValidationError):
        TaskCreate(instruction="   ")


def test_create_plan_validates_and_trims_steps(monkeypatch):
    monkeypatch.setattr(
        manager,
        "generate_text",
        lambda *_args, **_kwargs: (
            '{"summary":" Rencana singkat ","steps":[{"agent":"researcher",'
            '"title":" Riset ","expected_output":" Ringkasan "}]}'
        ),
    )

    assert manager.create_plan("Buat rencana") == {
        "summary": "Rencana singkat",
        "steps": [
            {
                "agent": "researcher",
                "title": "Riset",
                "expected_output": "Ringkasan",
            }
        ],
    }


def test_create_plan_passes_retrieved_context_to_project_manager(monkeypatch):
    captured = {}

    def fake_generate(prompt, **_kwargs):
        captured["prompt"] = prompt
        return '{"summary":"Rencana","steps":[{"agent":"researcher","title":"Riset","expected_output":"Ringkasan"}]}'

    monkeypatch.setattr(manager, "generate_text", fake_generate)

    manager.create_plan("Cari aturan", context="[S1] Sumber: panduan.md\nAturan internal")

    assert "[S1] Sumber: panduan.md" in captured["prompt"]


def test_application_plan_always_includes_designer_and_programmer(monkeypatch):
    monkeypatch.setattr(
        manager,
        "generate_text",
        lambda *_args, **_kwargs: (
            '{"summary":"Buat aplikasi cuaca","steps":['
            '{"agent":"researcher","title":"Riset cuaca","expected_output":"API"}]}'
        ),
    )

    plan = manager.create_plan("Buatkan aplikasi cuaca")

    assert [step["agent"] for step in plan["steps"]] == [
        "researcher",
        "designer",
        "programmer",
    ]
    assert plan["steps"][1]["expected_output"].endswith("ui/preview.svg untuk desain aplikasi satu halaman.")


def test_application_plan_places_designer_before_programmer(monkeypatch):
    monkeypatch.setattr(
        manager,
        "generate_text",
        lambda *_args, **_kwargs: (
            '{"summary":"Buat CRUD karyawan","steps":['
            '{"agent":"programmer","title":"CRUD","expected_output":"Kode"}]}'
        ),
    )

    plan = manager.create_plan("Implementasikan aplikasi CRUD karyawan")

    assert [step["agent"] for step in plan["steps"]] == ["designer", "programmer"]


@pytest.mark.parametrize(
    "instruction",
    [
        "Buat proyek menggunakan Laravel untuk CRUD karyawan",
        "Buatkan project Nuxt.js untuk dashboard inventaris",
        "Create a Python project for weather reports",
    ],
)
def test_framework_project_requests_are_recognized_for_file_delivery(instruction):
    assert manager.is_application_build_request(instruction)


@pytest.mark.parametrize(
    "response",
    [
        "bukan JSON",
        '{"summary":"x","steps":[]}',
        '{"summary":"x","steps":[{"agent":"shell","title":"run","expected_output":"x"}]}',
        '{"summary":"x","steps":[{"agent":"designer","title":"x","expected_output":"x"}]*4}',
    ],
)
def test_create_plan_rejects_invalid_or_unsafe_responses(monkeypatch, response):
    monkeypatch.setattr(manager, "generate_text", lambda *_args, **_kwargs: response)

    with pytest.raises(ValueError):
        manager.create_plan("Buat rencana")
