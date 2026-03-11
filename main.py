"""
main.py — точка входа и оркестрация.

Запуск:  python main.py
         python main.py --date 2026-03-10   # конкретная дата (для ретро-заполнения)
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

import amo
import sheets
import telegram

# ── Логирование ───────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ── Основная логика ───────────────────────────────────────────────────────────


def run(target_date: date) -> None:
    logger.info("=== Daily report started for %s ===", target_date.isoformat())

    # 1. Получаем данные из amoCRM (пока — заглушка)
    logger.info("Step 1/3: Fetching data from amoCRM…")
    all_data = amo.get_daily_stats(target_date)

    # 2. Записываем в Google Sheets
    logger.info("Step 2/3: Writing to Google Sheets…")
    sheets.write_daily_data(all_data, target_date)

    # 3. Отправляем отчёт в Telegram
    logger.info("Step 3/3: Sending Telegram report…")
    telegram.send_report(all_data, target_date)

    logger.info("=== Done ===")


# ── CLI ───────────────────────────────────────────────────────────────────────


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="amoCRM → Google Sheets daily sync"
    )
    parser.add_argument(
        "--date",
        type=date.fromisoformat,  # формат YYYY-MM-DD
        default=None,
        help="Дата для обработки (по умолчанию — сегодня). Формат: YYYY-MM-DD",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    target = args.date or date.today()
    run(target)
