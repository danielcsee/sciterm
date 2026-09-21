# scripts

Developer tooling.

## `dev.sh`

Launches the whole local stack — Postgres and Redis in Docker, the FastAPI
server and the React dev server on the host.

```bash
./scripts/dev.sh           # hot-reloading dev servers (UI on :5173)
./scripts/dev.sh --prod    # build the bundle and serve it from FastAPI (:8000)
./scripts/dev.sh --no-db   # skip Docker; app processes only
./scripts/dev.sh --force   # start anyway, even if a copy is already running
```

**It refuses to become a second copy.** It asks `stop.sh --list` whether this
checkout is already running and stops if so. Duplicates do not announce
themselves: two uvicorns share `:8000` with the kernel quietly preferring the
older one, and two Celery workers turn every shared entity into a deadlock
candidate. Both look like application bugs.

It is idempotent and safe to re-run. In order it will:

1. create `.env` from `.env.example` if missing, then source it
2. `docker compose up -d postgres redis-celery-broker redis-cache` and wait on
   their healthchecks
3. create `.venv` if missing and install `api/requirements.txt`
4. apply Alembic migrations (`alembic upgrade head`)
5. `npm install` in `ui/` if `node_modules` is missing
6. start uvicorn, and Vite unless `--prod`

It exports `SCITERM_ENV=local`, so a `.env` copied down from a prod host cannot
quietly put the access-code gate in front of local development.

Ctrl-C stops the app processes. **The datastores keep running** — stop them
with `docker compose down`.

## `admin.sh`

Calls the admin endpoints, authenticating with your SSH key. No shared secret
is involved: the server holds only the public keys committed in
[`api/authorized_keys/`](../api/authorized_keys), and this script asks for a
nonce, signs it with `ssh-keygen -Y sign`, and sends the signature.

```bash
./scripts/admin.sh codes 5                     # mint 5 free access codes
./scripts/admin.sh rotate-admin                # generate a new admin password
./scripts/admin.sh rotate-admin --ask          # choose the password yourself
./scripts/admin.sh codes 5 https://your.host   # against a deployment
```

Signing goes through `ssh-keygen`, so ssh-agent and passphrase-protected keys
work; nothing here ever reads your private key. `SCITERM_ADMIN_KEY` overrides
the default `~/.ssh/id_ed25519`.

`rotate-admin` **always** changes the password — that is what an authenticated
call means — and prints it once. It also revokes every live admin session, so
the old credential cannot outlive itself. The password is then usable in the
app's own sign-in modal.

To authorise another machine, drop its `.pub` into `api/authorized_keys/` and
commit. To revoke one, delete the file and redeploy.

## `stop.sh`

Stops everything `dev.sh` starts — the host processes and this project's
containers.

```bash
./scripts/stop.sh              # app processes and datastores
./scripts/stop.sh --apps-only  # leave Postgres/Redis running
./scripts/stop.sh --dry-run    # list what would be stopped
```

It finds processes by *what they are* — uvicorn, Celery, Vite whose command line
or working directory is this checkout — not by who started them, so a server
launched by hand outside `dev.sh` is stopped too. That case is not hypothetical:
two uvicorns can hold `:8000` at once, one bound to `127.0.0.1` and one to
`0.0.0.0`, and the kernel prefers the specific bind, so the stale one keeps
serving `localhost` while a restart appears to have worked.

Afterwards it re-checks the API port and kills anything of ours still holding
it, which catches uvicorn's `--reload` child — its command line names neither
uvicorn nor the app, so no pattern matches it directly.

## `cleanup.sh`

```bash
./scripts/cleanup.sh            # this project's containers and orphans
./scripts/cleanup.sh --full     # everything; see below
./scripts/cleanup.sh --dry-run  # print the plan, change nothing
```

Default is scoped to this project and **keeps volumes**, so imported papers
survive.

`--full` removes **every container on this Docker host**, including other
Compose projects', then drops this project's volumes and images and deletes
`.venv/`, `ui/node_modules/` and `ui/dist/`. Volumes and images stay scoped to
this project — rebuilding this project should not delete another one's database.
It prints the foreign containers by name and requires you to type the project
name to continue; `--yes` skips that for scripted use.

## `aiutils.sh`

Runs [aiutils](https://github.com/danielcsee/aiutils) — the function-level test
inventory and runner, and the Codex config generator. Every argument is
forwarded:

```bash
./scripts/aiutils.sh check              # what needs tests?
./scripts/aiutils.sh test               # run them
./scripts/aiutils.sh claude-to-codex    # regenerate AGENTS.md and .agents/
```

**It always runs the latest release.** On every invocation it asks GitHub for
the newest tag and downloads it only when the cached binary is a different
version, so staying current costs one API call rather than an 8 MB download per
command. The cache lives in `.aiutils/bin/` and keeps exactly one version;
older ones are deleted.

The repository is private, so downloads go through `gh`, which already holds
your credentials — `gh auth login` once and the script needs nothing else.

Set `AIUTILS_BIN` to run a local build instead, which is what you want when
working on aiutils itself:

```bash
AIUTILS_BIN=~/coding/aiutils/bin/aiutils ./scripts/aiutils.sh check
```

Configuration is `aiutils.json` in the project root; the ledger database and
artifacts live in `.aiutils/`.

## Codex configuration

Generated from the Claude Code configuration by the `claude-to-codex` command
in [aiutils](https://github.com/danielcsee/aiutils), the same binary
`aiutils.sh` above already fetches — so there is nothing extra to install:

```bash
./scripts/aiutils.sh claude-to-codex --dry-run   # show the plan
./scripts/aiutils.sh claude-to-codex             # write it
./scripts/aiutils.sh claude-to-codex --prune     # drop generated files whose source is gone
```

`CLAUDE.md` becomes `AGENTS.md` and `.claude/skills/` becomes `.agents/skills/`,
which Codex discovers automatically in any session started in this repo. It also
converts `.claude/agents/`, `.claude/commands/` and `.mcp.json` when they exist.

**It only writes; it never touches the Claude side.** Claude remains the source
of truth, so edit `CLAUDE.md` or `.claude/` and re-run — do not edit the
generated files. `.agents/.claude-sync.json` records what was generated, so
re-runs are idempotent and anything you wrote yourself is left alone
(`--force` overrides).

Things with no faithful Codex equivalent — tool permissions, hooks, per-skill
model pins — are reported rather than guessed at.

Verify what Codex actually loaded:

```bash
codex debug prompt-input | grep -i skill
```

## Ports

Read from `.env`, with defaults: API `8000`, UI `5173`, Postgres `5432`, Redis
broker `6379`, and Redis document cache `6380`.

## Dependencies

`bash`, `docker` (unless `--no-db`), `python3`, and `npm` — checked at startup
with a clear error rather than a stack trace.
