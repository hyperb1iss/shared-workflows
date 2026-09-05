"""Exercise the inline release scripts against disposable repositories."""

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def step(workflow, name):
    data = yaml.safe_load((ROOT / ".github/workflows" / workflow).read_text())
    return next(
        step
        for job in data["jobs"].values()
        for step in job.get("steps", [])
        if step.get("name") == name
    )


def run_inline(name, cwd, **env):
    script = step("rust-release.yml", name)["run"]
    code = script.split("<<'PYTHON'\n", 1)[1].rsplit("\nPYTHON", 1)[0]
    output = cwd / "output"
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=cwd,
        env={**os.environ, "GITHUB_OUTPUT": str(output), **env},
        capture_output=True,
        text=True,
    )
    values = (
        dict(line.split("=", 1) for line in output.read_text().splitlines())
        if output.exists()
        else {}
    )
    return result, values


def git(cwd, *args):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


@pytest.fixture
def crate(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src/lib.rs").write_text("pub fn value() -> u8 { 1 }\n")
    (tmp_path / "Cargo.toml").write_text(
        '[package]\nname="fixture"\nversion="1.2.3"\nedition="2021"\n'
    )
    return tmp_path


def patch(cwd, **extra):
    return run_inline(
        "Patch release versions",
        cwd,
        NEW_VERSION="1.3.0",
        WORKSPACE_CRATES=extra.pop("WORKSPACE_CRATES", ""),
        PATCH_DEPENDENCIES=extra.pop("PATCH_DEPENDENCIES", "false"),
        VERSION_FILES=extra.pop("VERSION_FILES", ""),
        **extra,
    )


def test_compact_manifest_version_is_patched(crate):
    result, output = patch(crate)
    assert result.returncode == 0, result.stderr
    assert tomllib.loads((crate / "Cargo.toml").read_text())["package"]["version"] == "1.3.0"
    assert json.loads(output["files"]) == ["Cargo.toml"]


def test_workspace_names_and_inheritance(tmp_path):
    (tmp_path / "Cargo.toml").write_text("""[workspace]
members = ["crates/core", "crates/cli"]
resolver = "2"
[workspace.package]
version="1.2.3"
[workspace.dependencies]
core = { package="fixture-core", path="crates/core", version="1.2.3" }
""")
    for name in ["core", "cli"]:
        path = tmp_path / "crates" / name
        (path / "src").mkdir(parents=True)
        (path / "src/lib.rs").write_text("")
        (path / "Cargo.toml").write_text(
            f'[package]\nname="fixture-{name}"\nversion.workspace=true\nedition="2021"\n'
        )
    result, _ = patch(
        tmp_path, WORKSPACE_CRATES="fixture-core crates/cli", PATCH_DEPENDENCIES="true"
    )
    assert result.returncode == 0, result.stderr
    data = tomllib.loads((tmp_path / "Cargo.toml").read_text())
    assert data["workspace"]["package"]["version"] == "1.3.0"
    assert data["workspace"]["dependencies"]["core"]["version"] == "1.3.0"
    assert (
        tomllib.loads((tmp_path / "crates/core/Cargo.toml").read_text())["package"]["version"][
            "workspace"
        ]
        is True
    )


@pytest.mark.parametrize(
    "extra",
    [
        {"WORKSPACE_CRATES": "missing"},
        {"VERSION_FILES": "missing.json"},
        {"VERSION_FILES": "package.json|.broken["},
        {"VERSION_FILES": "package.json|.missing"},
        {"VERSION_FILES": "readme.md"},
    ],
)
def test_invalid_requested_updates_fail(crate, extra):
    (crate / "package.json").write_text('{"version":"1.2.3"}')
    (crate / "readme.md").write_text("# Example\nversion: 1.2.3\n")
    result, _ = patch(crate, **extra)
    assert result.returncode != 0


def test_json_quotes_and_markdown_frontmatter(crate):
    (crate / "package.json").write_text('{"a-b":{"version":"1.2.3"}}')
    (crate / "notes.md").write_text("---\nversion: 1.2.3\n---\nversion: leave-me\n")
    result, output = patch(crate, VERSION_FILES=' package.json | .["a-b"].version\nnotes.md')
    assert result.returncode == 0, result.stderr
    assert json.loads((crate / "package.json").read_text())["a-b"]["version"] == "1.3.0"
    assert (crate / "notes.md").read_text() == '---\nversion: "1.3.0"\n---\nversion: leave-me\n'
    assert set(json.loads(output["files"])) == {"Cargo.toml", "package.json", "notes.md"}


def test_release_version_and_resume(crate):
    git(crate, "init", "-b", "main")
    git(crate, "add", ".")
    git(
        crate,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "initial",
    )
    git(crate, "tag", "v1.2.3")
    env = {"VERSION_INPUT": "", "BUMP": "patch", "RESUME_RELEASE": "false", "REF_TYPE": "branch"}
    result, output = run_inline("Determine version", crate, **env)
    assert result.returncode == 0, result.stderr
    assert output["new"] == "1.2.4"
    assert output["from"] == "v1.2.3"
    result, _ = run_inline("Determine version", crate, **{**env, "VERSION_INPUT": "1.2.3"})
    assert result.returncode != 0
    result, output = run_inline(
        "Determine version", crate, **{**env, "VERSION_INPUT": "1.2.3", "RESUME_RELEASE": "true"}
    )
    assert result.returncode == 0, result.stderr
    assert output["new"] == "1.2.3"


@pytest.mark.parametrize("version", ["01.2.3", "1.0.0", "1.2.3\nnew=9.0.0"])
def test_invalid_or_regressive_version_rejected(crate, version):
    git(crate, "init", "-b", "main")
    git(crate, "add", ".")
    git(
        crate,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "initial",
    )
    result, _ = run_inline(
        "Determine version",
        crate,
        VERSION_INPUT=version,
        BUMP="patch",
        RESUME_RELEASE="false",
        REF_TYPE="branch",
    )
    assert result.returncode != 0


def test_target_selection_rejects_partial_typos(tmp_path):
    script = step("rust-build-artifacts.yml", "Select build targets")["run"]
    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", script],
        cwd=tmp_path,
        env={**os.environ, "TARGETS": "linux-amd64 typo", "GITHUB_OUTPUT": str(tmp_path / "out")},
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "Unknown build target: typo" in result.stdout


def test_archive_preserves_executable_mode(tmp_path):
    staging = tmp_path / "staging"
    staging.mkdir()
    binary = staging / "demo"
    binary.write_text("#!/bin/sh\nexit 0\n")
    binary.chmod(0o755)
    script = step("rust-build-artifacts.yml", "Archive binaries")["run"]
    subprocess.run(
        ["bash", "-e", "-c", script],
        cwd=tmp_path,
        env={**os.environ, "BUILD_TARGET": "linux-amd64"},
        check=True,
    )
    import tarfile

    with tarfile.open(tmp_path / "binaries-linux-amd64.tar.gz") as archive:
        assert archive.getmember("./demo").mode == 0o755


def test_lockfile_refresh_preserves_unrelated_package(crate):
    other = crate / "other"
    (other / "src").mkdir(parents=True)
    (other / "src/lib.rs").write_text("")
    (other / "Cargo.toml").write_text('[package]\nname="other"\nversion="7.8.9"\nedition="2021"\n')
    with (crate / "Cargo.toml").open("a") as manifest:
        manifest.write('[dependencies]\nother={path="other", version="7"}\n')
    subprocess.run(
        ["cargo", "metadata", "--offline", "--format-version", "1"],
        cwd=crate,
        stdout=subprocess.DEVNULL,
        check=True,
    )
    result, _ = patch(crate)
    assert result.returncode == 0, result.stderr
    script = step("rust-release.yml", "Update lockfile")["run"]
    subprocess.run(["bash", "-e", "-c", script], cwd=crate, check=True)
    packages = {
        package["name"]: package["version"]
        for package in tomllib.loads((crate / "Cargo.lock").read_text())["package"]
    }
    assert packages == {"fixture": "1.3.0", "other": "7.8.9"}


def test_custom_profile_stages_from_selected_directory(tmp_path):
    binary_dir = tmp_path / "target" / "example-target" / "dist"
    binary_dir.mkdir(parents=True)
    (binary_dir / "demo").write_text("binary")
    script = step("rust-build-artifacts.yml", "Stage binaries")["run"]
    subprocess.run(
        ["bash", "-e", "-c", script],
        cwd=tmp_path,
        env={
            **os.environ,
            "CARGO_PROFILE": "dist",
            "BINARIES": "demo",
            "RUST_TARGET": "example-target",
            "SUFFIX": "",
        },
        check=True,
    )
    assert (tmp_path / "staging/demo").read_text() == "binary"


def test_release_prepares_content_before_atomic_push():
    workflow = yaml.safe_load((ROOT / ".github/workflows/rust-release.yml").read_text())
    names = [step.get("name", "") for step in workflow["jobs"]["release"]["steps"]]
    assert names.index("Generate release notes") < names.index("Create and push tag")
    assert names.index("Generate changelog") < names.index("Commit version bump")
    assert "git push --atomic" in step("rust-release.yml", "Create and push tag")["run"]
    assert "!inputs.resume-release" in step("rust-release.yml", "Create and push tag")["if"]


def test_release_doctest_failure_blocks_validation(crate):
    (crate / "src/lib.rs").write_text(
        "/// ```\n/// assert_eq!(1, 2);\n/// ```\npub fn example() {}\n"
    )
    subprocess.run(["cargo", "generate-lockfile", "--offline"], cwd=crate, check=True)
    script = step("rust-release.yml", "Run doc tests")["run"]
    result = subprocess.run(
        ["bash", "-e", "-c", script],
        cwd=crate,
        env={**os.environ, "CARGO_WORKSPACE": "false", "CARGO_ALL_FEATURES": "true"},
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "test result: FAILED" in result.stdout


def test_rust_scripts_never_interpolate_inputs():
    for filename in ROOT.glob(".github/workflows/rust-*.yml"):
        workflow = yaml.safe_load(filename.read_text())
        for job in workflow["jobs"].values():
            for item in job.get("steps", []):
                assert "${{" not in item.get("run", ""), (filename, item.get("name"))


@pytest.mark.parametrize("profile", ["test", "bench"])
def test_builtin_profiles_build_and_stage(crate, profile):
    (crate / "src/main.rs").write_text('fn main() { println!("fixture"); }\n')
    subprocess.run(["cargo", "generate-lockfile", "--offline"], cwd=crate, check=True)
    target = next(
        line.split(": ", 1)[1]
        for line in subprocess.check_output(["rustc", "-vV"], text=True).splitlines()
        if line.startswith("host: ")
    )
    env = {
        **os.environ,
        "CARGO_PROFILE": profile,
        "BUILD_ARGS": "--locked --offline",
        "RUST_TARGET": target,
        "BINARIES": "fixture",
        "SUFFIX": "",
    }
    for name in ["Build", "Stage binaries"]:
        subprocess.run(
            ["bash", "-e", "-c", step("rust-build-artifacts.yml", name)["run"]],
            cwd=crate,
            env=env,
            check=True,
        )
    staged = crate / "staging/fixture"
    assert staged.is_file()
    assert os.access(staged, os.X_OK)


@pytest.mark.parametrize("dry_run", ["true", "false"])
def test_resume_summary_reports_only_executed_operations(tmp_path, dry_run):
    output = tmp_path / "summary"
    subprocess.run(
        ["bash", "-e", "-c", step("rust-release.yml", "Summary")["run"]],
        cwd=tmp_path,
        env={
            **os.environ,
            "RESUME_RELEASE": "true",
            "DRY_RUN": dry_run,
            "CICD_WORKFLOW": "cicd.yml",
            "CURRENT_VERSION": "1.2.3",
            "NEW_VERSION": "1.2.3",
            "GITHUB_STEP_SUMMARY": str(output),
        },
        check=True,
    )
    summary = output.read_text()
    assert "Build and tests were not rerun." in summary
    assert "tests passed" not in summary
    assert "Version bumped" not in summary
    assert "Tag pushed" not in summary
    if dry_run == "true":
        assert "no release notes generated or downstream workflow dispatched" in summary
        assert "Downstream workflow triggered" not in summary
    else:
        assert "Existing tag reused without modification" in summary
        assert "Downstream workflow triggered: cicd.yml" in summary
