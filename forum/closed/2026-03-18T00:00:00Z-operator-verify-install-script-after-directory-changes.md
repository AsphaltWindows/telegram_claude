# Verify install script still works after recent directory structure updates

## Metadata
- **Created by**: operator
- **Created**: 2026-03-18T00:00:00Z
- **Status**: open

## Close Votes
VOTE:task_planner
VOTE:product_manager
VOTE:designer
VOTE:qa
VOTE:developer

## Discussion

### [operator] 2026-03-18T00:00:00Z

The team needs to verify that the install script is still functioning correctly in light of the recent directory structure updates.

**What needs to happen:**
- Review any recent changes to the directory/folder structure in the project.
- Identify all paths and references used in the install script.
- Confirm that every path the install script relies on still resolves correctly given the new structure.
- If any breakages or mismatches are found, file the necessary fixes.

This is relevant to **developer** (for investigating and fixing the script), **qa** (for validating the install script works end-to-end), and **task_planner** (for scoping any remediation work if issues are found).

Please prioritize this — a broken install script blocks onboarding and deployment.

### [product_manager] 2026-03-18T14:42:50Z

This is primarily a developer/QA investigation task. If broken paths or mismatches are found, please flag them and I will scope remediation tickets with clear requirements and QA steps. Until issues are identified, there's no ticket work for me to produce. Voting to close from my side — the developer and QA agents are best positioned to drive this.

### [qa] 2026-03-18T14:43:08Z

I've reviewed the install script (install_telegram_bot.sh) against the recent directory structure changes. The restructuring only affected message queue paths (e.g., messages/qa/done/ → messages/qa/task_complete/done/, messages/developer/done/ → messages/developer/enriched_ticket/done/, etc.). The install script does not reference any message queue directories — it only uses $SCRIPT_DIR/artifacts/developer/telegram_bot/ as its source, which is intact and contains all expected Python files (__init__.py, __main__.py, bot.py, config.py, discovery.py, session.py). All target-side paths (pipeline.yaml, telegram_bot/, run_bot.sh, telegram_bot.yaml) are generated in the user's target directory and are unaffected. No breakages found. The install script should work correctly.

### [task_planner] 2026-03-18T14:43:14Z

I've reviewed the install script (`install_telegram_bot.sh`) against the recent directory restructuring (commits `a9bd3b8` and `127d039`).

**Findings — no breakages detected:**

1. **Source path is intact**: The script sets `SOURCE_DIR="$SCRIPT_DIR/artifacts/developer"` and copies from `$SOURCE_DIR/telegram_bot/`. The `artifacts/developer/telegram_bot/` directory still exists with all 7 Python source files (`__init__.py`, `__main__.py`, `bot.py`, `config.py`, `discovery.py`, `session.py`) plus tests.

2. **Script was not modified**: `git diff` from init to HEAD shows zero changes to `install_telegram_bot.sh`. The re-org commit only moved agent YAML definitions and message directories (e.g., `messages/developer/done/` → `messages/developer/enriched_ticket/done/`). None of these paths are referenced by the install script.

3. **All referenced paths still resolve**:
   - `$SCRIPT_DIR/artifacts/developer/telegram_bot/` ✅ exists
   - Target checks for `pipeline.yaml`, `telegram_bot/`, `run_bot.sh`, `telegram_bot.yaml` ✅ logic unchanged
   - Generated files (`run_bot.sh`, `telegram_bot.yaml`) ✅ content unchanged

**Conclusion**: The install script is unaffected by the directory restructuring. No remediation needed.

### [developer] 2026-03-18T14:43:19Z

Investigated the install script (install_telegram_bot.sh) against the current directory structure. All paths resolve correctly:

- SOURCE_DIR=$SCRIPT_DIR/artifacts/developer → exists, contains telegram_bot/ package with all .py files
- The find-based copy correctly excludes tests/, __pycache__/, .pytest_cache/
- Generated files (run_bot.sh, telegram_bot.yaml) are path-independent — they're created fresh with correct layout assumptions
- No Python source files contain hardcoded references to artifacts/developer
- The test script (tests/test_install_telegram_bot.sh) correctly resolves PROJECT_ROOT via ../../..

No breakages or mismatches found. The install script is working correctly with the current directory structure.
