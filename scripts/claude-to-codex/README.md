# claude-to-codex

Generates Codex configuration from this repo's Claude Code configuration, so a
Codex agent works here without anyone redefining the same instructions twice.

Reads `CLAUDE.md` (root and nested) and `.claude/`; writes `AGENTS.md` and
`.agents/`. **It only writes.** The Claude side stays the source of truth and is
never modified.

```bash
(cd scripts/claude-to-codex && go run .)            # write it
(cd scripts/claude-to-codex && go run . --dry-run)  # show the plan
(cd scripts/claude-to-codex && go run . --prune)    # drop generated files whose source is gone
```

`--root` defaults to the nearest ancestor holding `CLAUDE.md` or `.claude/`, so
it works from anywhere in the checkout.

## Layout

Its own Go module, with no dependencies — stdlib only, so it builds offline.

| File | Holds |
| --- | --- |
| `main.go` | Flags, root resolution, orchestration, the report |
| `frontmatter.go` | A minimal ordered YAML frontmatter reader and writer |
| `writer.go` | Every write, the manifest, and `--prune` |
| `convert.go` | The five converters and their lossiness notes |

## Why a manifest

`.agents/.claude-sync.json` records the SHA-256 of everything generated. A file
not in it is never overwritten (`--force` overrides), `--prune` deletes only
files whose content still matches, and re-runs are idempotent.

Managed blocks in `AGENTS.md` are matched by source file, not by generator name,
so renaming this tool cannot orphan a block and append a duplicate beside it.
