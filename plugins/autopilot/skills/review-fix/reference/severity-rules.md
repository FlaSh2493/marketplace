# Severity Classification Rules

| Severity | Criteria | Prefix | Keywords |
|----------|----------|--------|----------|
| **critical** | security, vulnerability, data loss, race condition, crash | `[!]` | security, vulnerability, data loss, race condition, crash, deadlock, memory leak |
| **important** | bug, logic error, performance, type mismatch, incorrect behavior | `[*]` | bug, logic error, performance, type mismatch, incorrect, missing, redundant |
| **suggestion** | refactoring, naming, code style, best practices | `[~]` | consider, could be, refactor, naming, style, clean, improve |
| **nitpick** | formatting, minor preference, typo | `[.]` | nit:, style, formatting, typo, grammar |

## CodeRabbit Specifics
- CodeRabbit often uses prefixes like `nit:`, `Suggestion:`, `Important:`.
- If a prefix exists, it takes precedence.
