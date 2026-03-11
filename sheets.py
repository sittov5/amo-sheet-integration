"""
sheets.py — работа с Google Sheets через gspread.

Ключевые функции:
  - copy_template_if_needed(date)  — копирует _template если листа месяца ещё нет
  - write_daily_data(data, date)   — записывает данные за день в нужный столбец
  - find_date_column(ws, date)     — находит столбец по дате в строке заголовков
"""

from __future__ import annotations

import calendar
import logging
from datetime import date

import gspread
from google.oauth2.service_account import Credentials

import config

logger = logging.getLogger(__name__)

# OAuth-скоупы: читаем/пишем Sheets, Drive нужен для дублирования листа
_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Кеш клиента и таблицы — инициализируются один раз при первом обращении
_client: gspread.Client | None = None
_spreadsheet: gspread.Spreadsheet | None = None


def _get_spreadsheet() -> gspread.Spreadsheet:
    """Возвращает объект таблицы (singleton с ленивой инициализацией)."""
    global _client, _spreadsheet
    if _spreadsheet is None:
        creds = Credentials.from_service_account_file(
            config.GOOGLE_CREDENTIALS_FILE, scopes=_SCOPES
        )
        _client = gspread.authorize(creds)
        _spreadsheet = _client.open_by_key(config.SPREADSHEET_ID)
        logger.info("Connected to spreadsheet: %s", _spreadsheet.title)
    return _spreadsheet


# ── Работа с листами ──────────────────────────────────────────────────────────


_WEEKDAYS_RU = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


def _sheet_exists(spreadsheet: gspread.Spreadsheet, name: str) -> bool:
    return any(ws.title == name for ws in spreadsheet.worksheets())


def _date_to_col(target_date: date) -> int:
    """
    Вычисляет номер столбца для конкретной даты (1-indexed).
    Столбец = DATE_FIRST_COL + (день_месяца - 1).
    Например: 1-е → col 12, 2-е → col 13, …, 31-е → col 42.
    Не зависит от дня недели и разделителей.
    """
    return config.DATE_FIRST_COL + (target_date.day - 1)


def _populate_date_headers(worksheet: gspread.Worksheet, year: int, month: int) -> None:
    """
    Заполняет строку DATE_HEADER_ROW заголовками вида «01.03 | вс».
    Один столбец = один день: 1-е … последний день месяца.
    """
    days_in_month = calendar.monthrange(year, month)[1]
    row_values = []
    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        row_values.append(f"{d.strftime('%d.%m')} | {_WEEKDAYS_RU[d.weekday()]}")

    from gspread.utils import rowcol_to_a1
    start_a1 = rowcol_to_a1(config.DATE_HEADER_ROW, config.DATE_FIRST_COL)
    end_a1   = rowcol_to_a1(config.DATE_HEADER_ROW, config.DATE_FIRST_COL + days_in_month - 1)
    worksheet.update(f"{start_a1}:{end_a1}", [row_values], value_input_option="USER_ENTERED")

    logger.info(
        "Populated %d date headers for %02d/%d (%s:%s).",
        days_in_month, month, year, start_a1, end_a1,
    )


def _month_sheet_name(target_date: date) -> str:
    """Возвращает название листа с годом: «Март 2026», «Март 2027» и т.д."""
    return f"{config.MONTH_NAMES_RU[target_date.month]} {target_date.year}"


def copy_template_if_needed(target_date: date) -> None:
    """
    Копирует _template под именем текущего месяца+года (например, «Март 2026»),
    если такого листа ещё нет. Работает в любой день месяца.
    """
    sheet_name = _month_sheet_name(target_date)
    spreadsheet = _get_spreadsheet()

    if _sheet_exists(spreadsheet, sheet_name):
        logger.info("Sheet '%s' already exists, skipping template copy.", sheet_name)
        return

    template_ws = spreadsheet.worksheet(config.TEMPLATE_SHEET_NAME)
    new_ws = spreadsheet.duplicate_sheet(
        source_sheet_id=template_ws.id,
        insert_sheet_index=len(spreadsheet.worksheets()),
        new_sheet_name=sheet_name,
    )
    logger.info("Created new sheet '%s' from template.", sheet_name)

    # Сразу заполняем заголовки дат — без этого скрипт не найдёт нужный столбец
    _populate_date_headers(new_ws, target_date.year, target_date.month)


def get_month_sheet(target_date: date) -> gspread.Worksheet:
    """
    Возвращает лист для указанного месяца+года.
    Если лист не найден — выбрасывает исключение с понятным сообщением.
    """
    sheet_name = _month_sheet_name(target_date)
    spreadsheet = _get_spreadsheet()

    if not _sheet_exists(spreadsheet, sheet_name):
        raise ValueError(
            f"Sheet '{sheet_name}' not found in spreadsheet. "
            "Run copy_template_if_needed() first, or create the sheet manually."
        )
    return spreadsheet.worksheet(sheet_name)


# ── Поиск столбца по дате ─────────────────────────────────────────────────────


def find_date_column(worksheet: gspread.Worksheet, target_date: date) -> int | None:
    """
    Вычисляет номер столбца для даты математически (не читает лист).
    Использует DATE_FIRST_COL и WEEK_COL_SPAN из config.
    """
    col = _date_to_col(target_date)
    logger.debug("Date %s → col %d (DATE_FIRST_COL=%d)", target_date, col, config.DATE_FIRST_COL)
    return col


# ── Запись данных ─────────────────────────────────────────────────────────────


def _build_cells(
    manager_index: int,
    manager_data: dict[str, int | float],
    date_col: int,
) -> list[gspread.Cell]:
    """
    Формирует список объектов Cell для одного менеджера.
    manager_index: 0-based порядковый номер менеджера в списке MANAGER_IDS.
    """
    block_start_row = (
        config.MANAGER_BLOCK_START_ROW + manager_index * config.MANAGER_BLOCK_SIZE
    )
    cells = []
    for field, offset in config.ROW_OFFSETS.items():
        row = block_start_row + offset
        value = manager_data.get(field, 0)
        cells.append(gspread.Cell(row=row, col=date_col, value=value))
    return cells


def write_daily_data(
    all_managers_data: dict[int, dict[str, int | float]],
    target_date: date,
) -> None:
    """
    Главная точка записи: пишет данные всех менеджеров за день в таблицу.

    all_managers_data — словарь вида:
        {
            manager_id (int): {
                "hot_leads": 5,
                "taken_to_work": 5,
                "data_received": 3,
                "kp_sent": 3,
                "agreed_count": 3,
                "agreed_sum": 70000,
                "confirmed_count": 1,
                "confirmed_sum": 55000,
            },
            ...
        }
    """
    copy_template_if_needed(target_date)

    worksheet = get_month_sheet(target_date)

    # Проверяем, есть ли подпись даты в нужном столбце строки 8.
    # Если нет — заполняем заголовки (лист мог быть создан без них).
    date_col = find_date_column(worksheet, target_date)
    header_cell = worksheet.cell(config.DATE_HEADER_ROW, date_col).value
    if not header_cell:
        logger.info("Date header missing in row %d col %d — populating…", config.DATE_HEADER_ROW, date_col)
        _populate_date_headers(worksheet, target_date.year, target_date.month)

    if date_col is None:
        raise ValueError(
            f"Cannot write data: column for {target_date.strftime('%d.%m.%Y')} "
            f"could not be calculated. Check DATE_FIRST_COL={config.DATE_FIRST_COL} in config.py."
        )

    all_cells: list[gspread.Cell] = []

    for manager_index, manager_id in enumerate(config.MANAGER_IDS):
        manager_data = all_managers_data.get(manager_id, {})
        if not manager_data:
            logger.warning(
                "No data for manager_id=%d (index %d), writing zeros.",
                manager_id, manager_index,
            )
        cells = _build_cells(manager_index, manager_data, date_col)
        all_cells.extend(cells)

        # Имя менеджера в объединённой ячейке столбца A
        name = config.MANAGER_NAMES.get(manager_id, f"Менеджер {manager_index + 1}")
        block_start_row = config.MANAGER_BLOCK_START_ROW + manager_index * config.MANAGER_BLOCK_SIZE
        all_cells.append(gspread.Cell(row=block_start_row, col=config.MANAGER_NAME_COL, value=name))

    if all_cells:
        # Один batched API-запрос вместо N отдельных
        worksheet.update_cells(all_cells, value_input_option="USER_ENTERED")
        logger.info(
            "Written %d cells for %s (col %d).",
            len(all_cells), target_date.isoformat(), date_col,
        )
