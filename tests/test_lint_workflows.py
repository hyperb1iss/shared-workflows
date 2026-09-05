"""Exercise queue validation alongside the real actionlint syntax checker."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lint_workflows.py"


def lint(tmp_path: Path, concurrency: str, *, job_scope: bool = False, extra: str = ""):
    path = tmp_path / "workflow.yml"
    scope = "    " if job_scope else ""
    section = f"{scope}concurrency:\n{scope}  group: publish\n" + "".join(
        f"{scope}  {line}\n" for line in concurrency.splitlines()
    )
    path.write_text(
        "name: Queue test\non: push\n"
        + ("" if job_scope else section)
        + "jobs:\n  test:\n    runs-on: ubuntu-latest\n"
        + (section if job_scope else "")
        + extra
        + "    steps:\n      - run: echo valid\n"
    )
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path)], text=True, capture_output=True, check=False
    )


@pytest.mark.parametrize("job_scope", [False, True])
@pytest.mark.parametrize(
    "queue",
    ["queue: single", "queue: max", "queue: max\ncancel-in-progress: false", 'queue: "single"'],
)
def test_valid_queues(tmp_path: Path, job_scope: bool, queue: str):
    result = lint(tmp_path, queue, job_scope=job_scope)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "queue",
    [
        "queue: unlimited",
        "queue: true",
        "queue: 2",
        "queue: null",
        "queue: [max]",
        "queue: {value: max}",
        "queue: ${{ github.ref }}",
        "queue: max\ncancel-in-progress: true",
        'queue: max\ncancel-in-progress: "false"',
        "queue: max\ncancel-in-progress: ${{ false }}",
        "queue: single\nqueue: single",
    ],
)
def test_invalid_queues(tmp_path: Path, queue: str):
    result = lint(tmp_path, queue)
    assert result.returncode != 0
    assert "[queue-check]" in result.stderr
    assert str(tmp_path / "workflow.yml") in result.stderr


@pytest.mark.parametrize(
    "queue,extra,diagnostic",
    [
        ("quue: max", "", 'unexpected key "quue"'),
        ("queue: single", "    queue: max\n", 'unexpected key "queue" for "job"'),
        ("queue: single", "    runs-onn: ubuntu-latest\n", 'unexpected key "runs-onn"'),
    ],
)
def test_unrelated_syntax_is_not_suppressed(
    tmp_path: Path, queue: str, extra: str, diagnostic: str
):
    result = lint(tmp_path, queue, extra=extra)
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert diagnostic in output
    assert "[syntax-check]" in output
    assert str(tmp_path / "workflow.yml") in output


def test_missing_executable_is_failure(tmp_path: Path):
    path = tmp_path / "workflow.yml"
    path.write_text("name: Test\non: push\njobs: {}\n")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--actionlint", str(tmp_path / "absent"), str(path)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "Cannot run actionlint" in result.stderr
