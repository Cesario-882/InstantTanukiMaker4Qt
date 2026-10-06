# Packaging Notes (Material / Append / locale)

## Background

External resources live in three directories alongside the executable:

- `./Material`
- `./添加`
- `./locale`

They are **not** bundled into the package.

**Note**: during packaging, **all of `./Data/Image/*` is bundled as a whole**.
Therefore these directories must **not** be placed under `./Data/Image/`,
or they will be forced into the bundle and cannot be kept external.

## Requirements

When packaging, keep the following **outside the bundle**:

- `./Material`
- `./添加`
- `./locale`

**Never bundle them directly.**

## Path Reference

| Path | Note |
| --- | --- |
| `./Data/Image/*` | Bundled as a whole; internal resources go here |
| `./Material` | Shipped assets, external |
| `./添加` | User-added assets, external |
| `./locale` | Translations and alias table, external |

## Summary

1. Use `./Material` as the load path for `Material`, not `./Data/Image/Material`.
2. Do not bundle `./Material`, `./添加`, or `./locale` into the package.
