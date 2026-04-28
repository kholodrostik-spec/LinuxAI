from app.rag_agent import answer_question


def main() -> None:
    print("LinuxAI RAG Agent")
    print("Type 'exit' to quit.")
    print()

    while True:
        try:
            question = input("Question: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye.")
            break

        if question.lower() in {"exit", "quit", "q"}:
            break

        if not question:
            continue

        print("\nThinking...\n")

        try:
            answer = answer_question(question)
        except RuntimeError as error:
            print(f"[error] {error}\n")
            continue
        except Exception as error:
            print(f"[unexpected error] {error}\n")
            continue

        print("=" * 80)
        print(answer)
        print("=" * 80)
        print()


if __name__ == "__main__":
    main()
