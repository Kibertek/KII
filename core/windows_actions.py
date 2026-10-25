"""Базовые действия Windows с ограниченным набором запускаемых программ."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


class WindowsActions:
    """Открытие разрешённых приложений, файлов и папок, сведения о системе."""

    PROGRAMS: dict[str, list[str]] = {
        "блокнот": ["notepad.exe"],
        "notepad": ["notepad.exe"],
        "калькулятор": ["calc.exe"],
        "calculator": ["calc.exe"],
        "проводник": ["explorer.exe"],
        "explorer": ["explorer.exe"],
        "paint": ["mspaint.exe"],
        "паинт": ["mspaint.exe"],
        "paint": ["mspaint.exe"],
    }

    def launch_program(self, name: str) -> str:
        """Запускает только приложение из разрешённого списка."""
        normalized = name.strip().lower()
        command = self.PROGRAMS.get(normalized)
        if not command:
            allowed = ", ".join(sorted({"Блокнот", "Калькулятор", "Проводник", "Paint"}))
            return f"Не запускаю неизвестную программу. Пока разрешены: {allowed}."

        try:
            subprocess.Popen(command, shell=False)
            return f"Запустил: {normalized}."
        except FileNotFoundError:
            return f"Не удалось найти приложение «{normalized}» в этой системе."
        except OSError as exc:
            return f"Не удалось запустить приложение: {exc}"

    def open_path(self, raw_path: str) -> str:
        """Открывает существующий путь средствами операционной системы."""
        cleaned = raw_path.strip().strip('"').strip("'")
        if not cleaned:
            return "Не указан путь к файлу или папке."

        path = Path(os.path.expandvars(os.path.expanduser(cleaned))).resolve()
        if not path.exists():
            return f"Путь не найден: {path}"

        try:
            if sys.platform == "win32":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)], shell=False)
            else:
                opener = shutil.which("xdg-open")
                if not opener:
                    return "Не найден системный инструмент xdg-open."
                subprocess.Popen([opener, str(path)], shell=False)
            kind = "папку" if path.is_dir() else "файл"
            return f"Открываю {kind}: {path}"
        except OSError as exc:
            return f"Не удалось открыть путь: {exc}"

    def system_info(self) -> str:
        """Возвращает базовую информацию без сторонних библиотек."""
        details = [
            f"ОС: {platform.system()} {platform.release()}",
            f"Версия: {platform.version()}",
            f"Архитектура: {platform.machine()}",
            f"Процессор: {platform.processor() or 'не определён'}",
            f"Python: {platform.python_version()}",
        ]

        memory = self._memory_info()
        if memory:
            details.append(memory)

        return "\n".join(details)

    @staticmethod
    def _memory_info() -> str | None:
        """Получает объём оперативной памяти в Windows без psutil."""
        if sys.platform != "win32":
            return None

        try:
            import ctypes
            from ctypes import wintypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", wintypes.DWORD),
                    ("dwMemoryLoad", wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                total = status.ullTotalPhys / (1024**3)
                available = status.ullAvailPhys / (1024**3)
                return f"ОЗУ: {total:.1f} ГБ всего, {available:.1f} ГБ свободно"
        except Exception:
            return None

        return None
