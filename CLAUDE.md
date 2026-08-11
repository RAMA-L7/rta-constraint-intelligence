# Skills
- **check-sdc** (`.claude/skills/check-sdc/SKILL.md`) - Validate an SDC file. Trigger: `/check-sdc <file>`
- **run-tests** (`.claude/skills/run-tests/SKILL.md`) - Run the test suite. Trigger: `/run-tests`

# Hooks
- PostToolUse: auto-run tests after Edit/Write

# Agents
- **code-reviewer** (`.claude/agents/code-reviewer.md`) - Reviews code for bugs, cross-module impacts, quality
- **security-reviewer** (`.claude/agents/security-reviewer.md`) - Safety review for signoff-quality standards
- **test-writer** (`.claude/agents/test-writer.md`) - Generates pytest tests following project conventions
- **refactor-helper** (`.claude/agents/refactor-helper.md`) - Renames, extracts, restructures code safely
- **docs-generator** (`.claude/agents/docs-generator.md`) - Generates docstrings, README, inline comments
