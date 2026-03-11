"""
telegram.py — отправка ежедневного отчёта в Telegram.
"""

from __future__ import annotations

import logging
from datetime import date

import requests

import config

logger = logging.getLogger(__name__)

_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

# Названия дней недели на русском
_WEEKDAYS_RU = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


def send_report(
    all_managers_data: dict[int, dict[str, int | float]],
    target_date: date,
) -> None:
    """
    Формирует и отправляет отчёт в Telegram.

    По каждому менеджеру:
      - кол-во подтверждённых праздников + сумма
      - кол-во согласованных + сумма
    """
    text = _format_report(all_managers_data, target_date)
    _send_message(text)


def _format_report(
    all_managers_data: dict[int, dict[str, int | float]],
    target_date: date,
) -> str:
    weekday = _WEEKDAYS_RU[target_date.weekday()]
    date_str = f"{target_date.strftime('%d.%m.%Y')} ({weekday})"

    lines = [f"<b>Отчёт за {date_str}</b>\n"]

    for manager_index, manager_id in enumerate(config.MANAGER_IDS, start=1):
        data = all_managers_data.get(manager_id, {})
        name = config.MANAGER_NAMES.get(manager_id, f"Менеджер {manager_index}")

        hot_leads       = int(data.get("hot_leads", 0))
        taken_to_work   = int(data.get("taken_to_work", 0))
        data_received   = int(data.get("data_received", 0))
        kp_sent         = int(data.get("kp_sent", 0))
        agreed_count    = int(data.get("agreed_count", 0))
        agreed_sum      = float(data.get("agreed_sum", 0))
        confirmed_count = int(data.get("confirmed_count", 0))
        confirmed_sum   = float(data.get("confirmed_sum", 0))
        rejected        = int(data.get("rejected", 0))

        lines.append(
            f"👤 <b>{name}</b>\n"
            f"  🔥 Горячие (Входящее обращение): {hot_leads}\n"
            f"  📥 Взят в работу: {taken_to_work}\n"
            f"  📋 Данные для КП получены: {data_received}\n"
            f"  📤 КП отправлено: {kp_sent}\n"
            f"  🤝 Праздник согласован: {agreed_count}  ({_fmt_money(agreed_sum)})\n"
            f"  ✅ Праздник подтверждён: {confirmed_count}  ({_fmt_money(confirmed_sum)})\n"
            f"  ❌ Отказ: {rejected}"
        )

    # Итоговая строка
    total_confirmed = sum(
        int(d.get("confirmed_count", 0)) for d in all_managers_data.values()
    )
    total_sum = sum(
        float(d.get("confirmed_sum", 0)) for d in all_managers_data.values()
    )
    lines.append(
        f"\n<b>Итого подтверждено: {total_confirmed}  ({_fmt_money(total_sum)})</b>"
    )

    return "\n".join(lines)


def _fmt_money(amount: float) -> str:
    """Форматирует сумму: 55000 → '55 000 ₽'."""
    return f"{amount:,.0f} ₽".replace(",", "\u202f")  # тонкий пробел как разделитель тысяч


def _send_message(text: str) -> None:
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials not configured. Skipping message send.")
        logger.info("Report text:\n%s", text)
        return

    url = _API_URL.format(token=config.TELEGRAM_BOT_TOKEN)
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }

    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    logger.info("Telegram report sent successfully.")
