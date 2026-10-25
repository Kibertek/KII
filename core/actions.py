"""Менеджер пользовательских действий KII."""

from dataclasses import dataclass

from core.narrator import Narrator


@dataclass(frozen=True)
class Action:
    """Описание безопасного пользовательского действия."""

    name: str
    narration: str
    result: str


class ActionManager:
    """Определяет базовые команды и сообщает о выполняемом действии."""

    def __init__(self, narrator: Narrator) -> None:
        self.narrator = narrator
        self.actions = {
            "открой программу": Action(
                name="open_program",
                narration="Открываю программу.",
                result="Команда распознана. Реальный запуск приложения подключим следующим этапом.",
            ),
            "выведи данные": Action(
                name="show_data",
                narration="Вывожу данные.",
                result="Команда распознана. Источник данных подключим следующим этапом.",
            ),
        }

    def handle(self, command: str) -> str:
        normalized = command.lower().strip()

        for trigger, action in self.actions.items():
            if trigger in normalized:
                self.narrator.say(action.narration)
                return action.result

        self.narrator.say("Обрабатываю команду.")
        return f"Команда пока не подключена: {command}"
