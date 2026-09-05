#!/usr/bin/env bash
set -euo pipefail

: "${MAJOR_TAG:?MAJOR_TAG must name the release line}"
: "${GITHUB_SHA:?GITHUB_SHA must identify the validated commit}"
if [[ ! "$MAJOR_TAG" =~ ^v[1-9][0-9]*$ ]]; then
  echo "::error::Invalid major tag: $MAJOR_TAG"
  exit 1
fi

target_sha=$(git rev-parse HEAD)
if [ "$target_sha" != "$GITHUB_SHA" ]; then
  echo "::error::Checkout does not match the validated commit"
  exit 1
fi

git fetch origin refs/heads/main:refs/remotes/origin/main
if [ "$target_sha" != "$(git rev-parse refs/remotes/origin/main)" ]; then
  echo "::notice::Main has advanced; leave promotion to its own CI run"
  exit 0
fi

tag_ref="refs/tags/$MAJOR_TAG"
remote_tag=$(git ls-remote --refs origin "$tag_ref")
expected_oid="${remote_tag%%[[:space:]]*}"
if [ -n "$expected_oid" ]; then
  git fetch origin "+$tag_ref:$tag_ref"
  current_sha=$(git rev-parse "$tag_ref^{commit}")
  if [ "$current_sha" = "$target_sha" ]; then
    echo "$MAJOR_TAG already points to the validated commit"
    exit 0
  fi
  if ! git merge-base --is-ancestor "$current_sha" "$target_sha"; then
    echo "::error::Refusing to move $MAJOR_TAG backward or across histories"
    exit 1
  fi
fi

# The lease also protects first publication (an empty expected object).
git push --force-with-lease="$tag_ref:$expected_oid" origin "$target_sha:$tag_ref"
if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  printf 'Promoted %s to validated commit %s.\n' "$MAJOR_TAG" "$target_sha" >> "$GITHUB_STEP_SUMMARY"
fi
