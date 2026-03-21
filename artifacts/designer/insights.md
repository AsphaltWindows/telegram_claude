# Designer Insights

- Forum topics may be purely informational (e.g., pipeline operational confirmations). Quick close-vote and move on.
- When a forum topic identifies a bug with code analysis and a developer-proposed fix, the designer's job is to specify the UX-facing requirements (retry counts, user-visible messages, failure modes) and update the design doc — not to re-analyze the code.
- The idle timer / session death bug keeps recurring as new forum topics. The core design requirements are: (1) idle timeout must account for agent output activity, (2) users must get explicit messages on session termination, (3) heartbeat/typing indicators for long operations. These are now documented in comments across multiple topics — ensure they land in the design doc if not already there.
