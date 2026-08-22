import sys

from agent import ask

BANNER = """
Oraculo — Flaming Moe's virtual factory assistant
Ask about the process, the services or the OT tools.
Type 'exit' (or 'salir') to quit.
"""


def _run(question):
    return "".join(ask(question, history=_history))


_history = []


def _repl():
    print(BANNER.strip())
    while True:
        try:
            question = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            continue
        if question.lower() in ("exit", "quit", "salir"):
            break
        print()
        answer = _run(question)
        print(f"\nOraculo> {answer}")
        _history.append({"role": "user", "content": question})
        _history.append({"role": "assistant", "content": answer})


def main():
    question = " ".join(sys.argv[1:]).strip()
    if question:
        print(_run(question))
    else:
        _repl()


if __name__ == "__main__":
    main()
