"""Менеджер команд KII."""

from core.narrator import Narrator
from core.windows_actions import WindowsActions


class ActionManager:
    """Распознаёт ограниченный набор команд и сообщает о действиях."""

    def __init__(self, narrator: Narrator) -> None:
        self.narrator = narrator
        self.windows = WindowsActions()

    def handle(self, command: str) -> str:
        normalized = command.strip()
        lowered = normalized.lower()

        # Путь проверяется раньше названий программ, чтобы не спутать команды.
        for prefix in ("открой файл ", "открой папку ", "открой путь "):
            if lowered.startswith(prefix):
                path = normalized[len(prefix):].strip()
                self.narrator.say("Открываю файл или папку.")
                return self.windows.open_path(path)

        for prefix in ("открой ", "запусти ", "открыть "):
            if lowered.startswith(prefix):
                program = normalized[len(prefix):].strip()
                self.narrator.say(f"Запускаю {program}.")
                return self.windows.launch_program(program)

        if any(phrase in lowered for phrase in (
            "системная информация",
            "информация о системе",
            "характеристики компьютера",
            "покажи систему",
        )):
            self.narrator.say("Получаю информацию о системе.")
            return self.windows.system_info()

        if lowered in {"помощь", "команды", "что ты умеешь"}:
            return (
                "Команды: «открой блокнот», «открой калькулятор», "
                "«открой проводник», «открой paint», "
                "«открой файл ПУТЬ», «открой папку ПУТЬ», "
                "«покажи системную информацию», «выход»."
            )

        self.narrator.say("Обрабатываю команду.")
        return f"Эта команда пока не подключена: {normalized}"
