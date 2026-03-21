# add-typing-indicator-heartbeat

## Metadata
- **From**: developer
- **To**: qa

## Content

### Summary of Changes

Implemented typing indicator heartbeat that sends Telegram 'typing...' indicators during long agent operations when no output has been received for 5 seconds.

### Files Changed

- **telegram_bot/session.py** - Added _TYPING_HEARTBEAT_INTERVAL constant (5s), on_typing callback parameter to Session.__init__, _typing_task field, _typing_heartbeat() async method, updated start() to launch typing task, updated _finish() to cancel typing task, updated SessionManager.start_session to accept and pass on_typing.
- **telegram_bot/bot.py** - Added on_typing closure in agent_command_handler that calls bot.send_chat_action(action='typing'), passes it to session_manager.start_session.
- **telegram_bot/tests/test_typing_heartbeat.py** - New test file with 8 tests covering the typing heartbeat feature.

### Requirements Addressed

1. Bot sends typing indicator when no agent output for 5 seconds - DONE via _typing_heartbeat() checking last_activity
2. Typing indicator repeats periodically (every 5 seconds) - DONE via loop with asyncio.sleep(_TYPING_HEARTBEAT_INTERVAL)
3. Typing indicator stops when output arrives or session ends - DONE: checks _ended flag and last_activity freshness each iteration
4. Send errors are non-critical (logged and continued) - DONE: try/except Exception with logger.exception
5. Depends on idle timer fix - DONE: uses same last_activity field established by that ticket

### QA Steps

1. Start a session and send a message that triggers a long agent operation. Verify the Telegram chat shows a 'typing...' indicator while the agent is working.
2. Verify the typing indicator stops once the agent sends its response.
3. Verify that if the typing indicator send fails (e.g., network error), the session continues normally and the agent response is still delivered.
4. Verify the typing indicator does not appear during normal fast request/response exchanges.

### Test Coverage

8 tests in test_typing_heartbeat.py:
- test_typing_heartbeat_sends_after_silence - verifies indicator sent after silence
- test_typing_heartbeat_not_sent_during_activity - verifies no indicator during active output
- test_typing_heartbeat_stops_when_session_ends - verifies clean stop on session end
- test_typing_heartbeat_handles_callback_exception - verifies error handling
- test_typing_heartbeat_handles_cancellation - verifies CancelledError handling
- test_typing_heartbeat_not_started_when_no_callback - verifies backward compatibility
- test_typing_task_cancelled_in_finish - verifies cleanup in _finish()
- test_typing_heartbeat_sends_repeatedly - verifies periodic sending

Run: cd artifacts/developer && python -m pytest telegram_bot/tests/test_typing_heartbeat.py -v

### Notes

- The on_typing parameter is optional (defaults to None) for backward compatibility. Existing tests that create Sessions without on_typing continue to work.
- The heartbeat interval is set to 5 seconds via _TYPING_HEARTBEAT_INTERVAL constant, matching Telegram's typing indicator expiry.
- The typing heartbeat uses the same last_activity timestamp that _read_stdout() updates, so it naturally stops when agent output arrives.
