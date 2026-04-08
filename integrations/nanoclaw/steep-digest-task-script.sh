#!/usr/bin/env bash
# NanoClaw scheduled-task `script` body (paste into DB or use register_steep_digest_task.py).
# Requires main group `containerConfig.additionalMounts` to mount the steep repo at
# container path `steep` → appears as /workspace/extra/steep
# and nanoclaw-agent-steep image (integrations/container/Dockerfile.steep-agent).

set -euo pipefail

export STEEP_REPO_ROOT="/workspace/extra/steep"
export PYTHONPATH="${STEEP_REPO_ROOT}/src"

python3 -m steep_digest run

# Skip the LLM for this task — the digest already ran above.
echo '{"wakeAgent": false}'
