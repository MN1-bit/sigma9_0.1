# Sigma9 Refactoring Rules

## Mandatory
1. Doc-First: Plan in docs/Plan/refactor/ before code
2. Devlog: Report in docs/devlog/refactor/ per step
3. QA: lint-imports + pydeps --show-cycles required
4. No Singleton: _instance, get_*_instance() forbidden

## Workflow Order
/refactoring-planning -> /refactoring-execution -> /refactoring-verification -> /refactoring-pr
