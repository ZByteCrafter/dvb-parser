import pytest
from dvb_parser.bbframe.parser import BBFrameParser
from dvb_parser.bbframe.models import StreamType


class TestBBFrameParser:
    def test_parse_valid_bbframe(self):
        """Test parsing a valid BBFrame"""
        header_data = bytes([
            0b00000000, 0b00000000,  # MATYPE (TS mode)
            0x00, 0xBC,              # UPL (188 bytes)
            0x06, 0x18,              # DFL (1560 bits)
            0x00,                    # SYNC
            0x00, 0x00,              # SYNCD
            0x00                     # CRC-8 (placeholder)
        ])

        from dvb_parser.utils.crc import crc8
        crc_value = crc8(header_data[:9])
        header_data = header_data[:9] + bytes([crc_value])

        data_field = bytes([0x00] * 195)

        bbframe_data = header_data + data_field

        bbframe = BBFrameParser.parse(bbframe_data)

        assert bbframe.header.is_ts_mode
        assert bbframe.header.upl == 188
        assert bbframe.header.dfl == 1560
        assert len(bbframe.data_field) == 195

    def test_parse_invalid_crc(self):
        """Test CRC-8 checksum failure"""
        header_data = bytes([
            0b00000000, 0b00000000,  # MATYPE
            0x00, 0xBC,              # UPL
            0x06, 0x18,              # DFL
            0x00,                    # SYNC
            0x00, 0x00,              # SYNCD
            0xFF                     # Wrong CRC-8
        ])
        data_field = bytes([0x00] * 195)
        bbframe_data = header_data + data_field

        with pytest.raises(ValueError, match="CRC-8"):
            BBFrameParser.parse(bbframe_data)

    def test_parse_insufficient_data(self):
        """Test insufficient data"""
        data = bytes([0x00] * 5)

        with pytest.raises(ValueError, match="数据不足"):
            BBFrameParser.parse(data)

    def test_parse_gse_mode(self):
        """Test GSE mode"""
        header_data = bytes([
            0b01000000, 0b00000000,  # MATYPE (GSE mode)
            0x00, 0xBC,              # UPL
            0x06, 0x18,              # DFL
            0x00,                    # SYNC
            0x00, 0x00,              # SYNCD
            0x00                     # CRC-8 (placeholder)
        ])

        from dvb_parser.utils.crc import crc8
        crc_value = crc8(header_data[:9])
        header_data = header_data[:9] + bytes([crc_value])

        data_field = bytes([0x00] * 195)
        bbframe_data = header_data + data_field

        bbframe = BBFrameParser.parse(bbframe_data)

        assert bbframe.header.is_gse_mode
        assert not bbframe.header.is_ts_mode
