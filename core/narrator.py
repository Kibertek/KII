"""Короткие сообщения о действиях KII: текст и голос."""

from voice.tts import TTSEngine


class Narrator:
    """Единая точка для текстовых и голосовых сообщений."""

    def __init__(self, tts: TTSEngine | None = None, voice_enabled: bool = True) -> None:
        self.tts = tts or TTSEngine(enabled=voice_enabled)

    def say(self, text: str) -> None:
        """Показывает сообщение и пытается произнести его вслух."""
        print(f"KII: {text}")
        self.tts.speak(text)
