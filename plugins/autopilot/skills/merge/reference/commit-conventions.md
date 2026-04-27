# Commit Message Conventions

Follow the Angular/Conventional Commits style for automated and manual commits.

## Format
`<type>(<scope>): <subject>`

`<body (optional)>`

## Types
- `feat`: New feature or significant update
- `fix`: Bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code (white-space, formatting, etc)
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to the build process or auxiliary tools and libraries such as documentation generation

## Scope
- Use the issue key (e.g., `PROJ-123`) or the worktree branch name as the scope.

## Subject
- Use the imperative, present tense: "change" not "changed" nor "changes"
- Don't capitalize the first letter
- No dot (.) at the end
