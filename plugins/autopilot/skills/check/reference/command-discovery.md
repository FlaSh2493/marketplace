# Command Discovery Rules (Node.js Only)

This document outlines how verification commands are automatically detected for Node.js projects.

## Verification Items

1. **Lint**
   - Check `scripts.lint` in `package.json` -> `npm run lint`
   - If not found, check for `.eslintrc.*` or `eslint.config.js` -> `npx eslint .`

2. **Check-types**
   - Check `scripts.check-types` in `package.json` -> `npm run check-types`
   - If not found, check `scripts.typecheck` -> `npm run typecheck`
   - If not found, check for `tsconfig.json` -> `npx tsc --noEmit`

3. **Test**
   - Check `scripts.test` in `package.json` -> `npm run test`
   - If not found, check for `vitest.config.*` -> `npx vitest run`
   - If not found, check for `jest.config.js` -> `npx jest`

## Caching

Discovery results are cached in `.docs/tasks/{issue_key}/verify-config.json` to avoid redundant detection.
