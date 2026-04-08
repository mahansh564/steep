# Steep + NanoClaw (monorepo layout)

This repo vendors **[NanoClaw](https://github.com/qwibitai/nanoclaw)** as a **git submodule** at `nanoclaw/`.

```
steep/                      ← monorepo root (Gmail allowlist, steep-digest Python pkg)
├── nanoclaw/               ← submodule; you run NanoClaw from here
├── config/
├── src/steep_digest/
└── integrations/nanoclaw/  ← wiring docs + task script + register helper
```

## Use your own GitHub fork

Upstream remote is `qwibitai/nanoclaw`. To track **your** fork:

```bash
git submodule set-url nanoclaw https://github.com/YOU/nanoclaw.git
git submodule sync
git -C nanoclaw fetch && git -C nanoclaw checkout main
```

## 1. Agent image with Python

Stock NanoClaw agents are Node-only. Steep’s scheduled task runs **`python3 -m steep_digest`** in the container, so build the extended image:

```bash
cd nanoclaw/container && ./build.sh
cd ../..
docker build -f integrations/container/Dockerfile.steep-agent -t nanoclaw-agent-steep:latest .
```

In `nanoclaw/.env` (or your process manager):

```env
CONTAINER_IMAGE=nanoclaw-agent-steep:latest
TZ=America/Los_Angeles
```

## 2. Mount allowlist (host)

NanoClaw only mounts extra host dirs approved in **`~/.config/nanoclaw/mount-allowlist.json`**.

Copy `integrations/nanoclaw/mount-allowlist.steep.example.json`, set **`path`** to this **monorepo root** (the directory that contains `nanoclaw/` and `config/`).

## 3. Mount the steep repo into **main**’s container

Merge **`integrations/nanoclaw/registered-groups-steep-mount.fragment.json`** into your **main** group entry inside NanoClaw’s `registered_groups` store (usually via the agent editing SQLite / `registered_groups` flow — see NanoClaw docs).

- Replace **`hostPath`** with the same absolute monorepo root as in the allowlist.
- `containerPath` **`steep`** → appears at **`/workspace/extra/steep`**.

## 4. Point `digest.yaml` at NanoClaw’s CLAUDE.md

From the monorepo root, the reader profile can be:

```yaml
reader_claude_md: nanoclaw/groups/main/CLAUDE.md
```

(Already the default in `config/digest.yaml` once you uncomment/set it.)

## 5. Register the scheduled task

After **`nanoclaw/store/messages.db`** exists and **main** is registered:

```bash
python3 integrations/nanoclaw/register_steep_digest_task.py \
  --db nanoclaw/store/messages.db \
  --cron '0 9 * * *' \
  --next-run '2026-04-10T09:00:00+00:00'
```

The inserted **`script`** is `integrations/nanoclaw/steep-digest-task-script.sh`. It runs the digest and prints `{"wakeAgent": false}` so NanoClaw does **not** spawn an extra Claude turn for that schedule.

## 6. Secrets

Keep **`credentials.json`**, **`token.json`**, **`.env`** with `TELEGRAM_*` and optional `ANTHROPIC_*` in the **monorepo root** (already gitignored). The mount is **read/write** so **`state/digest-cursor.json`** persists.

When NanoClaw uses an Anthropic **proxy**, set **`ANTHROPIC_BASE_URL`** in the container environment so `steep-digest` can use the same path as Claude Code (see `llm_digest.py`).

## Run NanoClaw from the submodule

```bash
cd nanoclaw
npm install
# follow NanoClaw README for channels; then:
npm start
```

Always open issues/feature work against **your fork** or upstream `qwibitai/nanoclaw`, not against the submodule pointer here, unless you intentionally pin a patched commit.
