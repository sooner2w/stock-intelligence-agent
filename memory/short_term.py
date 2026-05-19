class ShortTermMemory:
    """
    Sliding window over the current conversation in Claude API message format.
    Keeps the last `max_turns` user/assistant pairs so the context window
    stays bounded regardless of session length.
    """

    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self._messages: list[dict] = []

    def add(self, role: str, content) -> None:
        """Append a message. content can be a string or a list of content blocks."""
        self._messages.append({"role": role, "content": content})
        self._trim()

    def get_messages(self) -> list[dict]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    # ------------------------------------------------------------------ #

    def _trim(self) -> None:
        # Each turn is one user message + one assistant message (2 entries).
        # We keep at most max_turns * 2 entries.
        limit = self.max_turns * 2
        if len(self._messages) > limit:
            self._messages = self._messages[-limit:]
