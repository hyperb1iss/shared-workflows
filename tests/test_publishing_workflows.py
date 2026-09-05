"""Exercise publishing workflow scripts with isolated artifacts and command doubles."""

import io
import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def script(workflow, step):
    config = yaml.safe_load((ROOT / ".github/workflows" / f"{workflow}.yml").read_text())
    return next(
        item["run"]
        for job in config["jobs"].values()
        for item in job["steps"]
        if item.get("name") == step
    )


@pytest.fixture
def sandbox(tmp_path):
    commands = tmp_path / "commands"
    commands.mkdir()
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    gh = commands / "gh"
    gh.write_text("""#!/usr/bin/env python3
import json, os, pathlib, shutil, sys
args = sys.argv[1:]
root = pathlib.Path(os.environ['FIXTURES'])
with open(os.environ['COMMAND_LOG'], 'a') as log:
    log.write(json.dumps(args) + '\\n')
if args[:1] == ['api'] and '--slurp' in args:
    print(json.dumps([{'artifacts': [{'name': p.name, 'expired': False} for p in root.iterdir()]}]))
elif args[:2] == ['run', 'download']:
    name = args[args.index('--name') + 1]
    shutil.copytree(root / name, args[args.index('--dir') + 1])
elif args[:1] == ['api'] and '--method' in args:
    print(sys.stdin.read())
elif args[:1] == ['api']:
    if 'CURRENT_FORMULA' not in os.environ:
        print('gh: Not Found (HTTP 404)', file=sys.stderr)
        sys.exit(1)
    import base64
    print(json.dumps({'sha': 'abc123', 'content': base64.b64encode(os.environ['CURRENT_FORMULA'].encode()).decode()}))
elif args[:2] == ['release', 'view']:
    directory = pathlib.Path(os.environ.get('RELEASE_ASSETS', '/nonexistent'))
    print(json.dumps({'assets': [{'name': p.name} for p in directory.iterdir()] if directory.exists() else []}))
elif args[:2] == ['release', 'download']:
    directory = pathlib.Path(args[args.index('--dir') + 1])
    directory.mkdir(exist_ok=True)
    name = args[args.index('--pattern') + 1]
    shutil.copyfile(pathlib.Path(os.environ['RELEASE_ASSETS']) / name, directory / name)
elif args[:2] == ['release', 'upload']:
    assert '--clobber' not in args
    if 'RELEASE_ASSETS' in os.environ:
        destination = pathlib.Path(os.environ['RELEASE_ASSETS']) / pathlib.Path(args[3]).name
        assert not destination.exists(), 'Asset already exists'
        shutil.copyfile(args[3], destination)
else:
    sys.exit('Unexpected gh arguments: ' + repr(args))
""")
    gh.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{commands}:{os.environ['PATH']}",
        "FIXTURES": str(fixtures),
        "COMMAND_LOG": str(tmp_path / "commands.jsonl"),
        "GITHUB_OUTPUT": str(tmp_path / "output"),
        "GITHUB_REPOSITORY": "owner/project",
        "GITHUB_RUN_ID": "123",
        "GITHUB_REF_NAME": "v1.2.3",
        "FORMULA_NAME": "sample",
        "FORMULA_DESC": 'A "quoted" #{description}',
        "FORMULA_HOMEPAGE": "https://example.com",
        "FORMULA_LICENSE": "MIT",
        "BINARY_NAMES": "one two three",
        "ARTIFACT_PATTERN": "binaries-*",
    }
    return work, fixtures, commands, env


def run(sandbox, workflow, step, **overrides):
    work, _, _, env = sandbox
    return subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", script(workflow, step)],
        cwd=work,
        env={**env, **overrides},
        text=True,
        capture_output=True,
    )


def artifact(fixtures, target, binaries=("one", "two", "three")):
    name = f"binaries-{target}"
    directory = fixtures / name
    directory.mkdir()
    with tarfile.open(directory / f"{name}.tar.gz", "w:gz") as archive:
        for binary in binaries:
            payload = f"{target}:{binary}".encode()
            info = tarfile.TarInfo(binary)
            info.size = len(payload)
            info.mode = 0o755
            archive.addfile(info, io.BytesIO(payload))
    return directory


@pytest.mark.parametrize(
    "targets", [("linux-amd64",), ("macos-arm64",), ("linux-amd64", "macos-arm64")]
)
def test_homebrew_available_platforms_and_binary_literals(sandbox, targets):
    work, fixtures, _, _ = sandbox
    for target in targets:
        artifact(fixtures, target)
    result = run(sandbox, "homebrew-update", "Prepare formula and release archives")
    assert result.returncode == 0, result.stderr
    formula = (work / "formula.rb").read_text()
    assert "['one', 'two', 'three']" in formula
    assert "desc 'A \"quoted\" #{description}'" in formula
    assert ("on_linux do" in formula) == ("linux-amd64" in targets)
    assert ("on_macos do" in formula) == ("macos-arm64" in targets)
    assert "sha256 ''" not in formula
    for target in targets:
        with tarfile.open(work / f"sample-1.2.3-{target}.tar.gz") as archive:
            assert archive.getmember("./one").mode & 0o111 == 0o111
            content = archive.extractfile("./one")
            assert content is not None
            assert content.read() == f"{target}:one".encode()


@pytest.mark.parametrize(
    "bad_input",
    [
        {"BINARY_NAMES": "one ../escape"},
        {"FORMULA_NAME": "../evil"},
        {"GITHUB_REF_NAME": "v1.2.3-rc.1"},
        {"FORMULA_HOMEPAGE": "https://example.com\ncode"},
    ],
)
def test_homebrew_rejects_invalid_inputs_before_external_work(sandbox, bad_input):
    result = run(sandbox, "homebrew-update", "Prepare formula and release archives", **bad_input)
    assert result.returncode != 0
    assert not Path(sandbox[3]["COMMAND_LOG"]).exists()


def test_homebrew_missing_binary_never_uploads(sandbox):
    artifact(sandbox[1], "linux-amd64", ("one",))
    result = run(sandbox, "homebrew-update", "Prepare formula and release archives")
    assert result.returncode != 0
    assert "Missing regular binary" in result.stderr
    assert "upload" not in Path(sandbox[3]["COMMAND_LOG"]).read_text()


def test_homebrew_no_artifacts_fails(sandbox):
    result = run(sandbox, "homebrew-update", "Prepare formula and release archives")
    assert result.returncode != 0
    assert "No supported binary artifacts" in result.stderr


def test_release_preserves_target_archives_and_executable_mode(sandbox):
    for target in ("linux-amd64", "linux-arm64", "macos-arm64"):
        artifact(sandbox[1], target)
    result = run(sandbox, "github-release", "Prepare release archives")
    assert result.returncode == 0, result.stderr
    archives = list((sandbox[0] / "release-assets").iterdir())
    assert len(archives) == 3
    for path in archives:
        target = path.name.removeprefix("binaries-").removesuffix(".tar.gz")
        with tarfile.open(path) as archive:
            content = archive.extractfile("one")
            assert content is not None
            assert content.read() == f"{target}:one".encode()
            assert archive.getmember("one").mode & 0o111 == 0o111


def test_release_missing_artifacts_fails(sandbox):
    result = run(sandbox, "github-release", "Prepare release archives")
    assert result.returncode != 0
    assert "No matching artifacts" in result.stderr


def test_release_rejects_raw_binary_contract(sandbox):
    directory = sandbox[1] / "binaries-linux-amd64"
    directory.mkdir()
    (directory / "one").write_text("raw")
    result = run(sandbox, "github-release", "Prepare release archives")
    assert result.returncode != 0
    assert "Expected binaries-linux-amd64.tar.gz" in result.stderr


@pytest.mark.parametrize("version", ["1.2.3", "2.0.0-rc.1", "main"])
def test_docker_validates_and_emits_version_only_tags(sandbox, version):
    result = run(
        sandbox,
        "docker-publish",
        "Validate image tags",
        VERSION_INPUT=version,
        REGISTRY="docker.io, ghcr.io",
        IMAGE_NAME="owner/project",
    )
    assert result.returncode == 0, result.stderr
    output = Path(sandbox[3]["GITHUB_OUTPUT"]).read_text()
    assert ":latest" not in output
    assert f"docker.io/owner/project:{version},ghcr.io/owner/project:{version}" in output


@pytest.mark.parametrize(
    "overrides",
    [
        {"VERSION_INPUT": "latest"},
        {"VERSION_INPUT": "branch/name"},
        {"REGISTRY": "ghcr.io,typo"},
        {"REGISTRY": "ghcr.io,ghcr.io"},
        {"IMAGE_NAME": "owner/project\ninjected"},
    ],
)
def test_docker_invalid_inputs_fail(sandbox, overrides):
    inputs = {"VERSION_INPUT": "1.2.3", "REGISTRY": "ghcr.io", "IMAGE_NAME": "owner/project"}
    result = run(sandbox, "docker-publish", "Validate image tags", **(inputs | overrides))
    assert result.returncode != 0
    assert not Path(sandbox[3]["GITHUB_OUTPUT"]).exists()


def mock_tags(sandbox):
    commands = sandbox[2]
    git = commands / "git"
    git.write_text('#!/bin/bash\nif [ "$1" = tag ]; then printf "%s\\n" "$GIT_TAGS"; fi\n')
    git.chmod(0o755)
    docker = commands / "docker"
    docker.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$COMMAND_LOG"\n')
    docker.chmod(0o755)


@pytest.mark.parametrize(
    ("version", "promoted"),
    [("1.2.3", False), ("2.0.0", True), ("2.1.0-rc.1", False), ("main", False)],
)
def test_docker_latest_preserves_newer_stable(sandbox, version, promoted):
    mock_tags(sandbox)
    result = run(
        sandbox,
        "docker-publish",
        "Promote newest stable image",
        VERSION=version,
        GIT_TAGS="v1.2.3\nv2.0.0\nv2.1.0-rc.1",
        REGISTRY="ghcr.io",
        IMAGE_NAME="owner/project",
        DIGEST="sha256:" + "a" * 64,
    )
    assert result.returncode == 0, result.stderr
    assert Path(sandbox[3]["COMMAND_LOG"]).exists() == promoted


@pytest.mark.parametrize(
    ("tag", "prerelease", "draft", "latest"),
    [
        ("v1.2.3", "false", "false", "false"),
        ("v2.0.0", "false", "false", "true"),
        ("v2.1.0-rc.1", "true", "false", "false"),
        ("v2.0.0", "false", "true", "false"),
    ],
)
def test_github_latest_eligibility(sandbox, tag, prerelease, draft, latest):
    mock_tags(sandbox)
    (sandbox[0] / "RELEASE_NOTES.md").write_text("Release notes")
    result = run(
        sandbox,
        "github-release",
        "Determine latest release eligibility",
        RELEASE_TAG=tag,
        PRERELEASE=prerelease,
        DRAFT=draft,
        GIT_TAGS="v1.2.3\nv2.0.0\nv2.1.0-rc.1",
    )
    assert result.returncode == 0, result.stderr
    assert Path(sandbox[3]["GITHUB_OUTPUT"]).read_text() == f"eligible={latest}\n"


def test_homebrew_rejects_archive_path_traversal(sandbox):
    directory = sandbox[1] / "binaries-linux-amd64"
    directory.mkdir()
    with tarfile.open(directory / "binaries-linux-amd64.tar.gz", "w:gz") as archive:
        info = tarfile.TarInfo("../../escape")
        info.size = 4
        archive.addfile(info, io.BytesIO(b"evil"))
    result = run(sandbox, "homebrew-update", "Prepare formula and release archives")
    assert result.returncode != 0
    assert "outside the destination" in result.stderr
    assert not (sandbox[0] / "escape").exists()
    assert "upload" not in Path(sandbox[3]["COMMAND_LOG"]).read_text()


@pytest.mark.parametrize(
    ("current", "new", "expected_status", "writes"),
    [
        ("version '2.0.0'", "version '1.0.0'", 1, False),
        ("version '1.0.0'", "version '1.0.0'", 0, False),
        ("version '1.0.0'", "version '2.0.0'", 0, True),
    ],
)
def test_homebrew_tap_update_is_monotonic_and_conditional(
    sandbox, current, new, expected_status, writes
):
    (sandbox[0] / "formula.rb").write_text(new)
    result = run(
        sandbox,
        "homebrew-update",
        "Update formula in tap",
        CURRENT_FORMULA=current,
        TAP_REPO="owner/tap",
    )
    assert result.returncode == expected_status, result.stderr
    calls = Path(sandbox[3]["COMMAND_LOG"]).read_text()
    assert ("PUT" in calls) == writes
    if writes:
        assert json.loads(result.stdout)["sha"] == "abc123"


def test_homebrew_same_version_rerun_reuses_immutable_assets(sandbox):
    artifact(sandbox[1], "linux-amd64")
    assets = sandbox[0].parent / "published-assets"
    assets.mkdir()
    first = run(
        sandbox,
        "homebrew-update",
        "Prepare formula and release archives",
        RELEASE_ASSETS=str(assets),
    )
    assert first.returncode == 0, first.stderr
    original = (assets / "sample-1.2.3-linux-amd64.tar.gz").read_bytes()
    formula = (sandbox[0] / "formula.rb").read_bytes()
    shutil.rmtree(sandbox[0] / "artifacts")
    Path(sandbox[3]["COMMAND_LOG"]).write_text("")
    second = run(
        sandbox,
        "homebrew-update",
        "Prepare formula and release archives",
        RELEASE_ASSETS=str(assets),
    )
    assert second.returncode == 0, second.stderr
    assert (assets / "sample-1.2.3-linux-amd64.tar.gz").read_bytes() == original
    assert (sandbox[0] / "formula.rb").read_bytes() == formula
    assert "upload" not in Path(sandbox[3]["COMMAND_LOG"]).read_text()


def test_homebrew_changed_same_version_fails_without_mutating_assets(sandbox):
    artifact(sandbox[1], "linux-amd64")
    assets = sandbox[0].parent / "published-assets"
    assets.mkdir()
    existing = assets / "sample-1.2.3-linux-amd64.tar.gz"
    existing.write_bytes(b"previously published immutable archive")
    result = run(
        sandbox,
        "homebrew-update",
        "Prepare formula and release archives",
        RELEASE_ASSETS=str(assets),
    )
    assert result.returncode != 0
    assert "Existing release asset differs" in result.stderr
    assert existing.read_bytes() == b"previously published immutable archive"
    assert "upload" not in Path(sandbox[3]["COMMAND_LOG"]).read_text()


@pytest.mark.parametrize(
    ("workflow", "prepare", "mutation", "group"),
    [
        ("github-release", "prepare", "publish", "shared-github-release-pointer"),
        ("docker-publish", "publish", "promote", "shared-docker-latest-${{ inputs.image-name }}"),
    ],
)
def test_latest_resource_lock_encloses_recheck_and_mutation(workflow, prepare, mutation, group):
    config = yaml.safe_load((ROOT / ".github/workflows" / f"{workflow}.yml").read_text())
    assert "concurrency" not in config
    assert "concurrency" not in config["jobs"][prepare]
    job = config["jobs"][mutation]
    assert job["needs"] == prepare
    assert job["concurrency"] == {"group": group, "cancel-in-progress": False, "queue": "max"}
    if workflow == "github-release":
        names = [step.get("name") for step in job["steps"]]
        assert names.index("Determine latest release eligibility") < names.index(
            "Create GitHub Release"
        )
    else:
        promotion = next(
            step for step in job["steps"] if step.get("name") == "Promote newest stable image"
        )
        assert promotion["run"].index("git fetch") < promotion["run"].index("imagetools create")
