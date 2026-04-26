"""
🔒 ЗАЩИЩЁННЫЙ КОНФИГ ГОЛОСОВЫХ НАСТРОЕК FISH AUDIO 🔒

⚠️ КРИТИЧНО: НЕ ИЗМЕНЯТЬ БЕЗ СОГЛАСОВАНИЯ ⚠️
Эти параметры оптимизированы для психологической консультации.
Любые изменения могут сломать эмпатичную манеру речи агентов.

ЗАПРЕЩЕНО ИЗМЕНЯТЬ:
- Voice IDs (Leon и Kylie)
- Prosody параметры (speed, volume)
- Эмоциональные маркеры
- Правила очистки текста
"""

import os

# ========== FISH AUDIO API ==========
# 🔒 НЕ ИЗМЕНЯТЬ: API ключ из переменных окружения
FISH_API_KEY = os.environ.get("FISH_AUDIO_API_KEY", "")

# ========== FISH AUDIO BACKEND MODEL ==========
# 🔒 КРИТИЧНО: S2-Pro — флагман Fish Audio на 2026 (#1 в blind-тестах, BT 3.07).
# Поддерживает натурально-языковой emotion control через [bracket]-синтаксис.
# Предыдущие: s1 (архив), s1-mini (open-source), speech-1.5 (устарела).
FISH_BACKEND = os.environ.get("FISH_BACKEND", "s2-pro")

# Latency mode: "balanced" (~300ms TTFB) для стриминга / "normal" (~500ms, выше качество).
FISH_LATENCY = os.environ.get("FISH_LATENCY", "balanced")

# ========== ГОЛОСА АГЕНТОВ ==========
# 🔒 НЕ ИЗМЕНЯТЬ: ID референсных голосов для агентов
VOICE_IDS = {
    "male": os.environ.get("FISH_VOICE_MALE", "d9247a00779649adbe7f4fdde2ac11c8"),      # Leon (Brad Pitt)
    "female": os.environ.get("FISH_VOICE_FEMALE", "7a98513e3a7d439682fa68f8d4da34c0"),  # Kylie (женский)
}

# ========== PROSODY НАСТРОЙКИ ==========
# 🔒 НЕ ИЗМЕНЯТЬ: Оптимизировано для профессионального, спокойного психолога
PROSODY_CONFIG = {
    "speed": 0.92,          # Живой темп с лёгким замедлением для вдумчивости (−8% от нормы)
    "volume": 4,            # Комфортная громкость (диапазон: -20 до 20)
}

# ========== ЭМОЦИОНАЛЬНЫЕ МАРКЕРЫ (S2-Pro [bracket] синтаксис) ==========
# 🔒 НЕ ИЗМЕНЯТЬ: Базовая эмоциональная настройка — «профессиональный / внимательный / уверенный / спокойный / живой»
# S2-Pro интерпретирует натурально-языковые теги в квадратных скобках прямо внутри текста.
EMOTION_MARKERS = {
    "base": "[calm][professional][attentive][warm]",  # Спокойный, профессиональный, внимательный, тёплый
    "empathy": "[warm][gentle]",           # (Зарезервировано, сейчас не применяется)
    "thoughtful": "[thoughtful]",          # (Зарезервировано, сейчас не применяется)
    "pause": "[sighing]",                  # (Зарезервировано, сейчас не применяется)
}

# ========== ПРАВИЛА ОЧИСТКИ ТЕКСТА ==========
# 🔒 НЕ ИЗМЕНЯТЬ: Регулярные выражения для подготовки текста к TTS
# Удаляются только элементы, которые ломают озвучку (markdown, списки, и т.д.)
TEXT_CLEANUP_RULES = {
    "remove_markdown": True,        # Убрать *, #, _, ~, `, >
    "remove_numbering": True,       # Убрать нумерацию списков (1., 2., и т.д.)
    "remove_emotion_prefixes": True,  # Убрать префиксы типа "Нежно,", "Мягко,"
    "normalize_newlines": True,     # Убрать лишние переносы строк
}

# ========== МАКСИМАЛЬНАЯ ДЛИНА ТЕКСТА ==========
# 🔒 НЕ ИЗМЕНЯТЬ: Ограничение для стабильной озвучки
MAX_TTS_LENGTH = 1000  # символов (Fish Audio рекомендует до 1000 для стриминга)


def get_emotion_prefix(context: str = "base") -> str:
    """
    Получить эмоциональный префикс для текста.
    
    Args:
        context: Тип контекста ("base", "empathy", "thoughtful", "pause")
    
    Returns:
        Строка с эмоциональными маркерами
    
    🔒 НЕ ИЗМЕНЯТЬ ЭТУ ФУНКЦИЮ
    """
    return EMOTION_MARKERS.get(context, EMOTION_MARKERS["base"])


def validate_voice_id(voice: str) -> str:
    """
    Валидация и получение Voice ID.

    Args:
        voice: "male" или "female"

    Returns:
        Voice ID для Fish Audio API

    🔒 НЕ ИЗМЕНЯТЬ ЭТУ ФУНКЦИЮ

    ⚠️ STRICT: голоса агентов НЕ должны пересекаться. Если voice неизвестен —
    бросаем исключение, чтобы Leon никогда случайно не заговорил голосом Kylie
    (и наоборот). Любой silent fallback ломает иллюзию разных персонажей.
    """
    if voice not in VOICE_IDS:
        raise ValueError(f"Invalid voice='{voice}'. Expected one of: {list(VOICE_IDS.keys())}")
    return VOICE_IDS[voice]
