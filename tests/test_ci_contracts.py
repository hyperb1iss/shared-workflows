"""Check caller contracts and execute the CI scripts' failure paths."""

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"


def workflow(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / f"{name}.yml").read_text())


def run_step(name: str, step_name: str, cwd: Path, env: dict[str, str]):
    step = next(
        step
        for job in workflow(name)["jobs"].values()
        for step in job.get("steps", [])
        if step.get("name") == step_name
    )
    return subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", step["run"]],
        cwd=cwd,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
    )


def test_public_workflows_leave_concurrency_to_callers():
    for path in WORKFLOWS.glob("*.yml"):
        data = yaml.safe_load(path.read_text())
        if "workflow_call" in (data.get("on", data.get(True)) or {}):
            assert "concurrency" not in data, path.name


def test_promotion_depends_on_every_validation_job():
    jobs = workflow("ci")["jobs"]
    assert set(jobs["promote"]["needs"]) == set(jobs) - {"promote"}
    assert "github.event_name == 'push'" in jobs["promote"]["if"]
    assert "refs/heads/main" in jobs["promote"]["if"]
    assert workflow("release-tags").get(True) == {"workflow_call": None}


@pytest.mark.parametrize("engine", ["vitepress", "mkdocs"])
def test_docs_engines_are_accepted(tmp_path: Path, engine: str):
    result = run_step("docs-deploy", "Validate documentation engine", tmp_path, {"ENGINE": engine})
    assert result.returncode == 0


def test_unknown_docs_engine_fails(tmp_path: Path):
    result = run_step("docs-deploy", "Validate documentation engine", tmp_path, {"ENGINE": "mkdoc"})
    assert result.returncode != 0
    assert "Unknown documentation engine" in result.stdout


def test_moon_command_cannot_mask_failure(tmp_path: Path):
    executable = tmp_path / "moon"
    executable.write_text("#!/bin/sh\nexit 23\n")
    executable.chmod(0o755)
    result = run_step(
        "moon-ci",
        "Run moon commands",
        tmp_path,
        {
            "MOON_COMMANDS": "moon run check; echo hidden",
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
        },
    )
    assert result.returncode == 23
    assert not result.stdout.rstrip().endswith("\nhidden")


def test_python_build_does_not_request_publish_credentials():
    data = workflow("python-build")
    assert data["permissions"] == {"contents": "read"}
    assert not (WORKFLOWS / "python-publish.yml").exists()
    assert not any(
        "pypi-publish" in step.get("uses", "") for step in data["jobs"]["build"]["steps"]
    )


def test_readme_callers_match_public_interfaces():
    snippets = re.findall(r"```yaml\n(.*?)```", (ROOT / "README.md").read_text(), re.S)
    checked = 0
    for snippet in snippets:
        data = yaml.safe_load(snippet)
        if not isinstance(data, dict):
            continue
        for job in data.get("jobs", {}).values():
            uses = job.get("uses", "")
            match = re.fullmatch(
                r"hyperb1iss/shared-workflows/\.github/workflows/(.+)\.yml@v2", uses
            )
            if not match:
                continue
            checked += 1
            callee = workflow(match[1])
            contract = callee.get("on", callee.get(True))["workflow_call"]
            inputs = contract.get("inputs", {})
            assert set(job.get("with", {})) <= set(inputs), uses
            for name, spec in inputs.items():
                if spec.get("required"):
                    assert name in job.get("with", {}), (uses, name)
            permissions = job.get("permissions", data.get("permissions", {}))
            required = dict(callee.get("permissions", {}))
            for called_job in callee["jobs"].values():
                for permission, level in called_job.get("permissions", {}).items():
                    if level == "write" or permission not in required:
                        required[permission] = level
            for permission, level in required.items():
                assert permissions.get(permission) in (
                    {"read", "write"} if level == "read" else {level}
                ), (
                    uses,
                    permission,
                )
    assert checked >= 5, "No complete caller examples were validated"


@pytest.mark.parametrize("name", ["moon-ci", "docs-deploy"])
@pytest.mark.parametrize(
    ("manifest", "override", "expected"),
    [
        ({"packageManager": "pnpm@10.29.3"}, "", ""),
        ({"devEngines": {"packageManager": {"name": "pnpm", "version": "10.29.3"}}}, "", ""),
        ({}, "", "10"),
        ({}, "11.25.0", "11.25.0"),
    ],
)
def test_pnpm_infers_project_pin(
    tmp_path: Path, name: str, manifest: dict, override: str, expected: str
):
    import json

    package = tmp_path / "package.json"
    package.write_text(json.dumps(manifest))
    output = tmp_path / "output"
    result = run_step(
        name,
        "Resolve pnpm version",
        tmp_path,
        {"PACKAGE_JSON": str(package), "PNPM_VERSION": override, "GITHUB_OUTPUT": str(output)},
    )
    assert result.returncode == 0, result.stderr
    assert output.read_text() == f"version={expected}\n"


def test_python_ci_rejects_stale_lock(tmp_path: Path):
    import sys

    manifest = tmp_path / "pyproject.toml"
    manifest.write_text(
        '[project]\nname = "lock-probe"\nversion = "0.1.0"\n'
        'requires-python = ">=3.13"\ndependencies = []\n'
    )
    env = {"UV_PYTHON": sys.executable, "UV_OFFLINE": "true"}
    subprocess.run(["uv", "lock"], cwd=tmp_path, env={**os.environ, **env}, check=True)
    original = (tmp_path / "uv.lock").read_bytes()
    manifest.write_text(manifest.read_text().replace("0.1.0", "0.2.0"))
    result = run_step("python-ci", "Install dependencies", tmp_path, env)
    assert result.returncode != 0
    assert "lockfile" in result.stderr
    assert (tmp_path / "uv.lock").read_bytes() == original
