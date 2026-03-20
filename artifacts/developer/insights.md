# Developer Insights

- When writing async tests with timed mock readlines under pytest-asyncio 1.3.0, use `await asyncio.sleep()` delays inside the mock readline (e.g., 0.7s) rather than relying on immediate mock returns + external sleep. The pytest-asyncio event loop may not schedule `asyncio.create_task` background tasks reliably when mock coroutines return instantly. Timed readlines that yield control properly always work.
- The idle timer reset pattern in Session is: `self.last_activity = time.monotonic()` followed by `self._reset_idle_timer()`. This 2-line pattern is used in both `send()` and `_read_stdout()`.
