"""Короткие текстовые сообщения KII с опциональным голосовым выводом."""

from voice.tts import TTSEngine


class Narrator:
    """Единая точка сообщений; голос выключен по умолчанию."""

    def __init__(self, tts: TTSEngine | None = None, voice_enabled: bool = False) -> None:
        self.tts = tts or TTSEngine(enabled=voice_enabled)

    def say(self, text: str) -> None:
        """Выводит сообщение в консоль и озвучивает только при явном включении."""
        print(f"KII: {text}")
        self.tts.speak(text)
