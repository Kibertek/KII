"""Локальный голос KII: Piper TTS с резервным системным движком."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_NAME = "ru_RU-irina-medium.onnx"


def _find_model() -> Path | None:
    """Находит модель Piper в стандартных местах или по переменной окружения."""
    configured = os.getenv("KII_PIPER_MODEL")
    candidates = [
        Path(configured).expanduser() if configured else None,
        PROJECT_ROOT / "models" / "voice" / DEFAULT_MODEL_NAME,
        PROJECT_ROOT / DEFAULT_MODEL_NAME,
        PROJECT_ROOT / "models" / "voice" / "ru" / "ru_RU" / "irina" / "medium" / DEFAULT_MODEL_NAME,
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate.resolve()
    return None


class TTSEngine:
    """Офлайн TTS. Piper используется первым, pyttsx3 — как запасной вариант."""

    def __init__(
        self,
        enabled: bool = True,
        rate: int = 165,
        volume: float = 0.9,
        length_scale: float = 1.08,
    ) -> None:
        self.enabled = enabled
        self.rate = max(100, min(int(rate), 250))
        self.volume = max(0.0, min(float(volume), 1.0))
        # Значение выше 1 немного замедляет Piper и делает подачу размереннее.
        self.length_scale = max(0.7, min(float(length_scale), 1.5))
        self._engine: Any | None = None
        self._piper_model = _find_model()
        self._piper_installed = importlib.util.find_spec("piper") is not None
        self._lock = threading.Lock()
        self._player: subprocess.Popen[bytes] | None = None

        if not enabled:
            return

        if self._piper_installed and self._piper_model:
            print(f"[KII] Локальный нейросетевой голос Piper: {self._piper_model.name}")

        # Инициализируем резервный движок даже при наличии Piper:
        # если синтез или воспроизведение WAV не сработает, останется системный TTS.
        self._init_system_voice()

        if not self._piper_model:
            print(
                "[KII] Модель Piper не найдена. Используется системный голос, "
                "если он доступен. См. README.md для установки русского голоса.",
                file=sys.stderr,
            )

    def _init_system_voice(self) -> None:
        """Подготавливает pyttsx3 как резервный локальный движок."""
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", self.rate)
            engine.setProperty("volume", self.volume)
            self._select_russian_voice(engine)
            self._engine = engine
        except Exception as exc:
            print(f"[KII] Системный голос недоступен: {exc}", file=sys.stderr)

    @staticmethod
    def _select_russian_voice(engine: Any) -> None:
        """Выбирает русский системный голос, если такой установлен."""
        try:
            for voice in engine.getProperty("voices") or []:
                description = " ".join(
                    str(getattr(voice, field, ""))
                    for field in ("id", "name", "languages")
                ).lower()
                if "ru-" in description or "ru_" in description or "russian" in description:
                    engine.setProperty("voice", voice.id)
                    return
        except Exception:
            # Остаёмся на голосе ОС по умолчанию.
            return

    @property
    def available(self) -> bool:
        """True, если доступен Piper с моделью или системный TTS."""
        return bool(
            self.enabled
            and (
                (self._piper_installed and self._piper_model)
                or self._engine is not None
            )
        )

    @property
    def engine_name(self) -> str:
        if self._piper_installed and self._piper_model:
            return "Piper / ru_RU-irina-medium"
        if self._engine is not None:
            return "pyttsx3 / системный голос"
        return "недоступен"

    def speak(self, text: str) -> bool:
        """Произносит текст офлайн. Возвращает False, если озвучить не удалось."""
        text = text.strip()
        if not self.enabled or not text:
            return False

        with self._lock:
            if self._piper_installed and self._piper_model:
                try:
                    self._speak_with_piper(text)
                    return True
                except Exception as exc:
                    print(f"[KII] Piper не смог озвучить текст: {exc}", file=sys.stderr)

            if self._engine is not None:
                try:
                    self._engine.say(text)
                    self._engine.runAndWait()
                    return True
                except Exception as exc:
                    print(f"[KII] Ошибка системного голоса: {exc}", file=sys.stderr)
                    self._engine = None

        return False

    def _speak_with_piper(self, text: str) -> None:
        """Создаёт WAV локально через Piper и передаёт его системному проигрывателю."""
        assert self._piper_model is not None
        fd, temporary_name = tempfile.mkstemp(prefix="kii-voice-", suffix=".wav")
        os.close(fd)
        wav_path = Path(temporary_name)

        try:
            command = [
                sys.executable, "-m", "piper",
                "--model", str(self._piper_model),
                "--length-scale", str(self.length_scale),
                "--noise-scale", "0.667",
                "--noise-w", "0.8",
                "--sentence-silence", "0.12",
                "--output_file", str(wav_path),
                "--",
                text,
            ]
            result = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120,
                check=False,
            )
            if result.returncode != 0 or not wav_path.is_file() or wav_path.stat().st_size == 0:
                details = (result.stderr or "Piper не создал WAV-файл").strip()
                raise RuntimeError(details[-1200:])

            self._play_wav(wav_path)
        finally:
            try:
                wav_path.unlink(missing_ok=True)
            except OSError:
                pass

    def _play_wav(self, wav_path: Path) -> None:
        """Воспроизводит WAV через стандартное средство текущей ОС."""
        if sys.platform == "win32":
            import winsound

            winsound.PlaySound(str(wav_path), winsound.SND_FILENAME)
            return

        if sys.platform == "darwin":
            player = shutil.which("afplay")
            command = [player, str(wav_path)] if player else None
        else:
            player = shutil.which("paplay") or shutil.which("aplay")
            command = [player, str(wav_path)] if player else None

        if command is None:
            raise RuntimeError(
                "Не найден аудиопроигрыватель (Linux: установи paplay или aplay)."
            )

        self._player = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            return_code = self._player.wait(timeout=180)
            if return_code != 0:
                raise RuntimeError(f"Аудиопроигрыватель завершился с кодом {return_code}.")
        finally:
            self._player = None

    def stop(self) -> None:
        """Останавливает доступное воспроизведение."""
        player = self._player
        if player and player.poll() is None:
            player.terminate()

        if self._engine is not None:
            try:
                self._engine.stop()
            except Exception:
                pass

        if sys.platform == "win32":
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
