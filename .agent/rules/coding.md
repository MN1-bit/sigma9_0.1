# Sigma9 Coding Rules

## File Limits
- Max lines: **500** (exceptions: seismograph.py, dashboard.py)
- Max class methods: **30**

## Forbidden Patterns
- `_instance` global variables
- `get_*_instance()` functions
- Global singletons

## Required
- **DI**: New services -> register in `Container`
- **Type Hints**: All functions
- **Comments**: ELI5 level (Korean)
- **Docstrings**: Google style

## Quality Gates
```bash
ruff format && ruff check .  # Format + Lint
mypy backend frontend        # Type check
lint-imports                 # Boundary check
```

## Reference
- `@PROJECT_DNA.md` -- Project DNA
- `docs/Plan/refactor/REFACTORING.md` -- Detailed rules (Sections 4-6)
