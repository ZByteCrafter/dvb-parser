import pytest
from dvb_parser.bbframe.models import (
    BBFrame,
    BBFrameHeader,
    ScramblingMode,
    StreamType,
)


class TestStreamType:
    def test_ts_value(self):
        assert StreamType.TS == 0b00

    def test_gse_value(self):
        assert StreamType.GSE == 0b01

    def test_gcs_value(self):
        assert StreamType.GCS == 0b10

    def test_reserved_value(self):
        assert StreamType.RESERVED == 0b11


class TestScramblingMode:
    def test_no_scrambling(self):
        assert ScramblingMode.NO_SCRAMBLING == 0b00

    def test_energy_dispersal(self):
        assert ScramblingMode.ENERGY_DISPERAL == 0b01

    def test_reserved_1(self):
        assert ScramblingMode.RESERVED_1 == 0b10

    def test_reserved_2(self):
        assert ScramblingMode.RESERVED_2 == 0b11


class TestBBFrameHeader:
    def _make_header(self, matype_byte0=0x00, matype_byte1=0x00):
        matype = bytes([matype_byte0, matype_byte1])
        return BBFrameHeader(
            matype=matype,
            upl=188,
            dfl=39200,
            sync=0x00,
            syncd=0x0000,
            crc8=0x00,
        )

    def test_stream_type_ts(self):
        header = self._make_header(matype_byte0=0b00_00_00_00)
        assert header.stream_type == StreamType.TS
        assert header.is_ts_mode is True
        assert header.is_gse_mode is False
        assert header.is_gcs_mode is False

    def test_stream_type_gse(self):
        header = self._make_header(matype_byte0=0b01_00_00_00)
        assert header.stream_type == StreamType.GSE
        assert header.is_gse_mode is True

    def test_stream_type_gcs(self):
        header = self._make_header(matype_byte0=0b10_00_00_00)
        assert header.stream_type == StreamType.GCS
        assert header.is_gcs_mode is True

    def test_stream_type_reserved(self):
        header = self._make_header(matype_byte0=0b11_00_00_00)
        assert header.stream_type == StreamType.RESERVED

    def test_scrambling_mode_no_scrambling(self):
        header = self._make_header(matype_byte0=0b00_00_00_00)
        assert header.scrambling_mode == ScramblingMode.NO_SCRAMBLING

    def test_scrambling_mode_energy_dispersal(self):
        header = self._make_header(matype_byte1=0b01_000000)
        assert header.scrambling_mode == ScramblingMode.ENERGY_DISPERAL

    def test_scrambling_mode_reserved_1(self):
        header = self._make_header(matype_byte1=0b10_000000)
        assert header.scrambling_mode == ScramblingMode.RESERVED_1

    def test_scrambling_mode_reserved_2(self):
        header = self._make_header(matype_byte1=0b11_000000)
        assert header.scrambling_mode == ScramblingMode.RESERVED_2

    def test_isi(self):
        header = self._make_header(matype_byte1=0x42)
        assert header.isi == 0x42

    def test_isi_default_when_short_matype(self):
        header = BBFrameHeader(
            matype=bytes([0x00]),
            upl=188,
            dfl=39200,
            sync=0x00,
            syncd=0x0000,
            crc8=0x00,
        )
        assert header.isi == 0

    def test_npd_enabled(self):
        header = self._make_header(matype_byte0=0b00_00_00_01)
        assert header.npd is True

    def test_npd_disabled(self):
        header = self._make_header(matype_byte0=0b00_00_00_00)
        assert header.npd is False

    def test_roll_off(self):
        header = self._make_header(matype_byte0=0b00_10_00_00)
        assert header.roll_off == 0b10

    def test_roll_off_zero(self):
        header = self._make_header(matype_byte0=0b00_00_00_00)
        assert header.roll_off == 0

    def test_combined_fields(self):
        header = self._make_header(matype_byte0=0b01_10_01_01, matype_byte1=0b10_000101)
        assert header.stream_type == StreamType.GSE
        assert header.scrambling_mode == ScramblingMode.RESERVED_1
        assert header.roll_off == 0b10
        assert header.npd is True
        assert header.isi == 0b10_000101


class TestBBFrame:
    def _make_frame(self, dfl_bits=39200):
        matype = bytes([0x00, 0x00])
        header = BBFrameHeader(
            matype=matype,
            upl=188,
            dfl=dfl_bits,
            sync=0x00,
            syncd=0x0000,
            crc8=0x00,
        )
        data_field = bytes(dfl_bits // 8)
        padding = b""
        return BBFrame(header=header, data_field=data_field, padding=padding)

    def test_data_field_length_bytes(self):
        frame = self._make_frame(dfl_bits=39200)
        assert frame.data_field_length_bytes == 39200 // 8

    def test_header_access(self):
        frame = self._make_frame()
        assert frame.header.upl == 188
        assert frame.header.stream_type == StreamType.TS

    def test_data_field(self):
        frame = self._make_frame(dfl_bits=800)
        assert len(frame.data_field) == 100

    def test_padding(self):
        matype = bytes([0x00, 0x00])
        header = BBFrameHeader(
            matype=matype,
            upl=188,
            dfl=800,
            sync=0x00,
            syncd=0x0000,
            crc8=0x00,
        )
        frame = BBFrame(
            header=header,
            data_field=bytes(100),
            padding=bytes(10),
        )
        assert len(frame.padding) == 10
