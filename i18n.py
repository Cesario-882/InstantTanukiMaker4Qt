import json
import os
import sys
import locale
import pathlib
from typing import Optional, Dict

_current: Dict[str, str] = {}
_current_lang: str = "en"


def _find_locale_dir() -> pathlib.Path:
    """locale 目录：外部（用户自备），内部兜底"""
    if hasattr(sys, "_MEIPASS"):
        external = pathlib.Path(sys.executable).resolve().parent / "locale"
        internal = pathlib.Path(sys._MEIPASS) / "locale"
    else:
        external = pathlib.Path(__file__).resolve().parent / "locale"
        internal = external

    if external.exists():
        return external
    return internal


LOCALE_DIR = str(_find_locale_dir())


def get_system_language() -> str:
    try:
        lang_env = os.environ.get('LANG', '') or os.environ.get('LC_ALL', '') or os.environ.get('LC_MESSAGES', '')
        if lang_env:
            lang_code = lang_env.split('.')[0]
        else:
            lang_code = locale.getdefaultlocale()[0] or 'en'
    except Exception:
        lang_code = 'en'

    if not lang_code:
        return 'en'
    if lang_code.startswith('zh'):
        return 'zh_CN'
    if lang_code.startswith('ja'):
        return 'ja'
    return 'en'


def load_language(lang: Optional[str] = None) -> bool:
    global _current, _current_lang

    if lang is None:
        lang = get_system_language()

    _current_lang = lang

    # 日语：空字典，显示源文本
    if lang == 'ja':
        _current = {}
        return True

    # 尝试加载对应语言的 json
    path = os.path.join(LOCALE_DIR, f"{lang}.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                _current = json.load(f)
            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load locale {lang}: {e}")

    # 尝试 fallback 到 en
    fallback_path = os.path.join(LOCALE_DIR, "en.json")
    if os.path.exists(fallback_path):
        try:
            with open(fallback_path, "r", encoding="utf-8") as f:
                _current = json.load(f)
            _current_lang = "en"
            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load fallback locale: {e}")

    # 都没有，空字典（显示日文源文本）
    _current = {}
    _current_lang = "en"
    return False


def _(text: str, **kwargs) -> str:
    result = _current.get(text, text)
    if kwargs:
        try:
            result = result.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return result


def get_current_language() -> str:
    return _current_lang


def get_all_keys() -> list:
    return list(_current.keys())


def reload_language() -> bool:
    return load_language(_current_lang)


def has_key(key: str) -> bool:
    return key in _current


def add_translation(key: str, value: str) -> None:
    _current[key] = value


load_language()
