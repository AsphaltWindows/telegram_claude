# Task Planner Insights

- `telegram_bot/session.py` is a key file: manages agent lifecycle, idle timers, stdin/stdout communication. The `send()` method handles user->agent input; `_read_stdout()` handles agent->user output. Activity tracking (`last_activity` + `_reset_idle_timer()`) must be maintained in both directions.
- Always check `git diff` for uncommitted changes before enriching a ticket — a previous developer session may have already applied the fix. Note this in the enriched ticket so the developer doesn't duplicate work.
- Use relative paths with `scripts/vote_close.sh` and `scripts/send_message.sh` — they prepend the working directory internally.
