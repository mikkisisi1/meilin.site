"""
Регрессионный тест: LLM не должен «проговаривать» в тексте ответа
маркеры эмоций Fish Audio (`(calm)`, `(soft tone)`, `(warm)(gentle)`,
`(sighing)`, `(thoughtful)` и т.п.). `strip_emotion_markers()` из
`routes/chat.py` вырезает их из видимого текста, не задевая легитимные
вставки в скобках (русские слова, имена с заглавной буквы и т.д.).
"""
import os

# Motor импортирует MONGO_URL на уровне модуля — подставим минимум для импорта.
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest

from routes.chat_helpers import strip_emotion_markers


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Базовые Fish Audio маркеры в начале
        ("(calm)(soft tone) Я слышу тебя. Это тяжело.",
         "Я слышу тебя. Это тяжело."),
        ("(warm)(gentle) Хм... понимаю.",
         "Хм... понимаю."),
        # Маркер внутри предложения
        ("Текст (sighing) с паузой.",
         "Текст с паузой."),
        ("Вопрос (thoughtful): что ты чувствуешь?",
         "Вопрос: что ты чувствуешь?"),
        # Несколько маркеров подряд
        ("(soft tone)  (thoughtful) Давай подумаем.",
         "Давай подумаем."),
        # Обычный текст без маркеров — не трогаем
        ("Обычный текст без маркеров.",
         "Обычный текст без маркеров."),
        # Русские слова в скобках — сохраняем (не ASCII-маркер)
        ("(calm) Привет, (Иван)! Как ты?",
         "Привет, (Иван)! Как ты?"),
        # Пусто/None-safe
        ("", ""),
    ],
)
def test_strip_emotion_markers(raw, expected):
    assert strip_emotion_markers(raw) == expected


def test_none_input_is_safe():
    assert strip_emotion_markers(None) is None


def test_does_not_eat_legitimate_parenthetical():
    """Скобки с цифрами/заглавными/многословными фразами не считаются TTS-маркером."""
    text = "Позвони по номеру 8-800-2000-122 (бесплатный телефон доверия)."
    # «бесплатный телефон доверия» — кириллица, regex её не трогает
    assert "(бесплатный телефон доверия)" in strip_emotion_markers(text)
