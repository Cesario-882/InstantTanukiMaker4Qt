# 狸合器 4Qt (InstantTanukiMaker 4Qt)

[中文](#中文文档) | [English](#english-documentation)

基于上游 Asashri 的 InstantTanukiMaker-en，将底层框架从 wxPython 迁移至 PySide6 的重构版本
完善了国际化（i18n）与跨平台兼容性（Windows / GNU/Linux），并制定了新的素材分发标准
Based on the upstream Asashri's InstantTanukiMaker-en, this is a refactored version with the underlying framework migrated from wxPython to PySide6.
It improves internationalization (i18n) and cross-platform compatibility (Windows / GNU/Linux), and introduces a new standard for asset distribution.

---

## 中文文档

### 核心特性

- 底层框架重构：将底层 UI 框架从 wxPython 迁移至 PySide6 (Qt6)，完全保留了原版的界面布局与操作逻辑
- .tzst素材包标准：引入基于Zstd -19压缩的 Tanukora Archive 格式，将原本几百兆的素材库压缩至几十兆，极大地节省了分发成本和存储空间
- 安全目录结构：区分 Material（随包核心）与 添加（用户自定义）。在导入素材包时，程序会自动进行智能合并，绝不会覆盖用户本地已有的翻译与自定义素材
- GitHub Actions 构建：云端全自动打包，提供免安装的 Windows 与 Linux 版本。内置运行库，解压即用，无需配置任何 Python 环境

### 安装与运行 (开发环境)

需要 Python 3.14+
在终端中执行：
```bash
python3 -m venv venv
source venv/bin/activate # Windows 用户请用 venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### 打包与分发

项目已配置自动构建脚本，在 Windows 下运行 build.ps1或在 Linux 下运行 build.sh，即可在本地生成包含所有运行库的免安装包。
关于目录结构的规范要求，请务必阅读 [打包须知.md](./打包须知.md)。

### 用户指南

如果你只是想往“添加”目录塞自定义素材，请务必在操作前阅读[添加前须知.md](./添加前须知.md)，了解目录映射规则与查重防呆指南。

### License

本项目采用 GPL v3 许可。详见 [LICENSE](./LICENSE)。如有中文阅读需求，请参阅 [LICENSE_zh](./LICENSE_zh)。

---

## English Documentation

A PySide6 rewrite of Asashri's `InstantTanukiMaker-en`, migrating the underlying framework from wxPython. Improved i18n and cross-platform compatibility (including GNU/Linux), and established a new material distribution standard.

### Key Features

- **Framework Migration**: Migrated the UI framework from wxPython to PySide6 (Qt6), while completely preserving the original UI layout and workflow.
- **`.tzst` Package Standard**: Introduced the Tanukora Archive format based on Zstd -19 compression. It compresses material libraries from hundreds of megabytes to just tens of megabytes, greatly saving distribution costs and storage space.
- **Safe Directory Structure**: Decouples `Material` (core assets) from `添加` (user-customized assets, meaning "Append"). When importing packages, the program performs intelligent merging and will absolutely never overwrite the user's local translations and custom materials.
- **GitHub Actions Build**: Fully automated cloud packaging. Provides standalone Windows and Linux versions with built-in runtimes. Just extract and run, with zero Python environment configuration required.

### Installation & Run (Development)

Requires Python 3.14+
Run in terminal:
```bash
python3 -m venv venv
source venv/bin/activate  # For Windows users: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Packaging

Automated build scripts are provided. Run build.ps1 on Windows or build.sh on Linux to generate standalone packages. For directory structure requirements, please read [PACKAGING.md](./PACKAGING.md).

### License

Licensed under GPL v3. See [LICENSE](./LICENSE) for details.
