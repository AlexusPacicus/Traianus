"""ZeroCopyExporter: 64-byte binary node block (Ulpia Fase 1).

Pure bytes-level packing (no side effects). Layout:

    offset   0-23   x, y, z, L, C, H   (6 x float32; L, C, H in [0,1])
    offset  24-55   note_id            (32-char UUID hex, uuid.uuid4().hex)
    offset  56-63   padding            (8-byte zero fill for 64-bit alignment)
    total                               64 bytes

The note_id MUST be exactly 32 lowercase hex characters. Over-long, short, or
non-hex ids are rejected loudly (never silently truncated) so the client GPU
buffer and the server contract can never drift.

`note_id_from_label` derives the note_id (client FNV mirror) for substrate
labels (NODE_*, VEC_*), which are not UUIDs; it is the bijective bridge
between the two halves of the contract.
"""

from __future__ import annotations

import re
import struct

_NOTE_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_BLOCK = struct.Struct("<6f32s8x")
_BLOCK_SIZE = _BLOCK.size  # 64


def _char_codes(label: str) -> list[int]:
    """UTF-16 code units of `label` (JS charCodeAt semantics, BMP-safe)."""
    raw = label.encode("utf-16-le")
    return [int.from_bytes(raw[i : i + 2], "little") for i in range(0, len(raw), 2)]


def note_id_from_label(label: str) -> str:
    """Deterministic 32-hex digest of a node label (client mirror).

    Mirrors `noteIdFromLabel` in frontend/src/binary.ts exactly (FNV-family
    mixer over UTF-16 code units, four 32-bit words) so server and client
    pack byte-identical note_ids from the same node label. The label ids
    emitted by the substrate (NODE_*, VEC_*) are not 32-hex UUIDs, so the
    digest makes the 64-byte zero-copy contract bijective across the boundary.
    Purely observational; not a security primitive.
    """
    codes = _char_codes(label)
    hash_a = 0x811C9DC5 ^ 0x9E3779B9
    hash_b = 0x01000193 ^ 0x85EBCA6B
    for i, code in enumerate(codes):
        hash_a = ((hash_a ^ code) * 0x01000193) & 0xFFFFFFFF
        hash_b = ((hash_b ^ codes[len(codes) - 1 - i]) * 0x85EBCA77) & 0xFFFFFFFF
    c = (hash_a ^ hash_b) & 0xFFFFFFFF
    d = (hash_a + hash_b) & 0xFFFFFFFF
    return f"{hash_a:08x}{hash_b:08x}{c:08x}{d:08x}"


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