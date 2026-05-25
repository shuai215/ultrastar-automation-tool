"""UltraStar txt tag editing helpers."""

from __future__ import annotations

import shutil
from pathlib import Path


class UltraStarTextEditor:
    def update_media_tags(self, txt_path: Path, mp3_path: Path | None, video_path: Path | None = None) -> None:
        txt_path = Path(txt_path)
        self._ensure_file(txt_path)

        lines = txt_path.read_text(encoding="utf-8").splitlines()
        if mp3_path is not None:
            lines = self._set_tag(lines, "MP3", Path(mp3_path).name)
        if video_path is not None:
            lines = self._set_tag(lines, "VIDEO", Path(video_path).name)
        txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def read_gap(self, txt_path: Path) -> int:
        self._ensure_file(txt_path)
        for line in Path(txt_path).read_text(encoding="utf-8").splitlines():
            if line.upper().startswith("#GAP:"):
                value = line.split(":", 1)[1].strip()
                return int(float(value))
        raise ValueError("missing #GAP tag")

    def write_gap(self, txt_path: Path, gap_ms: int) -> None:
        if gap_ms < 0:
            raise ValueError("gap_ms must not be negative")
        self._ensure_file(txt_path)
        lines = Path(txt_path).read_text(encoding="utf-8").splitlines()
        lines = self._set_tag(lines, "GAP", str(gap_ms))
        Path(txt_path).write_text("\n".join(lines) + "\n", encoding="utf-8")

    def adjust_gap(self, txt_path: Path, delta_ms: int) -> int:
        current = self.read_gap(txt_path)
        updated = max(0, current + delta_ms)
        self.backup(txt_path)
        self.write_gap(txt_path, updated)
        return updated

    def backup(self, txt_path: Path) -> Path:
        self._ensure_file(txt_path)
        backup_path = Path(txt_path).with_suffix(Path(txt_path).suffix + ".bak")
        shutil.copy2(txt_path, backup_path)
        return backup_path

    def restore_backup(self, txt_path: Path) -> None:
        backup_path = Path(txt_path).with_suffix(Path(txt_path).suffix + ".bak")
        self._ensure_file(backup_path)
        shutil.copy2(backup_path, txt_path)

    def _set_tag(self, lines: list[str], tag: str, value: str) -> list[str]:
        prefix = f"#{tag.upper()}:"
        replacement = f"{prefix}{value}"
        for index, line in enumerate(lines):
            if line.upper().startswith(prefix):
                updated = list(lines)
                updated[index] = replacement
                return updated
        return [replacement, *lines]

    def _ensure_file(self, path: Path) -> None:
        if not Path(path).is_file():
            raise FileNotFoundError(path)


