# Copyright (C) 2026 Cesario-882
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json
import os
import sys
import pathlib
import logging
from typing import Optional, Dict
from functools import lru_cache
from PySide6.QtCore import QLocale


_current: Dict[str, str] = {}
_current_lang: str = "en"
_uma_table: Dict[str, str] = {}
_tag_table: Dict[str, str] = {}
_alias_table: Dict[str, str] = {}


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
    """locale 目录：仅外置，与可执行文件（或脚本）同级"""
    if hasattr(sys, "_MEIPASS") or "__compiled__" in globals():
        # 打包后（PyInstaller / Nuitka）：exe 所在目录
        return pathlib.Path(sys.executable).resolve().parent / "locale"
    # 开发环境：脚本所在目录
    return pathlib.Path(__file__).resolve().parent / "locale"


LOCALE_DIR = _find_locale_dir()


# ===== 系统语言 =====
def get_system_language() -> str:
    """使用 Qt 底层获取系统语言，彻底解决 Windows 下 Python locale 识别抽风的问题"""
    try:
        # 只要 import 了 QtCore，即使没创建 QApplication，QLocale.system() 也会去读系统底层 API
        sys_locale = QLocale.system()
        lang_name = sys_locale.name()  # 返回格式如 "zh_CN", "en_US", "ja_JP"

        if lang_name.startswith('zh'):
            if any(p in lang_name for p in ('TW', 'HK', 'MO')):
                return 'zh_TW'
            return 'zh_CN'
        if lang_name.startswith('ja'):
            return 'ja'
    except Exception:
        pass

    # 只有在 Qt 拿不到的时候，才用原生的兜底
    try:
        import locale
        lang_code = locale.getlocale()[0] or 'en'
        if lang_code.startswith('zh'):
            return 'zh_CN'
        if lang_code.startswith('ja'):
            return 'ja'
    except Exception:
        pass

    return 'en'


# ===== 加载 =====
def _load_json_table(path: pathlib.Path) -> Dict[str, str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError) as e:
        logging.warning(f"Failed to load {path}: {e}")
        return {}


def _load_by_chain(chain: list, *subdirs: str) -> Dict[str, str]:
    """按回退链找第一个非空文件。subdirs 是 locale 下的子目录，如 ('uma',)"""
    for try_lang in chain:
        path = LOCALE_DIR.joinpath(*subdirs, f"{try_lang}.json")
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

def get_alias_table() -> Dict[str, str]:
    """目录名映射表包含于（locale/zh_CN.json），仅中文用户有内容"""
    return dict(_current)

def get_all_keys() -> list:
    return list(_current.keys())


def reload_language() -> bool:
    return load_language(_current_lang)


def has_key(key: str) -> bool:
    return key in _current


def add_translation(key: str, value: str) -> None:
    _current[key] = value
