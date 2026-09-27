# 狸合器 4Qt

[中文](#中文) | [English](#english)

基于 asashari 的 InstantTanukiMaker-en，使用 PySide6 重写 UI，
进一步完善了 i18n 与跨平台兼容性（含 GNU/Linux）。

A PySide6 rewrite of asashari's InstantTanukiMaker-en, with improved
i18n and cross-platform compatibility (including GNU/Linux).

---

<a name="中文"></a>
## 中文

### 依赖

- Python 3.10+
- 运行依赖见 `requirements.txt`
  （主要依赖：PySide6、Pillow、numpy、opencv-python、natsort）

### 安装

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 运行

```bash
python3 main.py
```

### 打包

`Material` 与 `locale` 需外置，不随包分发。详见 [PACKAGING.md](./PACKAGING.md)。

### License

本项目采用 GPL 许可，详见 [LICENSE](./LICENSE)。

---

<a name="english"></a>
## English

### Dependencies

- Python 3.10+
- Runtime dependencies: see `requirements.txt`
  (main: PySide6, Pillow, numpy, opencv-python, natsort)

### Install

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run

```bash
python3 main.py
```

### Packaging

`Material` and `locale` must be kept external and are not bundled.
See [PACKAGING.md](./PACKAGING.md) for details.

### License

Licensed under GPL. See [LICENSE](./LICENSE).
