"""Tests for core/compress.py."""

import shutil
from pathlib import Path

import pytest

from core.compress import (
    compress_file_gzip,
    compress_file_zip,
    compress_folder_targz,
    compress_folder_zip,
    decompress_file,
)

FIXTURE = Path(__file__).parent / "fixtures" / "test_data.txt"


@pytest.fixture
def work(tmp_path: Path) -> Path:
    shutil.copy(FIXTURE, tmp_path / "test_data.txt")
    return tmp_path


class TestFileRoundtrips:
    def test_zip_roundtrip(self, work: Path):
        src = work / "test_data.txt"
        original = src.read_bytes()

        archive = compress_file_zip(src)
        assert archive == work / "test_data.txt.zip"
        assert archive.exists()

        src.unlink()
        extracted = decompress_file(archive)
        assert extracted == [src]
        assert src.read_bytes() == original

    def test_gzip_roundtrip(self, work: Path):
        src = work / "test_data.txt"
        original = src.read_bytes()

        archive = compress_file_gzip(src)
        assert archive == work / "test_data.txt.gz"

        src.unlink()
        extracted = decompress_file(archive)
        assert extracted == [src]
        assert src.read_bytes() == original


class TestFolderRoundtrips:
    def test_folder_zip(self, work: Path):
        folder = work / "bundle"
        folder.mkdir()
        shutil.copy(FIXTURE, folder / "a.txt")
        (folder / "sub").mkdir()
        shutil.copy(FIXTURE, folder / "sub" / "b.txt")

        archive = compress_folder_zip(folder)
        assert archive == work / "bundle.zip"

        shutil.rmtree(folder)
        extracted = decompress_file(archive)
        assert (folder / "a.txt").read_bytes() == FIXTURE.read_bytes()
        assert (folder / "sub" / "b.txt").exists()
        assert set(extracted) == {folder / "a.txt", folder / "sub" / "b.txt"}

    def test_folder_targz(self, work: Path):
        folder = work / "bundle"
        folder.mkdir()
        shutil.copy(FIXTURE, folder / "a.txt")

        archive = compress_folder_targz(folder)
        assert archive == work / "bundle.tar.gz"

        shutil.rmtree(folder)
        extracted = decompress_file(archive)
        assert extracted == [folder / "a.txt"]
        assert (folder / "a.txt").read_bytes() == FIXTURE.read_bytes()


class TestErrors:
    def test_folder_zip_on_file_raises(self, work: Path):
        with pytest.raises(ValueError, match="Not a folder"):
            compress_folder_zip(work / "test_data.txt")

    def test_folder_targz_on_file_raises(self, work: Path):
        with pytest.raises(ValueError, match="Not a folder"):
            compress_folder_targz(work / "test_data.txt")

    def test_unsupported_extension_raises(self, work: Path):
        with pytest.raises(ValueError, match="Unsupported archive type"):
            decompress_file(work / "test_data.txt")
