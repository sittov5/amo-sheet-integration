"""
bot.py — Telegram-бот для ручного запуска отчёта.

Команды:
  /report              — отчёт за сегодня
  /report ГГГГ-ММ-ДД  — отчёт за конкретную дату (для проверки прошлых дней)

Запуск: python bot.py
Бот принимает команды только из чатов TELEGRAM_CHAT_IDS (из .env).
"""

from __future__ import annotations

import logging
import sys
from datetime import date

import requests

import config
import main as runner

logger = logging.getLogger(__name__)

_API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


# ── Telegram helpers ──────────────────────────────────────────────────────────


def _get_updates(offset: int) -> list[dict]:
    resp = requests.get(
        f"{_API}/getUpdates",
        params={"offset": offset, "timeout": 30},
        timeout=35,
    )
    resp.raise_for_status()
    return resp.json().get("result", [])


def _send(chat_id: int | str, text: str) -> None:
    requests.post(
        f"{_API}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )


# ── Обработка команд ──────────────────────────────────────────────────────────


def _handle(message: dict) -> None:
    chat_id = str(message.get("chat", {}).get("id", ""))
    text    = (message.get("text") or "").strip()

    # Принимаем команды только из авторизованных чатов
    if chat_id not in [str(c) for c in config.TELEGRAM_CHAT_IDS]:
        logger.warning("Ignoring message from unauthorized chat_id=%s", chat_id)
        return

    if not text.startswith("/report"):
        return

    parts = text.split()
    if len(parts) >= 2:
        try:
            target = date.fromisoformat(parts[1])
        except ValueError:
            _send(chat_id, "❌ Неверный формат даты. Пример: /report 2026-03-10")
            return
    else:
        target = date.today()

    _send(chat_id, f"⏳ Запускаю отчёт за {target.strftime('%d.%m.%Y')}…")

    try:
        runner.run(target)
        # Сам отчёт придёт через telegram.send_report() — отдельного сообщения не нужно
    except Exception as exc:
        logger.exception("Report run failed")
        _send(chat_id, f"❌ Ошибка при формировании отчёта:\n<code>{exc}</code>")


# ── Polling loop ──────────────────────────────────────────────────────────────


def poll() -> None:
    logger.info("Bot started. Listening for /report commands in chats %s…",
                config.TELEGRAM_CHAT_IDS)
    offset = 0

    while True:
        try:
            updates = _get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message") or update.get("edited_message")
                if message:
                    _handle(message)
        except KeyboardInterrupt:
            logger.info("Bot stopped.")
            break
        except requests.RequestException as exc:
            logger.error("Network error: %s", exc)


# ── Entry point ───────────────────────────────────────────────────────────────


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    poll()
