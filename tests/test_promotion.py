"""Exercise tag promotion against a local bare remote, including stale runs."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROMOTE = ROOT / "scripts/promote-tag.sh"


def git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
        cwd=cwd,
        text=True,
        stderr=subprocess.PIPE,
    ).strip()


@pytest.fixture
def repository(tmp_path: Path) -> tuple[Path, Path]:
    remote = tmp_path / "origin.git"
    repo = tmp_path / "checkout"
    git(tmp_path, "init", "--bare", str(remote))
    git(tmp_path, "init", "-b", "main", str(repo))
    git(repo, "config", "user.name", "Workflow Test")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "remote", "add", "origin", str(remote))
    commit(repo, "initial")
    git(repo, "push", "origin", "main")
    return repo, remote


def commit(repo: Path, message: str) -> str:
    git(repo, "commit", "--allow-empty", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def promote(repo: Path, sha: str | None = None, **extra: str) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "MAJOR_TAG": "v2",
        "GITHUB_SHA": sha or git(repo, "rev-parse", "HEAD"),
        "GITHUB_STEP_SUMMARY": str(repo / "summary.txt"),
        **extra,
    }
    return subprocess.run(["bash", str(PROMOTE)], cwd=repo, env=env, capture_output=True, text=True)


def test_bootstrap_and_forward_keep_v1_frozen(repository: tuple[Path, Path]):
    repo, remote = repository
    initial = git(repo, "rev-parse", "HEAD")
    git(repo, "tag", "v1")
    git(repo, "push", "origin", "v1")
    assert promote(repo).returncode == 0
    assert git(remote, "rev-parse", "v2") == initial
    newer = commit(repo, "next")
    git(repo, "push", "origin", "main")
    result = promote(repo)
    assert result.returncode == 0, result.stderr
    assert git(remote, "rev-parse", "v2") == newer
    assert git(remote, "rev-parse", "v1") == initial
    assert promote(repo).returncode == 0


def test_old_run_cannot_roll_tag_back(repository: tuple[Path, Path]):
    repo, remote = repository
    old = git(repo, "rev-parse", "HEAD")
    newer = commit(repo, "next")
    git(repo, "push", "origin", "main")
    assert promote(repo).returncode == 0
    git(repo, "checkout", "--detach", old)
    result = promote(repo)
    assert result.returncode == 0
    assert "Main has advanced" in result.stdout
    assert git(remote, "rev-parse", "v2") == newer


def test_rejects_unvalidated_checkout(repository: tuple[Path, Path]):
    repo, remote = repository
    result = promote(repo, "0" * 40)
    assert result.returncode != 0
    assert "does not match" in result.stdout
    assert git(remote, "tag", "-l", "v2") == ""


def test_rejects_tag_ahead_of_main(repository: tuple[Path, Path]):
    repo, remote = repository
    old = git(repo, "rev-parse", "HEAD")
    newer = commit(repo, "unmerged")
    git(repo, "tag", "v2", newer)
    git(repo, "push", "origin", "v2")
    git(repo, "checkout", "--detach", old)
    result = promote(repo)
    assert result.returncode != 0
    assert "backward or across histories" in result.stdout
    assert git(remote, "rev-parse", "v2") == newer


def test_annotated_tag_can_advance(repository: tuple[Path, Path]):
    repo, remote = repository
    git(repo, "-c", "tag.gpgsign=false", "tag", "-a", "v2", "-m", "v2")
    git(repo, "push", "origin", "v2")
    newer = commit(repo, "next")
    git(repo, "push", "origin", "main")
    result = promote(repo)
    assert result.returncode == 0, result.stderr
    assert git(remote, "rev-parse", "v2") == newer
