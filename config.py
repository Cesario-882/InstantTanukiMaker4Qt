from i18n import _
import json
import pathlib
from typing import Optional, Tuple

from PIL import Image
import numpy as np
from itertools import cycle
from collections.abc import Iterator

import const
from image_manager import ImageManager, FrameImage, FileImage, PartsImage
import editor


# ===== JSON 序列化键名 =====
JSON_TYPE = "_type"
JSON_VALUE = "value"
JSON_VERSION = "version"


class InstantEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ImageManager):
            return obj.to_json()
        if isinstance(obj, FrameImage):
            return obj.to_json()
        if isinstance(obj, (FileImage, PartsImage)):
            return {
                JSON_TYPE: type(obj).__name__,
                JSON_VALUE: self._convert_value(obj),
            }
        if isinstance(obj, np.ndarray):
            return {JSON_TYPE: "ndarray", JSON_VALUE: obj.tolist()}
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, Image.Image):
            return {JSON_TYPE: "Image", JSON_VALUE: editor.encode_image(obj)}
        if isinstance(obj, (pathlib.Path, cycle, Iterator)):
            return None
        return super().default(obj)

    @staticmethod
    def _convert_value(obj):
        return {
            key: {JSON_TYPE: "tuple", JSON_VALUE: val} if isinstance(val, tuple) else val
            for key, val in obj.__dict__.items()
        }


class InstantDecoder(json.JSONDecoder):
    _HANDLERS = {
        "ImageManager": None,   # 特殊，后面单独处理
        "FrameImage": None,
        "FileImage": None,
        "PartsImage": None,
        "Image": None,
        "ndarray": None,
        "tuple": None,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        if JSON_TYPE not in obj:
            return obj

        t = obj[JSON_TYPE]
        v = obj.get(JSON_VALUE)

        if t == ImageManager.__name__:
            manager = ImageManager(**v)
            manager.convert_id2img()
            return manager
        if t == FrameImage.__name__:
            return FrameImage(**v)
        if t == FileImage.__name__:
            return FileImage(**v)
        if t == PartsImage.__name__:
            return PartsImage(**v)
        if t == "Image":
            return editor.decode_image(v)
        if t == "ndarray":
            return np.array(v)
        if t == "tuple":
            return tuple(v)

        return obj


class Config:
    def __init__(self):
        self.manager = ImageManager()
        self.dir_dialog = None

    def save_manager(self, path_save: pathlib.Path):
        with open(path_save, "w", encoding="utf-8") as f:
            json.dump(self.manager, f, cls=InstantEncoder,
                      ensure_ascii=False, indent=4)

    def load_manager(self, path_json: pathlib.Path) -> Tuple[bool, str]:
        with open(path_json, "r", encoding="utf-8") as f:
            text = f.read()

        dic_json = json.loads(text)

        is_target, message = self.check_json(dic_json)
        if not is_target:
            return False, message

        self.manager = json.loads(text, cls=InstantDecoder)
        return True, _("読込が完了しました！")

    def check_json(self, dic_json: dict) -> Tuple[bool, str]:
        if dic_json.get(JSON_TYPE) != ImageManager.__name__:
            return False, _("たぬこらのプロジェクトファイルではありません！")

        version_json = dic_json.get(JSON_VALUE, {}).get(JSON_VERSION)
        if version_json is None:
            return False, _("プロジェクトファイルにバージョン情報がありません！")

        if self._compare_version(version_json, const.VERSION) > 0:
            return False, _("プロジェクトファイルのバージョンが今のアプリより新しいため読み込めません！\n"
                            "たぬこらのバージョンをあげてみて下さい！")

        return True, _("チェック完了")

    @staticmethod
    def _compare_version(v1: str, v2: str) -> int:
        """比较两个版本号。v1 > v2 返回正数，v1 < v2 返回负数，相等返回 0。"""
        p1 = [int(x) for x in v1.split(".")]
        p2 = [int(x) for x in v2.split(".")]
        n = max(len(p1), len(p2))
        p1 += [0] * (n - len(p1))
        p2 += [0] * (n - len(p2))
        return (p1 > p2) - (p1 < p2)


CONFIG = Config()
