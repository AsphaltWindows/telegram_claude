# Task Planner Insights

- The developer's modified code often lives in `artifacts/developer/` but may not be applied to the live codebase. Always compare both versions when investigating test failures or enriching tickets. The live `telegram_bot/session.py` and the developer's `artifacts/developer/telegram_bot/session.py` can be out of sync.

- Test files live in `artifacts/developer/tests/` (top-level tests) and `artifacts/developer/telegram_bot/tests/` (package tests). There are currently NO test files in the live codebase outside of artifacts.

- When a ticket says "do not modify production code", verify whether the production code changes from a prior ticket have actually been applied. If not, flag this as a critical dependency in the enriched ticket.

- Forum topic close votes get cleared when any agent adds a new comment (`add_comment.sh` runs `sed -i '/^VOTE:.\+$/d'`). After commenting, always re-vote if you want to close.
