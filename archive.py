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

"""Tanukora Zstd/Tar Archive (.tzst) 导入导出。"""
from __future__ import annotations

import os
import pathlib
import tarfile
import shutil
import json
import tempfile
from typing import Callable, Optional

import const

try:
    import zstandard as zstd
    HAS_ZSTD = True
except ImportError:
    HAS_ZSTD = False


class ArchiveError(Exception):
    def __init__(self, message_key: str, **kwargs):
        super().__init__(message_key)
        self.message_key = message_key
        self.kwargs = kwargs


def export_archive(path_out: pathlib.Path,
                   progress: Optional[Callable[[str], None]] = None) -> None:
    if not HAS_ZSTD:
        raise ArchiveError("zstdライブラリが見つかりません。")

    path_out = pathlib.Path(path_out)
    if not const.FOLDER_MATERIAL.exists():
        raise ArchiveError("必要なフォルダが見つかりません: {names}", names=const.FOLDER_MATERIAL.name)

    folders = [f for f in const.ARCHIVE_FOLDERS if f.exists()]

    # 极限多线程
    cctx = zstd.ZstdCompressor(level=const.ARCHIVE_ZSTD_LEVEL, threads=-1)

    # ===== 核心改进：利用 tmpfs =====
    # 如果系统有 /dev/shm（Linux 内存盘），我们就用它作为临时工作区，速度起飞
    tmp_base = "/dev/shm" if os.path.exists("/dev/shm") else None

    # 使用 tempfile 在指定的内存盘（或系统临时目录）创建临时文件
    # 如果目标是当前目录，且不在跨磁盘，使用同目录下的临时文件也是一种极速方案
    tmp_fd, tmp_name = tempfile.mkstemp(
        suffix=".tzst.tmp",
        prefix=".tanukora_",
        dir=tmp_base if tmp_base else str(path_out.parent)
    )
    tmp_path = pathlib.Path(tmp_name)

    try:
        with open(tmp_fd, "wb") as raw:
            with cctx.stream_writer(raw, closefd=False) as compressor:
                with tarfile.open(fileobj=compressor, mode="w|") as tar:
                    for folder in folders:
                        # 路径推算
                        for root in const.ARCHIVE_ROOTS:
                            if str(folder) == str(const._external_dir / root):
                                base_dir = const._external_dir
                                break
                        else:
                            base_dir = folder.parents[len(folder.parts) - 2]

                        for entry in _iter_files(folder):
                            rel = entry.relative_to(base_dir).as_posix()

                            if rel in const.ARCHIVE_EXCLUDE:
                                continue
                            if progress:
                                progress(rel)

                            tar_info = tar.gettarinfo(str(entry), arcname=rel)
                            with open(entry, "rb") as f:
                                tar.addfile(tar_info, f)

        # 如果临时目录和输出目录在同一个分区，这里是零耗时重命名
        # 如果是跨分区（比如从 /dev/shm 移到物理盘），这里就是一次顺序拷贝
        shutil.move(str(tmp_path), str(path_out))
    except Exception as e:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        raise ArchiveError("書き出しエラー: {err}", err=str(e))


def _iter_files(root: pathlib.Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            p = pathlib.Path(dirpath) / name
            if p.is_file() and not p.is_symlink():
                yield p


def _is_valid_root(parts: tuple) -> bool:
    for root in const.ARCHIVE_ROOTS:
        root_parts = pathlib.PurePosixPath(root).parts
        if parts[:len(root_parts)] == root_parts:
            return True
    return False


def inspect_archive(path_in: pathlib.Path) -> None:
    if not HAS_ZSTD:
        raise ArchiveError("zstdライブラリが見つかりません。")

    path_in = pathlib.Path(path_in)
    if not path_in.exists():
        raise ArchiveError("アーカイブが見つかりません。")

    total_size = 0
    dctx = zstd.ZstdDecompressor()

    try:
        with open(path_in, "rb") as raw:
            with dctx.stream_reader(raw) as reader:
                with tarfile.open(fileobj=reader, mode="r|") as tar:
                    for member in tar:
                        _check_member(member)
                        if member.isfile():
                            total_size += member.size
                            if total_size > const.ARCHIVE_TOTAL_LIMIT:
                                raise ArchiveError("アーカイブの展開サイズが上限を超えています。")
    except Exception as e:
        if isinstance(e, ArchiveError):
            raise
        raise ArchiveError("アーカイブの検証に失敗しました。破損している可能性があります。")


def _check_member(member: tarfile.TarInfo) -> None:
    if member.issym() or member.islnk():
        raise ArchiveError("アーカイブにリンクが含まれています: {name}", name=member.name)
    if member.isdev():
        raise ArchiveError("アーカイブに特殊ファイルが含まれています: {name}", name=member.name)

    if member.isdir():
        return
    if not member.isfile():
        raise ArchiveError("アーカイブに不明なエントリがあります: {name}", name=member.name)

    parts = pathlib.PurePosixPath(member.name).parts
    if not parts or not _is_valid_root(parts):
        raise ArchiveError("アーカイブ内のパスが不正です: {name}", name=member.name)
    if any(p in ("..", "") for p in parts):
        raise ArchiveError("アーカイブ内のパスが不正です: {name}", name=member.name)
    if member.size > const.ARCHIVE_MEMBER_LIMIT:
        raise ArchiveError("ファイルサイズが上限を超えています: {name}", name=member.name)


def _merge_json(target_path: pathlib.Path, new_data: dict) -> None:
    if target_path.exists():
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                local_data = json.load(f)
        except Exception:
            local_data = {}
    else:
        local_data = {}

    local_data.update(new_data)

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(local_data, f, ensure_ascii=False, indent=2)


def import_archive(path_in: pathlib.Path,
                   overwrite: bool = True,
                   progress: Optional[Callable[[str], None]] = None) -> None:
    inspect_archive(path_in)

    base = const._external_dir
    dctx = zstd.ZstdDecompressor()

    try:
        with open(path_in, "rb") as raw:
            with dctx.stream_reader(raw) as reader:
                with tarfile.open(fileobj=reader, mode="r|") as tar:
                    for member in tar:
                        if not member.isfile():
                            continue
                        if member.name in const.ARCHIVE_EXCLUDE:
                            continue

                        target = base / pathlib.PurePosixPath(member.name)

                        is_uma_json = (
                            member.name.startswith("locale/uma/") and
                            member.name.endswith(".json")
                        )

                        if is_uma_json and target.exists():
                            if progress:
                                progress(member.name)
                            src = tar.extractfile(member)
                            if src is None:
                                continue
                            try:
                                new_data = json.loads(src.read().decode("utf-8"))
                                _merge_json(target, new_data)
                            except Exception:
                                pass
                            continue

                        if overwrite and target.exists():
                            try:
                                target.unlink()
                            except Exception:
                                pass

                        if not overwrite and target.exists():
                            if progress:
                                progress(member.name)
                            continue

                        if progress:
                            progress(member.name)

                        # ===== 优化：减少 I/O 查询 =====
                        if not target.parent.exists():
                            target.parent.mkdir(parents=True, exist_ok=True)

                        src = tar.extractfile(member)
                        if src is None:
                            continue

                        with open(target, "wb") as out:
                            while True:
                                chunk = src.read(1 << 20) # 每次读 1MB
                                if not chunk:
                                    break
                                out.write(chunk)
    except Exception as e:
        if isinstance(e, ArchiveError):
            raise
        raise ArchiveError("展開中にエラーが発生しました: {err}", err=str(e))
