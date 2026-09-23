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

from traianus.geometry.zero_copy import ZeroCopyExporter, note_id_from_label


def _hex32(seed: int) -> str:
    """Deterministic 32-char hex string (uuid.hex format)."""
    return f"{seed:032x}"


_TS_DIGEST_ORACLE: dict[str, str] = {
    "NODE_1": "c37fe37c062ac054c5552328c9aaa3d0",
    "NODE_2": "c67fe83599577b6f5f28935a5fd763a4",
    "VEC_03f2a9c": "0060a0650e7ddcb90e1d7cdc0ede7d1e",
    "concept-omega": "76f7ed7e82a0becaf45753b4f998ac48",
    "HITL-ethos": "2f096f67f5f6fb45daff942225006aac",
    "node-with-hyphen_7": "99167fa46e4f8340f759fce4076602e4",
    "NODE_0": "c47fe50f91c6323955b9d73656461748",
}

_TS_RESTING_HEX_ORACLE: str = (
    # NODE_1
    "cdcccc3dcdcc4cbe9a99993ecdcccc3d9a99993e6666663f"
    "6333376665333763303632616330353463353535323332386339616161336430"
    "0000000000000000"
    # NODE_2
    "abaaaa3e7cd9a03e000000bf9a99193f3333333fcdcccc3e"
    "6336376665383335393935373762366635663238393335613566643736336134"
    "0000000000000000"
    # VEC_03f2a9c
    "000000000000803f000080bf0000803f00000000abaaaa3e"
    "3030363061303635306537646463623930653164376364633065646537643165"
    "0000000000000000"
    # concept-omega
    "17b7d13872f97f3f0000003f0000003f0000003f0000003f"
    "3736663765643765383261306265636166343537353362346639393861633438"
    "0000000000000000"
    # HITL-ethos
    "000040bf0000803e0000003ecdcc4c3ecdcc4c3f0000803f"
    "3266303936663637663566366662343564616666393432323235303036616163"
    "0000000000000000"
    # NODE_0
    "000000000000000000000000000000000000000000000000"
    "6334376665353066393163363332333935356239643733363536343631373438"
    "0000000000000000"
)

_TS_NODES_LITERAL: dict[str, dict[str, float]] = {
    "NODE_1": {"x": 0.1, "y": -0.2, "z": 0.3, "l": 0.1, "c": 0.30000000000000004, "h": 0.9},
    "NODE_2": {"x": 1 / 3, "y": 0.3141592653589793, "z": -0.5, "l": 0.6, "c": 0.7, "h": 0.4},
    "VEC_03f2a9c": {"x": 0.0, "y": 1.0, "z": -1.0, "l": 1.0, "c": 0.0, "h": 1 / 3},
    "concept-omega": {"x": 0.0001, "y": 0.9999, "z": 0.5, "l": 0.5, "c": 0.5, "h": 0.5},
    "HITL-ethos": {"x": -0.75, "y": 0.25, "z": 0.125, "l": 0.2, "c": 0.8, "h": 1.0},
    "NODE_0": {"x": 0.0, "y": 0.0, "z": 0.0, "l": 0.0, "c": 0.0, "h": 0.0},
}


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


class TestNoteIdFromLabel:
    """Server-side mirror of the client digest (frontend/src/binary.ts).

    The client derives the 32-hex note_id via noteIdFromLabel (FNV-family);
    the server must emit byte-identical note_ids from the same node label so
    the zero-copy buffer is bijective across the boundary. Oracle values are
    produced by compiling the real frontend binary.ts and running it in Node.
    """

    def test_format_is_32_lowercase_hex(self):
        for label in _TS_DIGEST_ORACLE:
            digest = note_id_from_label(label)
            assert len(digest) == 32
            assert all(ch in "0123456789abcdef" for ch in digest)

    def test_deterministic(self):
        assert note_id_from_label("NODE_1") == note_id_from_label("NODE_1")

    def test_matches_client_oracle(self):
        for label, expected in _TS_DIGEST_ORACLE.items():
            assert note_id_from_label(label) == expected, f"digest mismatch for {label}"

    def test_feeds_the_exporter_contract(self):
        exporter = ZeroCopyExporter()
        block = exporter.pack(0.1, 0.2, 0.3, 0.5, 0.3, 0.7, note_id_from_label("HITL-ethos"))
        assert len(block) == 64


class TestByteParityWithClient:
    """Full 64-byte resting buffer must be byte-identical to the client packer.

    Golden hex was produced by compiling frontend/src/binary.ts to JS and
    packing the same node vector in Node (frontend/src/binary.ts is the
    single source of truth for the client half of the contract).
    """

    def test_resting_buffer_byte_parity(self):
        exporter = ZeroCopyExporter()
        blocks = b"".join(
            exporter.pack(
                x=ch["x"],
                y=ch["y"],
                z=ch["z"],
                l=ch["l"],
                c=ch["c"],
                h=ch["h"],
                note_id=note_id_from_label(node_id),
            )
            for node_id, ch in _TS_NODES_LITERAL.items()
        )
        assert blocks.hex() == _TS_RESTING_HEX_ORACLE

    def test_per_node_offsets_and_padding(self):
        exporter = ZeroCopyExporter()
        for node_id, ch in _TS_NODES_LITERAL.items():
            block = exporter.pack(
                x=ch["x"],
                y=ch["y"],
                z=ch["z"],
                l=ch["l"],
                c=ch["c"],
                h=ch["h"],
                note_id=note_id_from_label(node_id),
            )
            assert block[24:56] == note_id_from_label(node_id).encode("ascii")
            assert block[56:64] == b"\x00" * 8