"""ZeroCopyExporter (Ulpia Fase 1) — 64-byte binary node block.

Contract (validated against the Ulpia binary spec and the frontend GLSL):
  offset  0-23  x, y, z, L, C, H   (6 x float32, L/C in [0,1])
  offset 24-55  note_id            (32-byte UUID hex string)
  offset 56-63  padding            (8 bytes for 64-bit alignment)
  total                              64 bytes

Note id MUST be exactly 32 lowercase hex chars (uuid.hex); anything else is
rejected loudly (never silently truncated).
"""
import struct

import pytest

from traianus.geometry.zero_copy import ZeroCopyExporter


def _hex32(seed: int) -> str:
    """Deterministic 32-char hex string (uuid.hex format)."""
    return f"{seed:032x}"


class TestZeroCopyBlockSize:
    def test_block_size_is_exactly_64_bytes(self):
        exporter = ZeroCopyExporter()
        block = exporter.pack(
            x=0.5, y=-0.25, z=0.75, l=0.1, c=0.9, h=0.6, note_id=_hex32(7)
        )
        assert len(block) == 64

    def test_padding_fills_last_8_bytes(self):
        exporter = ZeroCopyExporter()
        block = exporter.pack(x=1, y=0, z=0, l=1, c=0, h=1, note_id=_hex32(1))
        assert block[56:64] == b"\x00" * 8

    def test_offsets(self):
        exporter = ZeroCopyExporter()
        note = _hex32(42)
        block = exporter.pack(x=1.0, y=-1.0, z=0.5, l=0.25, c=0.75, h=0.5, note_id=note)
        x, y, z, l, c, h = struct.unpack_from("<6f", block, 0)
        assert (x, y, z, l, c, h) == struct.unpack("<6f", block[:24])
        assert struct.unpack_from("<32s", block, 24)[0].rstrip(b"\x00") == note.encode()
        assert (pytest.approx(x), pytest.approx(y), pytest.approx(z)) == (1.0, -1.0, 0.5)
        assert (pytest.approx(l), pytest.approx(c), pytest.approx(h)) == (0.25, 0.75, 0.5)


class TestZeroCopyRoundTrip:
    def test_round_trip_preserves_note_id(self):
        exporter = ZeroCopyExporter()
        note = _hex32(1234)
        block = exporter.pack(x=0.1, y=0.2, z=0.3, l=0.4, c=0.5, h=0.6, note_id=note)
        fields = exporter.unpack(block)
        assert fields["note_id"] == note

    def test_round_trip_preserves_channels(self):
        exporter = ZeroCopyExporter()
        values = {"x": 0.1, "y": 0.2, "z": 0.3, "l": 0.4, "c": 0.5, "h": 0.6, "note_id": _hex32(9)}
        block = exporter.pack(**values)
        fields = exporter.unpack(block)
        for key in ("x", "y", "z", "l", "c", "h"):
            assert fields[key] == pytest.approx(values[key])

    def test_multiple_blocks_contiguous(self):
        exporter = ZeroCopyExporter()
        blocks = b"".join(
            exporter.pack(x=i, y=0, z=0, l=0, c=0, h=0, note_id=_hex32(i))
            for i in range(4)
        )
        assert len(blocks) == 4 * 64


class TestZeroCopyNoteIdValidation:
    def test_rejects_note_id_shorter_than_32(self):
        exporter = ZeroCopyExporter()
        with pytest.raises(ValueError, match="32"):
            exporter.pack(x=0, y=0, z=0, l=0, c=0, h=0, note_id="abc123")

    def test_rejects_note_id_longer_than_32_no_truncation(self):
        """Never silently truncate an over-long id (user note requirement)."""
        exporter = ZeroCopyExporter()
        with pytest.raises(ValueError, match="32"):
            exporter.pack(x=0, y=0, z=0, l=0, c=0, h=0, note_id="f" * 40)

    def test_rejects_non_hex_note_id(self):
        exporter = ZeroCopyExporter()
        with pytest.raises(ValueError, match="hex"):
            exporter.pack(x=0, y=0, z=0, l=0, c=0, h=0, note_id="z" * 32)

    def test_accepts_exact_32_hex_uuid(self):
        exporter = ZeroCopyExporter()
        block = exporter.pack(x=0, y=0, z=0, l=0, c=0, h=0, note_id=_hex32(1))
        assert len(block) == 64