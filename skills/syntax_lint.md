# Skill: Static Code Review
- **Action Keyword:** lint_code
- **Model Target:** qwen2.5-coder:7b
- **Description:** Reads a block of source and reports likely defects - syntax errors, unhandled exceptions, unused imports, off-by-one and resource leaks. Use before code is saved or handed on.
- **CRITICAL CONSTRAINT:** You are READING, not running. Everything you report is a reading, not a proof - say `unverified` on anything you did not trace line by line. Do not rewrite the file. Report at most the 5 most serious findings; if the code looks sound, say so in one line rather than inventing faults.
- **Output Structure Requirement:** One block per finding:
  ```
  • Line: <number or "unknown">
  • Bug: <one sentence>
  • Severity: high|medium|low
  • Patch: <the corrected line only, not the whole file>
  ```
- **Parameters Needed:** <content>The source code to review</content>
