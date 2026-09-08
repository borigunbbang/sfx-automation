"""
M3: 효과음 매칭 엔진 (TECH_SPEC.md 3.4)

분류된 effect_type의 sfx_folder 안에서 파일을 하나 고른다.
같은 파일이 연달아 나오지 않도록 순환(round-robin) 방식을 쓴다.
"""
from __future__ import annotations
import os

SFX_EXTENSIONS = (".wav", ".mp3", ".m4a", ".aiff")


class SfxPicker:
    def __init__(self):
        self._cursors: dict[str, int] = {}
        self._file_cache: dict[str, list[str]] = {}

    def _list_files(self, folder: str) -> list[str]:
        if folder not in self._file_cache:
            files = sorted(
                f for f in os.listdir(folder)
                if f.lower().endswith(SFX_EXTENSIONS)
            )
            self._file_cache[folder] = files
        return self._file_cache[folder]

    def pick(self, folder: str) -> str | None:
        files = self._list_files(folder)
        if not files:
            return None
        idx = self._cursors.get(folder, 0)
        chosen = files[idx % len(files)]
        self._cursors[folder] = idx + 1
        return os.path.join(folder, chosen)
