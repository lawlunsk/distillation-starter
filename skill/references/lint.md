# Lint

The local lint is a lightweight health check for notes touched by one distillation session.

It checks:

- notes with no backlinks
- missing parent map
- missing concept limits
- possible capture debts
- optional semantic neighbors that are not linked

Run:

```bash
python3 scripts/lint_scope.py "<note>" --config config.yml
```

Warnings are suggestions, not automatic obligations.

If Smart Connections vectors or `numpy` are missing, semantic cross-reference checks are skipped and the script reports a warning.

