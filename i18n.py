import json
import os
import sys
import locale
import pathlib
import logging
from typing import Optional, Dict
from functools import lru_cache


_current: Dict[str, str] = {}
_current_lang: str = "en"
_uma_table: Dict[str, str] = {}
_tag_table: Dict[str, str] = {}


# ===== 回退链 =====
# 请求语言 → 依次尝试的加载顺序
# 空列表 = 不翻译（ja 源语言）
FALLBACK_CHAIN = {
    "zh_TW": ["zh_TW", "zh_CN", "en"],
    "zh_HK": ["zh_TW", "zh_CN", "en"],
    "zh_CN": ["zh_CN", "en"],
    "en":    ["en"],
    "ja":    [],
}


def _resolve_chain(lang: str) -> list:
    if lang in FALLBACK_CHAIN:
        return FALLBACK_CHAIN[lang]
    return [lang, "en"]


# ===== 路径 =====
def _find_locale_dir() -> pathlib.Path:
    if hasattr(sys, "_MEIPASS"):
        external = pathlib.Path(sys.executable).resolve().parent / "locale"
        internal = pathlib.Path(sys._MEIPASS) / "locale"
    else:
        external = pathlib.Path(__file__).resolve().parent / "locale"
        internal = external
    return external if external.exists() else internal


LOCALE_DIR = str(_find_locale_dir())


# ===== 系统语言 =====
def get_system_language() -> str:
    try:
        lang_env = (os.environ.get('LANG', '')
                    or os.environ.get('LC_ALL', '')
                    or os.environ.get('LC_MESSAGES', ''))
        if lang_env:
            lang_code = lang_env.split('.')[0]
        else:
            lang_code = locale.getdefaultlocale()[0] or 'en'
    except Exception:
        lang_code = 'en'

    if not lang_code:
        return 'en'
    if lang_code.startswith('zh'):
        if any(p in lang_code for p in ('TW', 'HK', 'MO', 'Hant')):
            return 'zh_TW'
        return 'zh_CN'
    if lang_code.startswith('ja'):
        return 'ja'
    return 'en'


# ===== 加载 =====
def _load_json_table(path: str) -> Dict[str, str]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logging.warning(f"Failed to load {path}: {e}")
        return {}


def _load_by_chain(chain: list, *subdirs: str) -> Dict[str, str]:
    """按回退链找第一个非空文件。subdirs 是 locale 下的子目录，如 ('uma',)"""
    for try_lang in chain:
        path = os.path.join(LOCALE_DIR, *subdirs, f"{try_lang}.json")
        data = _load_json_table(path)
        if data:
            return data
    return {}


def load_language(lang: Optional[str] = None) -> bool:
    global _current, _current_lang, _uma_table, _tag_table

    if lang is None:
        lang = get_system_language()

    _current_lang = lang

    # ja：源语言，不翻译
    if lang == 'ja':
        _current = {}
        _uma_table = {}
        _tag_table = {}
        return True

    chain = _resolve_chain(lang)

    _current = _load_by_chain(chain)
    _uma_table = _load_by_chain(chain, "uma")
    _tag_table = _load_by_chain(chain, "tag")

    if 'display' in globals():
        display.cache_clear()

    return bool(_current)


# ===== 查询 =====
def _(text: str, **kwargs) -> str:
    """UI 文案"""
    result = _current.get(text, text)
    if kwargs:
        try:
            result = result.format(**kwargs)
        except (KeyError, ValueError):
            logging.warning(f"i18n format failed: {text!r} with {kwargs}")
    return result


def uma(jp_name: str) -> str:
    """马名。找不到返回原文。"""
    return _uma_table.get(jp_name, jp_name)


def tag(jp_name: str) -> str:
    """标签/分类。找不到返回原文。"""
    return _tag_table.get(jp_name, jp_name)


def _clean_translation(s: str) -> str:
    """清理翻译值：去掉尾部 * °，斜杠取第一个。"""
    if not s:
        return s
    s = s.rstrip('*°')
    if '/' in s:
        s = s.split('/')[0]
    return s

def _translate_suffix(rest: str) -> str:
    """翻译后缀：反复匹配表里最长的前缀，替换后继续，直到无匹配。
    用于 stem 里名字后面的部件/状态词，如 顔無し、[頭]垂れ耳。
    """
    if not rest:
        return rest
    result = []
    while rest:
        best = None
        for table in (_current, _tag_table):
            for key, val in table.items():
                if rest.startswith(key):
                    if best is None or len(key) > best[0]:
                        best = (len(key), key, val)
        if best is None:
            result.append(rest[0])
            rest = rest[1:]
        else:
            _, key, val = best
            result.append(_clean_translation(val))
            rest = rest[len(key):]
    return ''.join(result)


@lru_cache(maxsize=4096)
def display(jp_text: str) -> str:
    """级联查询：马名 → 标签 → UI 文案 → 最长前缀匹配 → 原文。
    用于 stem 这种类型不确定的输入（可能带【F1】等程序后缀）。"""
    # 1. 精确匹配
    for table in (_uma_table, _tag_table, _current):
        if jp_text in table:
            return _clean_translation(table[jp_text])

    # 2. 最长前缀匹配
    best = None
    for table in (_uma_table, _tag_table, _current):
        for key, val in table.items():
            if len(key) < len(jp_text) and jp_text.startswith(key):
                if best is None or len(key) > best[0]:
                    best = (len(key), key, val)

    if best is not None:
        _, key, val = best
        rest = jp_text[len(key):]
        return _clean_translation(val) + _translate_suffix(rest)

    # 3. 整个字符串尝试后缀翻译（比如 stem 本身就是部件名）
    translated = _translate_suffix(jp_text)
    if translated != jp_text:
        return translated

    # 4. 回落原文
    return jp_text


# ===== 辅助 =====
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
