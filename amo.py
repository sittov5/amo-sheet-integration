"""
amo.py — работа с amoCRM API v4.

Логика подсчёта (соответствует фильтру CRM «Созданы: За сегодня»):
  - hot_leads      : все сделки, СОЗДАННЫЕ за день
  - остальные этапы: из этих же сделок, сгруппированные по текущему status_id
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone, timedelta

import requests

import config

logger = logging.getLogger(__name__)

_BASE_URL = f"https://{config.AMO_DOMAIN}"
_HEADERS = {
    "Authorization": f"Bearer {config.AMO_TOKEN}",
    "Content-Type": "application/json",
}

_MSK = timezone(timedelta(hours=3))


# ── Публичный интерфейс ───────────────────────────────────────────────────────


def get_daily_stats(target_date: date) -> dict[int, dict[str, int | float]]:
    """
    Возвращает статистику за день:
        {
            manager_id: {
                "hot_leads": 14,       # всего новых сделок за день
                "taken_to_work": 9,    # из них сейчас в статусе «Взят в работу»
                "data_received": 1,
                "kp_sent": 0,
                "agreed_count": 2,
                "agreed_sum": 149000,
                "confirmed_count": 0,
                "confirmed_sum": 0,
                "rejected": 0,
            },
            ...
        }
    """
    return _fetch_from_amo(target_date)


# ── Реализация ────────────────────────────────────────────────────────────────


def _fetch_from_amo(target_date: date) -> dict[int, dict[str, int | float]]:
    start_ts, end_ts = _day_range(target_date)

    leads = _fetch_leads_created(start_ts, end_ts)
    logger.info("Leads created today (%s): %d", target_date, len(leads))

    return _aggregate(leads)


def _day_range(target_date: date) -> tuple[int, int]:
    start = datetime(target_date.year, target_date.month, target_date.day,
                     0, 0, 0, tzinfo=_MSK)
    end   = datetime(target_date.year, target_date.month, target_date.day,
                     23, 59, 59, tzinfo=_MSK)
    return int(start.timestamp()), int(end.timestamp())


def _fetch_leads_created(from_ts: int, to_ts: int) -> list[dict]:
    """Постраничная загрузка сделок, созданных за день в нашей воронке."""
    all_leads: list[dict] = []
    page = 1

    while True:
        params = {
            "filter[created_at][from]": from_ts,
            "filter[created_at][to]":   to_ts,
            "filter[pipeline_id]":       config.PIPELINE_ID,
            "page":  page,
            "limit": 250,
        }
        resp = requests.get(
            f"{_BASE_URL}/api/v4/leads",
            headers=_HEADERS,
            params=params,
            timeout=30,
        )
        if resp.status_code == 204:
            break
        resp.raise_for_status()

        body = resp.json()
        page_leads: list[dict] = body.get("_embedded", {}).get("leads", [])
        if not page_leads:
            break

        all_leads.extend(page_leads)

        if not body.get("_links", {}).get("next"):
            break
        page += 1

    return all_leads


# ── Агрегация ─────────────────────────────────────────────────────────────────


def _aggregate(leads: list[dict]) -> dict[int, dict[str, int | float]]:
    # Инвертируем STATUS_IDS: status_id (str) → field_name
    # hot_leads не участвует — он считается как «все новые сделки»
    status_to_field: dict[str, str] = {}
    for field, status_id in config.STATUS_IDS.items():
        if status_id and field != "hot_leads":
            status_to_field[str(status_id)] = field

    sum_fields = {"agreed", "confirmed"}

    result: dict[int, dict[str, int | float]] = {
        mid: _empty_stats() for mid in config.MANAGER_IDS
    }

    for lead in leads:
        manager_id = lead.get("responsible_user_id", 0)
        if manager_id not in result:
            continue

        status_id = str(lead.get("status_id", ""))
        price     = float(lead.get("price", 0) or 0)

        # Горячие = все новые сделки за день (независимо от текущего статуса)
        result[manager_id]["hot_leads"] += 1

        # Текущий статус сделки
        field = status_to_field.get(status_id)
        if not field:
            continue

        result[manager_id][field] += 1

        base = field.replace("_count", "")
        if base in sum_fields:
            result[manager_id][f"{base}_sum"] += price

    return result


def _empty_stats() -> dict[str, int | float]:
    return {
        "hot_leads":       0,
        "taken_to_work":   0,
        "data_received":   0,
        "kp_sent":         0,
        "agreed_count":    0,
        "agreed_sum":      0.0,
        "confirmed_count": 0,
        "confirmed_sum":   0.0,
        "rejected":        0,
    }
