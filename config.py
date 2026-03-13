"""
config.py — все константы и переменные окружения.
Реальные значения задаются в .env (см. .env.example).
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── amoCRM ────────────────────────────────────────────────────────────────────

AMO_DOMAIN: str = os.getenv("AMO_DOMAIN", "yourcompany.amocrm.ru")
AMO_TOKEN: str = os.getenv("AMO_TOKEN", "")
PIPELINE_ID: int = int(os.getenv("PIPELINE_ID", "0"))

# ID менеджеров из amoCRM (порядок определяет, какой блок в таблице чей)
_raw_ids = os.getenv("MANAGER_IDS", "")
MANAGER_IDS: list[int] = [int(x.strip()) for x in _raw_ids.split(",") if x.strip()]

# Отображаемые имена менеджеров для Telegram-отчёта.
# Заполни после получения доступа к CRM: {amoCRM_user_id: "Имя"}
MANAGER_NAMES: dict[int, str] = {
    9894862: "Алена Вихарева",
    8617441: "Виктория Удникова",
    12439510: "Екатерина Коковина",
}

# amoCRM status_id для каждого этапа воронки.
# Заполни после получения доступа к CRM.
STATUS_IDS: dict[str, str] = {
    "hot_leads":     os.getenv("STATUS_HOT_LEADS", ""),      # Горячие (входящее обращение)
    "taken_to_work": os.getenv("STATUS_TAKEN_TO_WORK", ""),  # Взят в работу
    "data_received": os.getenv("STATUS_DATA_RECEIVED", ""),  # Данные для КП получены
    "kp_sent":       os.getenv("STATUS_KP_SENT", ""),        # КП отправлено
    "agreed_count":  os.getenv("STATUS_AGREED", ""),         # Праздник согласован
    "confirmed_count": os.getenv("STATUS_CONFIRMED", ""),   # Праздник подтверждён
    "rejected":      os.getenv("STATUS_REJECTED", ""),       # Отказ
}

# ── Google Sheets ─────────────────────────────────────────────────────────────

SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID", "")

# Путь к JSON-ключу сервисного аккаунта Google (скачивается из Google Cloud Console)
GOOGLE_CREDENTIALS_FILE: str = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

# ── Структура таблицы ─────────────────────────────────────────────────────────

# Строка с заголовками дат (формат ячейки: "01.03 | пн").
# Строки 1-2 объединены — якорная ячейка мержа row 1, поэтому пишем в неё.
DATE_HEADER_ROW: int = 1

# Столбец, с которого начинаются даты в строке DATE_HEADER_ROW (1-indexed).
# 11 = столбец K (новый шаблон).
DATE_FIRST_COL: int = 11

# Столбец с именем менеджера (объединённая ячейка на весь блок, столбец B = 2)
MANAGER_NAME_COL: int = 2

# Строка, с которой начинается блок первого менеджера (1-indexed)
MANAGER_BLOCK_START_ROW: int = 3

# Количество строк на один блок менеджера (включая пустую строку-разделитель)
MANAGER_BLOCK_SIZE: int = 9

# Смещения строк внутри блока (от начала блока, 0-indexed).
# Скрипт пишет ТОЛЬКО в эти строки; формулы/заголовки не трогаем.
ROW_OFFSETS: dict[str, int] = {
    "hot_leads":       0,   # Горячие (Входящее обращение) — кол-во новых лидов
    "taken_to_work":   1,   # Взят в работу — кол-во сделок
    "data_received":   2,   # Данные для КП получены — кол-во
    "kp_sent":         3,   # КП отправлено — кол-во
    "agreed_count":    4,   # Праздник согласован — кол-во
    "agreed_sum":      5,   # На сумму (после согласован)
    "confirmed_count": 6,   # Праздник подтверждён — кол-во
    "confirmed_sum":   7,   # На сумму (после подтверждён)
}

# ── Telegram ──────────────────────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Список chat_id через запятую: "-100123456789,486797180"
_raw_chat_ids = os.getenv("TELEGRAM_CHAT_IDS", os.getenv("TELEGRAM_CHAT_ID", ""))
TELEGRAM_CHAT_IDS: list[str] = [x.strip() for x in _raw_chat_ids.split(",") if x.strip()]

# ID топиков (threads) для групповых чатов с форумом.
# Формат: "chat_id:topic_id,chat_id:topic_id"
# Пример: "-100123456789:42,-100987654321:7"
# Если для chat_id топик не указан — сообщение отправляется в общий чат.
_raw_topic_ids = os.getenv("TELEGRAM_TOPIC_IDS", "")
TELEGRAM_TOPIC_IDS: dict[str, int] = {}
for _entry in _raw_topic_ids.split(","):
    _entry = _entry.strip()
    if ":" in _entry:
        _cid, _tid = _entry.rsplit(":", 1)
        if _cid.strip() and _tid.strip():
            TELEGRAM_TOPIC_IDS[_cid.strip()] = int(_tid.strip())

# ── Вспомогательное ───────────────────────────────────────────────────────────

# Названия вкладок (месяц → название листа в таблице)
MONTH_NAMES_RU: dict[int, str] = {
    1: "Январь",   2: "Февраль",  3: "Март",
    4: "Апрель",   5: "Май",      6: "Июнь",
    7: "Июль",     8: "Август",   9: "Сентябрь",
    10: "Октябрь", 11: "Ноябрь",  12: "Декабрь",
}

# Название шаблонного листа, который копируется 1-го числа каждого месяца
TEMPLATE_SHEET_NAME: str = "_template"
