# Packaging Notes (Material / locale)

## Background

`Material` has two candidate load paths:

- `./Data/Image/Material`
- `./Material`

During packaging, **all of `./Data/Image/*` is bundled as a whole**. As a result,
if `Material` is placed under `./Data/Image/`, it will be forced into the bundle
and cannot be kept external.

## Requirements

When packaging, keep the following **outside the bundle**:

- `./Material`
- `./locale`

Mount them via **Nuitka or PyInstaller parameters**.

**Never bundle them directly.**

## Path Reference

| Path | Note |
| --- | --- |
| `./Data/Image/Material` | Bundled as part of `./Data/Image/*`; not recommended |
| `./Material` | Standalone path; use this one when packaging |

## Summary

1. Use `./Material` as the load path for `Material`, not `./Data/Image/Material`.
2. Do not bundle `./Material` or `./locale` into the package.
3. Mount them at runtime via Nuitka / PyInstaller parameters.
