# Product Manager Insights

- When breaking error-handling designs into tickets, separate the retry mechanism from the circuit breaker. The retry wrapper is a dependency of the circuit breaker, so they should be two tickets with an explicit dependency noted in the second.
- Always check the actual codebase (e.g., bot.py) to understand which functions need modification — this helps write concrete requirements referencing real function names rather than abstract descriptions.
- The send_message.sh script takes: from, to, message_type, message_name, content (5 positional args).
