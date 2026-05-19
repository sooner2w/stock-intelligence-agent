import anthropic

from memory import LongTermMemory, SemanticMemory, ShortTermMemory
from tools import TOOLS, execute_tool

MODEL = "claude-opus-4-7"
MAX_TOKENS = 4096


class Agent:
    """
    A Claude-powered agent with a three-layer memory architecture:

      1. Short-term  — sliding window of the current conversation (in-context)
      2. Long-term   — SQLite episodic log; every turn persisted across sessions
      3. Semantic    — Chroma vector store; recalled by similarity at turn start

    The tool calling loop is manual so you can see every step clearly.
    """

    def __init__(self, session_id=None):
        self.client = anthropic.Anthropic()
        self.short_term = ShortTermMemory(max_turns=20)
        self.long_term = LongTermMemory()
        self.semantic = SemanticMemory()

        # Create a new session or resume an existing one
        self.session_id = session_id or self.long_term.new_session()
        print(f"[agent] session: {self.session_id}")

    # ------------------------------------------------------------------ #
    # Public API

    def chat(self, user_message: str) -> str:
        """Send a user message; return the agent's final text reply."""

        # 1. Persist user turn
        self.short_term.add("user", user_message)
        self.long_term.add(self.session_id, "user", user_message)

        # 2. Build system prompt injecting relevant semantic memories
        system = self._build_system_prompt(user_message)

        # 3. Tool-calling loop
        while True:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                thinking={"type": "adaptive"},
                system=system,
                tools=TOOLS,
                messages=self.short_term.get_messages(),
            )

            # -- end_turn: Claude is done --
            if response.stop_reason == "end_turn":
                reply = _extract_text(response)
                self.short_term.add("assistant", response.content)
                self.long_term.add(self.session_id, "assistant", reply)
                return reply

            # -- tool_use: execute tools and feed results back --
            if response.stop_reason == "tool_use":
                # Add Claude's response (including tool_use blocks) to short-term
                self.short_term.add("assistant", response.content)

                # Build tool results
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"[tool] {block.name}({block.input})")
                        result = execute_tool(block.name, block.input, self.semantic)
                        print(f"[tool] → {result[:120]}")
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            }
                        )

                # Feed results back to Claude in the next iteration
                self.short_term.add("user", tool_results)

            else:
                # Unexpected stop reason — surface it and break
                print(f"[agent] unexpected stop_reason: {response.stop_reason}")
                break

        return ""

    # ------------------------------------------------------------------ #
    # Internals

    def _build_system_prompt(self, query: str) -> str:
        relevant = self.semantic.search(query, n_results=3)
        memory_block = ""
        if relevant:
            joined = "\n".join(f"- {m}" for m in relevant)
            memory_block = f"\n\n## Relevant memories\n{joined}"

        return (
            "You are a helpful, thoughtful AI assistant with persistent memory. "
            "You have access to tools for saving and searching your memory. "
            "Use `search_memory` before answering questions about the user's history or preferences. "
            "Use `save_memory` whenever you learn something important about the user."
            + memory_block
        )


# ------------------------------------------------------------------ #
# Helpers

def _extract_text(response) -> str:
    """Pull plain text from the response content blocks."""
    parts = []
    for block in response.content:
        if hasattr(block, "type") and block.type == "text":
            parts.append(block.text)
    return "\n".join(parts)
