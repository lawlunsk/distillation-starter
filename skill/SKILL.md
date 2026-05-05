---
name: distillation-starter
description: Distill Markdown highlights into durable Obsidian knowledge notes. Use when the user asks to process an inbox folder, distill highlights, enrich a second brain, or route reading notes into concepts, pivots, frameworks, how-tos, maps, or watchlist entries.
---

# Distillation Starter

You help the user transform raw reading highlights into durable notes in their own Obsidian vault. This is not mechanical summarization. Your job is to extract mechanisms, reformulate in the user's voice, connect ideas to the existing note system, and enrich before creating.

## Core Principles

1. **Enrich before creating.** A strengthened existing note is usually better than a shallow new note.
2. **Distill, do not summarize.** A highlight is raw material. A distilled note explains the underlying mechanism.
3. **Ask before writing.** Present routing decisions before changing the vault.
4. **Identify limits.** Concepts without limits, counterexamples, or failure modes are immature.
5. **Link deliberately.** Every created or enriched note should connect to maps, neighboring notes, or capture debts.
6. **Reject weak material.** Not every highlight deserves a permanent note.

## Expected Config

The scripts read `config.yml`. The important fields are:

- `vault_root`
- `inbox_dir`
- `knowledge_dir`
- `archive_dir`
- `log_path`
- `indexes_dir`
- `note_types`
- `smart_connections`

Do not assume folder names. Read the config or ask the user to provide it.

## Invocation Patterns

Common requests:

- `distill Inbox/my-article.md`
- `distill 5 highlights`
- `process this file`
- `lint the notes touched by the last distillation`

If a count is ambiguous, ask for clarification. Never invent a number.

## Phase A - Analyze and Route

Goal: understand the source, decide whether it deserves distillation, and identify candidate target notes.

Steps:

1. Select the source file or batch.
2. Read the full source, including frontmatter and highlights.
3. Detect book mode if the source is long, multi-theme, or tagged as a book.
4. Run candidate search when available:

```bash
python3 scripts/find_candidates.py "Inbox/<source>" --config config.yml
```

5. If semantic search is unavailable, read the configured indexes and nearby folders manually.
6. Classify each meaningful idea as `CONCEPT`, `PIVOT`, `FRAMEWORK`, `HOWTO`, `MAP`, `WATCHLIST`, or `NOISE`.
7. Present a confirmation table before writing:

```markdown
| # | Source idea | Category | Action | Target |
|---|---|---|---|---|
| 1 | Friction can protect attention | CONCEPT | ENRICH | [[Useful friction]] |
| 2 | A three-step review routine | HOWTO | CREATE | [[Run a weekly reading review]] |
```

Wait for confirmation before Phase B.

## Phase B - Write or Enrich

Use `skill/references/templates.md`.

Rules:

- Do not copy long highlight passages.
- Write in the user's own vocabulary and context.
- For concepts, include limits and counterexamples.
- For frameworks, make the structure reusable.
- For how-tos, make steps executable.
- Add the source to the note's references section.
- If an idea is assertive or opinionated, place it under production angles rather than making the whole note a thesis.

## Phase C - Link and Index

Goal: make the note findable and connected.

Actions:

- Add links to parent maps or adjacent notes.
- Add reciprocal links when useful.
- List missing concepts as capture debts rather than creating them automatically.
- Update indexes:

```bash
python3 scripts/update_indexes.py "<note>" --action create --description "<short mechanism>" --config config.yml
python3 scripts/update_indexes.py "<note>" --action enrich --config config.yml
```

## Phase D - Lint, Archive, Log

Run local lint:

```bash
python3 scripts/lint_scope.py "<note1>" "<note2>" --config config.yml
```

Archive processed sources only after writing and linking are complete:

```bash
python3 scripts/archive_source.py "Inbox/<source>" --config config.yml
```

Append a session log:

```bash
python3 scripts/append_log.py "<entry-file>" --config config.yml
```

Final response should summarize created notes, enriched notes, index updates, archived sources, lint warnings, and suggested follow-up links.

## Book Mode

Use book mode when one source contains many highlights across multiple themes.

Do not distill immediately. First propose a map of possible notes:

```markdown
## Distillation Plan - Book Title

1. CONCEPT - [[Useful friction]] - covers highlights 3, 8, 12
2. FRAMEWORK - [[Attention review loop]] - covers highlights 15, 16, 20
3. NOISE - highlights 5, 6 - anecdotes without reusable mechanism

Question: should items 1 and 2 remain separate or become one larger pivot?
```

Wait for selection before writing.

## When in Doubt

Ask for arbitration when two actions remain plausible:

- enrich existing note vs create new note
- concept vs framework
- framework vs how-to
- permanent note vs watchlist
- map or pivot creation

Do not silently default to creating a new concept.

