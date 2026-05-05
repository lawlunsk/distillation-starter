# Distillation Starter

An opinionated starter kit for turning Markdown highlight exports into durable Obsidian notes with the help of an AI agent.

The core idea is simple: do not summarize highlights mechanically. Distill them into reusable concepts, frameworks, procedures, and maps. Before creating a new note, look for an existing note that can be enriched.

## What This Is

Distillation Starter gives you:

- an agent workflow in `skill/SKILL.md`
- reference rules for classification, templates, indexes, and linting
- Python helper scripts for candidate search, archiving, logging, index maintenance, and local linting
- a small fictitious Obsidian vault fixture for testing
- a configuration file so you can adapt paths to your own vault

It is a starter kit, not a universal knowledge-management product. You should adapt the note types, templates, and folder names to match how you think.

## Requirements

- Python 3.10+
- Obsidian notes in Markdown
- Highlight exports saved into an inbox folder in your vault
- Optional: the Obsidian Smart Connections plugin if you want semantic candidate search
- Optional: `numpy` for semantic search and semantic linting

If `numpy` or Smart Connections data is missing, the scripts return structured warnings instead of failing hard.

## Setup

```bash
git clone https://github.com/lawlunsk/distillation-starter Distillation-starter
cd Distillation-starter
cp config.example.yml config.yml
```

Edit `config.yml` so `vault_root` points to your vault and the folders match your structure.

Example:

```yaml
vault_root: /path/to/Obsidian/Vault
inbox_dir: Inbox
knowledge_dir: Knowledge
archive_dir: Archives/Inbox
log_path: System/distillation-log.md
indexes_dir: System/Indexes
```

## Agent Workflow

Give the agent `skill/SKILL.md` as its operating instructions. A typical request looks like:

```text
Distill Inbox/My article.md using this starter kit.
```

The workflow asks the agent to:

1. read the source highlight file
2. search for existing candidate notes
3. classify the material before writing
4. ask for confirmation
5. create or enrich notes
6. update links and indexes
7. archive processed sources
8. append a session log

## Script Usage

All scripts accept `--config config.yml`.

```bash
python3 scripts/find_candidates.py "Inbox/example.md" --config config.yml
python3 scripts/archive_source.py "Inbox/example.md" --config config.yml
python3 scripts/append_log.py examples/log-entries/sample-entry.md --config config.yml
python3 scripts/update_indexes.py "Knowledge/Concepts/Useful friction.md" --action create --config config.yml
python3 scripts/lint_scope.py "Knowledge/Concepts/Useful friction.md" --config config.yml
```

Config precedence:

1. explicit `--config`
2. `DISTILLATION_CONFIG`
3. `config.yml` in the current directory
4. built-in defaults

`config.example.yml` is documentation. Scripts never mutate it silently.

## Try the Fixture

The default config points to `examples/vault-fixture`, so you can run:

```bash
python3 scripts/find_candidates.py "Inbox/Designing useful friction.md" --config config.example.yml
python3 scripts/lint_scope.py "Knowledge/Concepts/Useful friction.md" --config config.example.yml
```

The fixture intentionally has no Smart Connections data, so candidate search reports a clear warning. This is expected.

To test the semantic path with tiny fixture vectors:

```bash
python3 scripts/find_candidates.py "Inbox/Designing useful friction.md" --config examples/config.smart-fixture.yml
```

## Public Safety

Before publishing a fork, run:

```bash
python3 scripts/find_candidates.py --help
python3 scripts/archive_source.py --help
python3 scripts/append_log.py --help
python3 scripts/update_indexes.py --help
python3 scripts/lint_scope.py --help
```

Then search for private strings, absolute local paths, real highlight filenames, and copied personal logs.

## License

MIT.
