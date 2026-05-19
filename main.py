"""
Demo entry point.

  python main.py             — start a fresh session
  python main.py <session_id> — resume an existing session
"""

import sys

from agent import Agent


def main():
    session_id = sys.argv[1] if len(sys.argv) > 1 else None
    agent = Agent(session_id=session_id)

    print("\nAgent ready. Type 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "bye"}:
            print("Bye.")
            break

        reply = agent.chat(user_input)
        print(f"\nAgent: {reply}\n")


if __name__ == "__main__":
    main()
