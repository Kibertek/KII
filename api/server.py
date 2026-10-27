"""Локальный HTTP API для подключения клиентов KII.

По умолчанию сервер слушает только loopback. Для доступа из локальной сети
задай KII_API_HOST=0.0.0.0 и обязательно установи KII_API_TOKEN.
"""

from __future__ import annotations

import hmac
import os
from typing import Literal

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.actions import ActionManager
from core.narrator import Narrator

APP_VERSION = "0.1.0"
API_TOKEN = os.getenv("KII_API_TOKEN", "").strip()
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "KII_ALLOWED_ORIGINS",
        "http://localhost:8080,http://127.0.0.1:8080",
    ).split(",")
    if origin.strip()
]

app = FastAPI(
    title="KII API",
    description="API комплекса «Комплексный интеллектуальный интерфейс».",
    version=APP_VERSION,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "X-KII-API-Key"],
)

# Голосовой вывод намеренно отключён. Его подключим отдельным этапом.
actions = ActionManager(Narrator(voice_enabled=False))


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: str = Field(min_length=1, max_length=128)
    client: str = Field(default="unknown", max_length=64)


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    client: str


def verify_api_key(x_kii_api_key: str | None = Header(default=None)) -> None:
    """Проверяет ключ, если он настроен на сервере."""
    if API_TOKEN and not hmac.compare_digest(x_kii_api_key or "", API_TOKEN):
        raise HTTPException(status_code=401, detail="Неверный или отсутствующий API-ключ.")


@app.get("/health")
def health() -> dict[str, str | bool]:
    """Проверка доступности сервиса без раскрытия конфигурации."""
    return {
        "status": "ok",
        "service": "kii-api",
        "version": APP_VERSION,
        "voice_output": False,
    }


@app.post("/api/v1/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
def chat(payload: ChatRequest) -> ChatResponse:
    """Передаёт текст в текущий безопасный обработчик команд KII."""
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Сообщение не должно быть пустым.")

    reply = actions.handle(message)
    return ChatResponse(reply=reply, session_id=payload.session_id, client=payload.client)


def main() -> None:
    host = os.getenv("KII_API_HOST", "127.0.0.1").strip() or "127.0.0.1"
    try:
        port = int(os.getenv("KII_API_PORT", "8000"))
    except ValueError as exc:
        raise SystemExit("KII_API_PORT должен быть целым числом.") from exc

    if not 1 <= port <= 65535:
        raise SystemExit("KII_API_PORT должен быть в диапазоне 1–65535.")

    if host in {"0.0.0.0", "::", "*"} and not API_TOKEN:
        raise SystemExit(
            "Отказ запуска: для доступа не только с этого компьютера задай "
            "KII_API_TOKEN. Не выставляй API в сеть без аутентификации."
        )

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
