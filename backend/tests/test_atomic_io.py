"""原子写回归测试 (P0 #2 #3) — 崩溃/并发下目标文件永不损坏。

覆盖：文本/字节 round-trip、覆盖原子性、无 temp 残留、并发写不混合、自动建父目录。
"""
from __future__ import annotations

import threading
from pathlib import Path

import pytest

from app.utils.atomic_io import atomic_write_bytes, atomic_write_text


class TestAtomicWrite:
    def test_text_roundtrip(self, tmp_path: Path):
        f = tmp_path / "a.txt"
        atomic_write_text(f, "hello\n世界\n")
        assert f.read_text(encoding="utf-8") == "hello\n世界\n"

    def test_bytes_roundtrip(self, tmp_path: Path):
        f = tmp_path / "b.bin"
        atomic_write_bytes(f, b"\x00\x01\x02\xff")
        assert f.read_bytes() == b"\x00\x01\x02\xff"

    def test_overwrite_atomic(self, tmp_path: Path):
        """覆盖后内容是新写入的完整内容，永不截断混合。"""
        f = tmp_path / "c.txt"
        atomic_write_text(f, "old-content" * 10)
        atomic_write_text(f, "new")
        assert f.read_text(encoding="utf-8") == "new"

    def test_no_tmp_leftover(self, tmp_path: Path):
        f = tmp_path / "d.txt"
        atomic_write_text(f, "x")
        leftover = [
            p for p in tmp_path.iterdir()
            if ".tmp" in p.name or p.suffix == ".tmp"
        ]
        assert leftover == [], f"temp leftover detected: {leftover}"

    def test_creates_parent_dir(self, tmp_path: Path):
        f = tmp_path / "sub" / "deep" / "f.txt"
        atomic_write_text(f, "nested")
        assert f.read_text(encoding="utf-8") == "nested"

    def test_concurrent_writes_no_corruption(self, tmp_path: Path):
        """N 并发写：最终内容必是某次完整写入，绝不截断或交错混合。"""
        f = tmp_path / "e.txt"
        contents = [f"content-{i:03d}-" + "x" * 200 for i in range(20)]

        def write(c: str):
            atomic_write_text(f, c)

        threads = [threading.Thread(target=write, args=(c,)) for c in contents]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        final = f.read_text(encoding="utf-8")
        assert final in contents, f"corrupted/interleaved content: {final[:60]!r}..."

    def test_concurrent_writes_distinct_files(self, tmp_path: Path):
        """并发写不同文件全部成功。"""
        files = [tmp_path / f"f{i}.txt" for i in range(10)]
        contents = [f"payload-{i}" for i in range(10)]

        def write(path: Path, c: str):
            atomic_write_text(path, c)

        threads = [
            threading.Thread(target=write, args=(files[i], contents[i]))
            for i in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for i in range(10):
            assert files[i].read_text(encoding="utf-8") == contents[i]
