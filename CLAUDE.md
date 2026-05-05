# Distillation Starter — Claude Code Context

This repo is a starter kit for distilling Markdown highlight exports into durable Obsidian knowledge notes. The agent workflow lives in `skill/SKILL.md`. The Python scripts are helpers; the agent orchestrates them.

## First-time setup

`config.yml` is gitignored. If it does not exist, create it from the template:

```bash
cp config.example.yml config.yml
```

Then edit `config.yml` to set `vault_root` to the user's Obsidian vault path. All other paths are relative to `vault_root`.

If `config.yml` is missing and the user asks to distill something, ask them to create it before proceeding.

## How to run a distillation

Load `skill/SKILL.md` as your operating instructions. The workflow has four phases: Analyze → Write/Enrich → Link/Index → Lint/Archive/Log.

Always read the config before assuming folder names. Do not hardcode `Inbox/`, `Knowledge/`, or any other path — they come from `config.yml`.

## Scripts

All scripts are in `scripts/` and accept `--config config.yml`. Run them with `python3`.

| Script | Purpose |
|---|---|
| `find_candidates.py <source>` | Semantic search for existing notes similar to a source |
| `archive_source.py <source>` | Move a processed source to the archive folder |
| `append_log.py <entry-file>` | Append a session entry to the distillation log |
| `update_indexes.py <note> --action create\|enrich` | Register or update a note in the indexes |
| `lint_scope.py <note...>` | Lightweight health check on notes touched in a session |
| `download_images.py <source>` | Localize external images from a source file |

`config_loader.py` is a shared library, not a standalone script.

## Testing with the fixture

`config.example.yml` points to `examples/vault-fixture`. Use it to run scripts without touching a real vault:

```bash
python3 scripts/find_candidates.py "Inbox/Designing useful friction.md" --config config.example.yml
python3 scripts/lint_scope.py "Knowledge/Concepts/Useful friction.md" --config config.example.yml
```

For semantic search with tiny fixture vectors:

```bash
python3 scripts/find_candidates.py "Inbox/Designing useful friction.md" --config examples/config.smart-fixture.yml
```

## Key constraints

- **Never archive outside `inbox_dir`.** `archive_source.py` enforces this and returns an error if violated.
- **Ask before writing.** Phase A always ends with a confirmation table. Do not proceed to Phase B without user approval.
- **Enrich before creating.** A new note is only justified when no existing note can absorb the idea.
- **`config.yml` must never be committed.** It contains absolute local paths.

## Reference files

- `skill/references/classification.md` — when to use CONCEPT vs FRAMEWORK vs HOWTO vs MAP etc.
- `skill/references/templates.md` — frontmatter and section structure for each note type
- `skill/references/indexes.md` — index entry format and grade definitions
- `skill/references/lint.md` — what the lint script checks and how to interpret warnings
