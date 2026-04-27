# Conflict Patterns

Common conflict patterns and their recommended resolution strategies.

## Auto-resolvable Patterns
- **Lock Files**: `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `poetry.lock`
  - Strategy: Use `theirs` or regenerate the lock file.
- **Imports/Dependencies**: Conflicts in import sections where both sides added different imports.
  - Strategy: Merge both sets of imports and sort/dedupe.
- **Simple Appends**: Both branches added new lines to the end of a file.
  - Strategy: Keep both additions.
- **Version/Metadata**: Version bumps in `package.json` or `manifest.json`.
  - Strategy: Usually `theirs` (target branch) or manually increment if both changed.

## Manual Resolution Required
- Logic changes in the same function block.
- Conflicting structural changes (file moved on one side, edited on another).
- Complex deletions.
