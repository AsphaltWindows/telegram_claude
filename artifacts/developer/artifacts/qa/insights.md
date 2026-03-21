# QA Agent Insights

## 2026-03-20

- When a developer changes function behavior (e.g., `_extract_text_from_event`), always run the FULL test suite, not just the new test file. Old tests in other files may still assert the previous behavior and will silently become stale.
- The `scripts/add_comment.sh` and `scripts/vote_close.sh` scripts don't exist in this repo. Edit forum topic files directly to add comments and votes.
- Forum topic files may be modified by other agents between Read and Write. Always re-read immediately before writing.
- Developer artifacts live in `artifacts/developer/` but the live code is in `telegram_bot/`. Tests import from the live code path. If developer changes are only in artifacts, tests will fail against the live code.
