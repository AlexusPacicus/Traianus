"""ZeroCopyExporter: 64-byte binary node block (Ulpia Fase 1).

Pure bytes-level packing (no side effects). Layout:

    offset   0-23   x, y, z, L, C, H   (6 x float32; L, C, H in [0,1])
    offset  24-55   note_id            (32-char UUID hex, uuid.uuid4().hex)
    offset  56-63   padding            (8-byte zero fill for 64-bit alignment)
    total                               64 bytes

The note_id MUST be exactly 32 lowercase hex characters. Over-long, short, or
non-hex ids are rejected loudly (never silently truncated) so the client GPU
buffer and the server contract can never drift.
"""

from __future__ import annotations

import re
import struct

_NOTE_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_BLOCK = struct.Struct("<6f32s8x")
_BLOCK_SIZE = _BLOCK.size  # 64


class ZeroCopyExporter:
    """Stateless packer/unpacker for the 64-byte Ulpia binary contract."""

    def __init__(self) -> None:
        self._struct = _BLOCK

    @property
    def block_size(self) -> int:
        return _BLOCK_SIZE

    def pack(
        self,
        x: float,
        y: float,
        z: float,
        l: float,
        c: float,
        h: float,
        note_id: str,
    ) -> bytes:
        """Pack one node into a 64-byte block.

        Raises
        ------
        ValueError
            If note_id is not exactly 32 lowercase hex characters, or any
            L/C/H channel is outside [0,1].
        """
        if not _NOTE_ID_RE.fullmatch(note_id):
            raise ValueError(
                "note_id must be exactly 32 lowercase hex chars "
                f"(uuid.hex), got {len(note_id)} chars: {note_id!r}"
            )
        for name, value in (("l", l), ("c", c), ("h", h)):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0,1], got {value}")
        return self._struct.pack(x, y, z, l, c, h, note_id.encode("ascii"))

    def unpack(self, block: bytes) -> dict[str, str | float]:
        """Unpack a 64-byte block into a dict of fields."""
        if len(block) != _BLOCK_SIZE:
            raise ValueError(
                f"block must be exactly {_BLOCK_SIZE} bytes, got {len(block)}"
            )
        x, y, z, l, c, h, note_bytes = self._struct.unpack(block)
        note_id = note_bytes.rstrip(b"\x00").decode("ascii")
        return {
            "x": float(x),
            "y": float(y),
            "z": float(z),
            "l": float(l),
            "c": float(c),
            "h": float(h),
            "note_id": note_id,
        }