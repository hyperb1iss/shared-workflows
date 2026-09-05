"""Validate concurrency queues and retain actionlint's original source diagnostics."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode

# GitHub defines queue independently of cancellation, while actionlint's schema
# recognizes only group and cancel-in-progress. Validate the missing field here.
# https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency
QUEUE_DIAGNOSTIC = (
    '^unexpected key "queue" for "concurrency" section\\. '
    'expected one of "cancel-in-progress", "group"$'
)


def members(node: Node, name: str) -> list[Node]:
    """Return every matching value, preserving duplicate keys for validation."""
    if not isinstance(node, MappingNode):
        return []
    return [value for key, value in node.value if isinstance(key, ScalarNode) and key.value == name]


def queue_errors(path: Path) -> list[str]:
    """Check literal queue values at workflow and job concurrency locations."""
    try:
        root = yaml.compose(path.read_text(), Loader=yaml.SafeLoader)
    except (OSError, yaml.YAMLError) as error:
        return [f"{path}: {error}"]
    if root is None:
        return []  # actionlint diagnoses empty workflows.

    concurrency = members(root, "concurrency")
    for jobs in members(root, "jobs"):
        if isinstance(jobs, MappingNode):
            for _, job in jobs.value:
                concurrency.extend(members(job, "concurrency"))

    errors: list[str] = []

    def report(node: Node, message: str) -> None:
        mark = node.start_mark
        errors.append(f"{path}:{mark.line + 1}:{mark.column + 1}: {message} [queue-check]")

    for section in concurrency:
        queues = members(section, "queue")
        if len(queues) > 1:
            report(queues[1], "duplicate concurrency queue key")
        for queue in queues:
            if (
                not isinstance(queue, ScalarNode)
                or queue.tag != "tag:yaml.org,2002:str"
                or queue.value not in {"single", "max"}
            ):
                report(queue, "concurrency queue must be the literal string 'single' or 'max'")
                continue
            if queue.value == "max":
                cancellations = members(section, "cancel-in-progress")
                if len(cancellations) != 1 or not (
                    isinstance(cancellations[0], ScalarNode)
                    and cancellations[0].tag == "tag:yaml.org,2002:bool"
                    and cancellations[0].value.lower() == "false"
                ):
                    report(queue, "queue: max requires an explicit cancel-in-progress: false")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actionlint", default="actionlint", help="actionlint executable path")
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    paths = args.paths or sorted(Path(".github/workflows").glob("*.yml"))
    if not paths:
        parser.error("no workflow files found")
    errors = [error for path in paths for error in queue_errors(path)]
    for error in errors:
        print(error, file=sys.stderr)
    # Pass original paths so every remaining error retains its exact source anchor.
    try:
        result = subprocess.run(
            [args.actionlint, "-ignore", QUEUE_DIAGNOSTIC, *map(str, paths)], check=False
        )
    except OSError as error:
        print(f"Cannot run actionlint: {error}", file=sys.stderr)
        return 1
    return result.returncode or bool(errors)


if __name__ == "__main__":
    sys.exit(main())
