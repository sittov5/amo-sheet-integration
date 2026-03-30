"""
amo.py — работа с amoCRM API v4.

Логика подсчёта:
  - hot_leads      : сделки СОЗДАННЫЕ за день
                     (дата создания = дата входа в первый этап для новых сделок)
  - остальные этапы: сделки, которые ПЕРЕШЛИ в этот этап за день
                     (по событиям API lead_status_changed)
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone, timedelta
from itertools import islice

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
                "hot_leads": 14,       # сделки СОЗДАННЫЕ за день
                "taken_to_work": 9,    # сделки, ПЕРЕШЕДШИЕ в этот этап за день
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

    # hot_leads: сделки СОЗДАННЫЕ за день
    created_leads = _fetch_leads_created(start_ts, end_ts)
    logger.info("Leads created today (%s): %d", target_date, len(created_leads))

    # Остальные этапы: сделки, ПЕРЕШЕДШИЕ в этап за день (через API событий)
    stage_changes = _fetch_stage_changes(start_ts, end_ts)
    logger.info("Stage change events today (%s): %d", target_date, len(stage_changes))

    return _aggregate(created_leads, stage_changes)


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


# ── События смены этапа ───────────────────────────────────────────────────────


def _fetch_stage_changes(from_ts: int, to_ts: int) -> list[dict]:
    """
    Возвращает список переходов этапа за день в нашей воронке:
        [{"manager_id": X, "status_id": Y, "price": Z}, ...]
    Каждый элемент — одно событие (сделка может войти в список несколько раз,
    если за день перешла через несколько этапов).
    """
    raw_events = _fetch_raw_status_events(from_ts, to_ts)
    if not raw_events:
        return []

    # Уникальные ID сделок из событий
    lead_ids = list({e["entity_id"] for e in raw_events})

    # Детали сделок: ответственный, цена, pipeline_id
    leads_by_id = _fetch_leads_by_ids(lead_ids)

    result = []
    for event in raw_events:
        lead_id = event["entity_id"]
        lead = leads_by_id.get(lead_id)
        if not lead:
            continue

        # Только наша воронка
        if lead.get("pipeline_id") != config.PIPELINE_ID:
            continue

        new_status_id = _extract_new_status_id(event)
        if new_status_id is None:
            continue

        result.append({
            "manager_id": lead.get("responsible_user_id"),
            "status_id":  new_status_id,
            "price":      float(lead.get("price", 0) or 0),
        })

    return result


def _fetch_raw_status_events(from_ts: int, to_ts: int) -> list[dict]:
    """Постраничная загрузка событий смены этапа за день."""
    all_events: list[dict] = []
    page = 1

    while True:
        params = {
            "filter[entity][]":         "leads",
            "filter[type][]":           "lead_status_changed",
            "filter[created_at][from]": from_ts,
            "filter[created_at][to]":   to_ts,
            "page":  page,
            "limit": 100,
        }
        resp = requests.get(
            f"{_BASE_URL}/api/v4/events",
            headers=_HEADERS,
            params=params,
            timeout=30,
        )
        if resp.status_code == 204:
            break
        resp.raise_for_status()

        body = resp.json()
        page_events: list[dict] = body.get("_embedded", {}).get("events", [])
        if not page_events:
            break

        all_events.extend(page_events)

        if not body.get("_links", {}).get("next"):
            break
        page += 1

    return all_events


def _extract_new_status_id(event: dict) -> int | None:
    """Извлекает новый status_id из события смены этапа.

    amoCRM возвращает value_after как список:
      [{"lead_status": {"id": 41295151, "pipeline_id": 5678}}]
    """
    value_after = event.get("value_after", [])
    if isinstance(value_after, list):
        for item in value_after:
            status_info = item.get("lead_status")
            if status_info:
                return status_info.get("id")
    elif isinstance(value_after, dict):
        status_info = value_after.get("lead_status")
        if status_info:
            return status_info.get("id")
    return None


def _fetch_leads_by_ids(lead_ids: list[int]) -> dict[int, dict]:
    """Загружает сделки по списку ID батчами, возвращает {lead_id: lead_dict}."""
    result: dict[int, dict] = {}

    for batch in _batched(lead_ids, 100):
        # amoCRM принимает filter[id][]=X&filter[id][]=Y
        params: list[tuple[str, int]] = [("filter[id][]", lid) for lid in batch]
        params.append(("limit", 250))

        resp = requests.get(
            f"{_BASE_URL}/api/v4/leads",
            headers=_HEADERS,
            params=params,
            timeout=30,
        )
        if resp.status_code == 204:
            continue
        resp.raise_for_status()

        for lead in resp.json().get("_embedded", {}).get("leads", []):
            result[lead["id"]] = lead

    return result


def _batched(iterable, n: int):
    """Разбивает список на батчи размером n."""
    it = iter(iterable)
    while chunk := list(islice(it, n)):
        yield chunk


# ── Агрегация ─────────────────────────────────────────────────────────────────


def _aggregate(
    created_leads: list[dict],
    stage_changes: list[dict],
) -> dict[int, dict[str, int | float]]:
    # Инвертируем STATUS_IDS: status_id (str) → field_name
    # hot_leads не участвует — он считается по created_leads
    status_to_field: dict[str, str] = {}
    for field, status_id in config.STATUS_IDS.items():
        if status_id and field != "hot_leads":
            status_to_field[str(status_id)] = field

    sum_fields = {"agreed", "confirmed"}

    result: dict[int, dict[str, int | float]] = {
        mid: _empty_stats() for mid in config.MANAGER_IDS
    }

    # hot_leads: сделки СОЗДАННЫЕ за день
    for lead in created_leads:
        manager_id = lead.get("responsible_user_id", 0)
        if manager_id not in result:
            continue
        result[manager_id]["hot_leads"] += 1

    # Остальные этапы: по дате перехода в этап
    for change in stage_changes:
        manager_id = change.get("manager_id", 0)
        if manager_id not in result:
            continue

        field = status_to_field.get(str(change["status_id"]))
        if not field:
            continue

        result[manager_id][field] += 1

        base = field.replace("_count", "")
        if base in sum_fields:
            result[manager_id][f"{base}_sum"] += change["price"]

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
