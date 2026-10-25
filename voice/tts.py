"""Локальное озвучивание KII через системный голос Windows."""

from __future__ import annotations

import sys
from typing import Any


class TTSEngine:
    """Локальный TTS с безопасным переходом в текстовый режим при ошибке."""

    def __init__(self, enabled: bool = True, rate: int = 175, volume: float = 1.0) -> None:
        self._engine: Any | None = None
        if not enabled:
            return

        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", max(100, min(rate, 250)))
            engine.setProperty("volume", max(0.0, min(volume, 1.0)))
            self._select_russian_voice(engine)
            self._engine = engine
        except Exception as exc:
            print(f"[KII] Голос недоступен, остаюсь в текстовом режиме: {exc}", file=sys.stderr)

    @staticmethod
    def _select_russian_voice(engine: Any) -> None:
        """Выбирает русский системный голос, если он установлен."""
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
            # Если список голосов недоступен, остаётся голос Windows по умолчанию.
            return

    @property
    def available(self) -> bool:
        return self._engine is not None

    def speak(self, text: str) -> bool:
        """Произносит текст. False означает, что голос недоступен."""
        if not self._engine or not text.strip():
            return False
        try:
            self._engine.say(text)
            self._engine.runAndWait()
            return True
        except Exception as exc:
            print(f"[KII] Ошибка озвучивания: {exc}", file=sys.stderr)
            self._engine = None
            return False

    def stop(self) -> None:
        """Останавливает воспроизведение, если движок доступен."""
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass
