from pathlib import Path


def test_ci_workflow_has_no_or_true_fallback() -> None:
    workflow = Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml"
    text = workflow.read_text(encoding="utf-8")
    assert " or True" not in text
    assert "or True" not in text
