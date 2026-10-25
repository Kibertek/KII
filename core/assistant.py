"""Основной объект ассистента KII."""

from core.actions import ActionManager
from core.narrator import Narrator


class KII:
    """Минимальное ядро KII для локального запуска."""

    def __init__(self) -> None:
        self.narrator = Narrator()
        self.actions = ActionManager(self.narrator)

    def run(self) -> None:
        self.narrator.say("KII запущен.")
        self.narrator.say("Готов к работе.")

        while True:
            try:
                command = input("Вы: ").strip()
            except (KeyboardInterrupt, EOFError):
                print()
                self.narrator.say("Завершаю работу.")
                break

            if not command:
                continue

            if command.lower() in {"выход", "выйти", "exit", "quit"}:
                self.narrator.say("Завершаю работу.")
                break

            result = self.actions.handle(command)
            print(f"KII: {result}")
