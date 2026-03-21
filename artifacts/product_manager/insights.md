# Product Manager Insights

- When a design change touches multiple sections of the design doc (e.g., idle timer fix + death notifications + heartbeat), break into separate tickets per section with explicit dependency ordering. The heartbeat depends on the timer fix since it builds on the same activity-tracking mechanism.
- Always read the full design.md to understand existing error handling (e.g., circuit breaker, retry logic) before scoping tickets — death notification requirements interact with existing retry/circuit-breaker behavior.
