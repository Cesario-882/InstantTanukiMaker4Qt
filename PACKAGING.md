# Packaging Notes (Material / Append / locale)

## Background

External resources are loaded from three directories alongside the executable:
- `./Material`
- `./添加` (Append)
- `./locale`

They are **not** bundled into the PyInstaller package.

**Note**: During packaging, **all of `./Data/Image/*` is bundled as a whole** into the executable.
Therefore, these three external directories must **not** be placed under `./Data/Image/`,
or they will be forced into the bundle and the external loading mechanism will fail.

## Requirements

When packaging (e.g., using PyInstaller), keep the following **outside the bundle**:
- `./Material`
- `./添加` (Append)
- `./locale`

**Never bundle them directly.** Our CI/CD scripts (`build.ps1` / `build.sh`) automatically copy them to the output directory after the build process.

## Path Reference

| Path | Note |
| --- | --- |
| `./Data/Image/*` | Internal resources (icons, fonts), bundled as a whole |
| `./Material` | Shipped core assets, external |
| `./添加` (Append) | User-added assets, external |
| `./locale` | Translations and i18n configs, external |

## Summary

1. Use `./Material` as the load path for `Material`, not `./Data/Image/Material`.
2. Do not bundle `./Material`, `./添加`, or `./locale` into the package.
3. It is highly recommended to use the built-in `.tzst` import/export feature for material distribution.
