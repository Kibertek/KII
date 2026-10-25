"""Точка входа KII."""

from core.assistant import KII


def main() -> None:
    assistant = KII()
    assistant.run()


if __name__ == "__main__":
    main()
