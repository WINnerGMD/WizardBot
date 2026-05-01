---
description: Automatic documentation update and commit generator
---

// turbo-all

This workflow automatically updates project documentation (README.md and GEMINI.md), stages all changes, generates a descriptive commit message, and commits them.

### Steps:

1. **Analyze Changes**: Get the diff of current changes to understand what was modified.
   ```bash
   git diff
   ```
2. **Update Documentation**: Based on the changes, update `README.md` and `GEMINI.md` to ensure they reflect the current state of the project (e.g., tech stack changes, new specialists, architecture updates).
3. **Stage All Changes**: Stage all modified files, including updated documentation.
   ```bash
   git add .
   ```
4. **Analyze Staged**: Review the diff of staged changes for the commit message.
   ```bash
   git diff --cached
   ```
5. **Generate & Commit**: Generate a professional message following [Conventional Commits](https://www.conventionalcommits.org/) and execute the commit.
   ```bash
   git commit -m "<ai_generated_message>"
   ```
6. **Push**: Optionally push the changes.
   ```bash
   git push
   ```