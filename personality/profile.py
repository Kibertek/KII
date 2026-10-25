"""Настраиваемые параметры характера KII."""

from dataclasses import dataclass


@dataclass
class PersonalityProfile:
    """Базовый профиль личности.

    Значения находятся в диапазоне 0-10 и могут изменяться со временем.
    """

    intelligence: int = 9
    calmness: int = 10
    independence: int = 7
    sarcasm: int = 3
    emotion: int = 2
    verbosity: int = 2
    initiative: int = 6
    formality: int = 4
    humor: int = 3

    def set_value(self, name: str, value: int) -> None:
        """Изменить параметр профиля с проверкой диапазона."""
        if not hasattr(self, name):
            raise ValueError(f"Неизвестный параметр личности: {name}")

        if not 0 <= value <= 10:
            raise ValueError("Параметр личности должен быть от 0 до 10.")

        setattr(self, name, value)
