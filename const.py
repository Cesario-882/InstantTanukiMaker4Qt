import sys
import pathlib
from dataclasses import dataclass, fields
from PIL import Image
import numpy as np

from PySide6.QtGui import QImage, QFontDatabase


VERSION = "3.0.0"

# ===== 图像逻辑尺寸（影响合成结果，不要为了 UI 随便改）=====
DEFAULT_SIZE = (500, 500)
MAX_SIZE = (1500, 1500)
MIN_SIZE = (100, 100)
DEFAULT_WIDTH, DEFAULT_HEIGHT = DEFAULT_SIZE
MAX_WIDTH, MAX_HEIGHT = MAX_SIZE
MIN_WIDTH, MIN_HEIGHT = MIN_SIZE

# ===== 缩略图 / 图标尺寸（UI 用，可以按屏幕调小）=====
ICON_SIZE = (80, 80)
THUMB_SIZE = (64, 64)
THUMB_MINI_SIZE = (63, 63)

# ===== 窗口尺寸（768p 屏幕适配）=====
# 1366x768 的可用高度约 720，宽度约 1346
WINDOW_DEFAULT_WIDTH = 1200
WINDOW_DEFAULT_HEIGHT = 700
WINDOW_MARGIN = 20

# ===== プロパティパネル色 =====
COLOR_FILE = (200, 230, 200)
COLOR_PARTS = (200, 200, 250)
COLOR_NONE = (200, 200, 200)

# ===== フレーム数表示 =====
DISPLAY_FONT_SINGLE_SIZE = 20
DISPLAY_FONT_DOUBLE_SIZE = 14
DISPLAY_BBOX = (19, 53, 67, 84)


# ===== ImageType =====
@dataclass
class ImageType:
    BASE: str = "素体"
    TRANSPARENT: str = "素体透過"
    COSTUME: str = "きぐるみ"
    FACE: str = "表情"
    BROWS: str = "眉"
    EYES: str = "目"
    MOUTH: str = "口"
    ACCESSORY: str = "アクセサリ"
    COLLAGE: str = "パーツ"
    FREE: str = "フリー"
    ETC: str = "その他"


TYPES_IMAGE = [field.default for field in fields(ImageType)]
TYPES_REPLACE = [ImageType.BASE, ImageType.COSTUME,
                 ImageType.FACE, ImageType.BROWS, ImageType.EYES, ImageType.MOUTH]

KEYWORD_TRANSPARENT = "【透過】"
KEYWORDS_SEPARATE = ["[腕と手]", "[ばらばら]"]

TYPES_BASE = [ImageType.BASE, ImageType.TRANSPARENT, ImageType.COLLAGE]
DIC_BASE_OFFSET = {"イナリワン": np.array((-25, 0)),
                   "ライスシャワー": np.array((0, 25)),
                   "マーベラスサンデー": np.array((-11, 0))}

OFFSET_FLAT = np.array([0, 0])


# ===== BlendMode =====
@dataclass
class BlendMode:
    MULTIPLY: str = "乗算"
    SCREEN: str = "スクリーン"
    OVERLAY: str = "オーバーレイ"
    ALPHA: str = "アルファ"
    NONE: str = "なし"


MODES_BLEND = [field.default for field in fields(BlendMode)]


# ===== ImageFilter =====
@dataclass
class ImageFilter:
    LINE: str = "鉛筆風"
    COLORING: str = "塗り絵"
    DOT: str = "ドット"
    MOCHI: str = "もちもち"
    NONE: str = "なし"


FILTERS_IMAGE = [field.default for field in fields(ImageFilter)]


# ===== ColorFilter =====
@dataclass
class ColorFilter:
    MONO: str = "モノクロ"
    ASH: str = "灰"
    GAMING: str = "ゲーミング"
    NONE: str = "なし"


FILTERS_COLOR = [field.default for field in fields(ColorFilter)]


# ===== SaveMode =====
@dataclass
class SaveMode:
    GIF: str = "GIF"
    PNG_SEQUENCE: str = "連番PNG"
    PNG_ANIME: str = "APNG"


MODES_SAVE = [field.default for field in fields(SaveMode)]
THRESHOLD_CONVERT_SINGLE = 0.25


# ===== フォルダパス =====

def _find_base_dir():
    """程序内部资源目录（打包后为 _MEIPASS，开发时为脚本目录）"""
    if hasattr(sys, "_MEIPASS"):
        return pathlib.Path(sys._MEIPASS)
    return pathlib.Path(__file__).resolve().parent


def _find_external_dir():
    """程序外部资源目录（用户可见、可修改）"""
    if hasattr(sys, "_MEIPASS"):
        return pathlib.Path(sys.executable).resolve().parent
    return pathlib.Path(__file__).resolve().parent


def _find_material_dir():
    """Material 目录：外部优先，内部兜底"""
    candidates = [
        _external_dir / "Material",
        _external_dir / "Data" / "Image" / "Material",
        _base_dir / "Data" / "Image" / "Material",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


_base_dir = _find_base_dir()
_external_dir = _find_external_dir()

# ===== 内部资源（打包进 _MEIPASS）=====
FOLDER_DATA = _base_dir / "Data"
FOLDER_IMAGE = FOLDER_DATA / "Image"
FOLDER_ICON = FOLDER_IMAGE / "Icon"
FOLDER_WIDGET = FOLDER_ICON / "Widget"
FOLDER_BUTTON = FOLDER_ICON / "Folder"
FOLDER_BACKGROUND = FOLDER_ICON / "Background"
FOLDER_FONT = FOLDER_DATA / "Font"

# ===== 外部资源（用户可见、可修改）=====
FOLDER_MATERIAL = _find_material_dir()
FOLDER_BASE = FOLDER_MATERIAL / ImageType.BASE

FOLDER_APPEND = _external_dir / "あぺんど"
FOLDER_APPEND_BUTTON = FOLDER_APPEND / "フォルダアイコン"


# ===== ウィジェットアイコン =====
PATH_ICON = FOLDER_WIDGET / "Instant.ico"
PATH_FOCUS_ON = FOLDER_WIDGET / "focus_on.png"
PATH_FOCUS_OFF = FOLDER_WIDGET / "focus_off.png"
PATH_DISPLAY_NUM = FOLDER_WIDGET / "display_number.png"
PATH_MARK_ON = FOLDER_WIDGET / "mark_on.png"
PATH_MARK_OFF = FOLDER_WIDGET / "mark_off.png"
PATH_PAUSE = FOLDER_WIDGET / "pause.png"
PATH_PLAYING = FOLDER_WIDGET / "playing.gif"
PATH_MACHAN = FOLDER_WIDGET / "umaaji.png"
PATH_BTN_IMPORT = FOLDER_WIDGET / "import.png"

# ===== サムネイルアイコン =====
PATH_BG_FOLDER = FOLDER_BACKGROUND / "フォルダ背景.png"
PATH_BG_ANIMATION = FOLDER_BACKGROUND / "アニメーション背景.png"
PATH_BG_PHOTO = FOLDER_BACKGROUND / "静止画背景.png"
PATH_BG_FILE = FOLDER_BACKGROUND / "ファイル背景.png"
PATH_BG_PARTS = FOLDER_BACKGROUND / "パーツ背景.png"

PATH_BG_UNSELECTED = FOLDER_BACKGROUND / "未選択.png"
PATH_BUTTON_UNKNOWN = FOLDER_BUTTON / "Unknown.png"


# ===== PIL Image 对象 =====
def _load_image(path, fallback=None):
    if path.exists():
        return Image.open(path).convert("RGBA")
    if fallback is not None:
        return fallback
    return Image.new("RGBA", (100, 100), (0, 0, 0, 0))


BG_FOLDER = _load_image(PATH_BG_FOLDER)
BG_ANIMATION = _load_image(PATH_BG_ANIMATION, fallback=BG_FOLDER)
BG_PHOTO = _load_image(PATH_BG_PHOTO, fallback=BG_FOLDER)
BG_FILE = _load_image(PATH_BG_FILE, fallback=BG_FOLDER)
BG_PARTS = _load_image(PATH_BG_PARTS, fallback=BG_FOLDER)
BG_UNSELECTED = _load_image(
    PATH_BG_UNSELECTED,
    fallback=Image.new("RGBA", (80, 80), (200, 200, 200, 255))
)
BG_MACHAN = _load_image(PATH_MACHAN, fallback=BG_UNSELECTED)


# ===== PIL → QImage =====
def pil_to_qimage(pil_image):
    """将 PIL Image 转换为 QImage（含拷贝，避免悬垂指针）"""
    if pil_image is None:
        qimage = QImage(1, 1, QImage.Format.Format_RGBA8888)
        qimage.fill(0)
        return qimage

    if pil_image.mode != "RGBA":
        pil_image = pil_image.convert("RGBA")

    data = pil_image.tobytes("raw", "RGBA")
    # 必须 .copy()：QImage 不拷贝 data，data 是局部变量，返回后会被 GC
    qimage = QImage(data, pil_image.width, pil_image.height,
                    QImage.Format.Format_RGBA8888).copy()
    return qimage


# 预生成的 QImage（可在 QApplication 创建前使用）
UNSELECTED_QIMAGE = pil_to_qimage(BG_UNSELECTED)
MACHAN_QIMAGE = pil_to_qimage(BG_MACHAN)


# ===== 加工画像パス =====
PATH_GIF_PREVIEW = FOLDER_MATERIAL / "preview.gif"
PATH_MASK_COSTUME = FOLDER_MATERIAL / "mask_costume.gif"
PATH_MASK_FACE = FOLDER_MATERIAL / "mask_face.png"


# ===== フォント =====
PATH_FONT_GENEI = FOLDER_DATA / "Font/GenEiNuGothic-EB_v1.1/GenEiNuGothic-EB.ttf"
FACE_FONT_GENEI = "源暎Nuゴシック EB"
FONT_FAMILY = FACE_FONT_GENEI


def register_fonts():
    """注册自定义字体（必须在 QApplication 创建后调用）"""
    global FONT_FAMILY
    try:
        if PATH_FONT_GENEI.exists():
            font_id = QFontDatabase.addApplicationFont(str(PATH_FONT_GENEI))
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    FONT_FAMILY = families[0]
                    return FONT_FAMILY
    except Exception as e:
        print(f"Font registration warning: {e}")
    return FONT_FAMILY


# ===== 取り込める拡張子 =====
SUFFIXES_IMAGE = [".jpg", ".jpeg", ".png", ".gif",
                  ".JPG", ".JPEG", ".PNG", ".GIF"]
