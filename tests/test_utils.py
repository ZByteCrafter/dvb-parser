import pytest
from dvb_parser.utils.crc import crc8, crc32


class TestCRC8:
    def test_crc8_basic(self):
        """Test CRC-8 basic calculation"""
        data = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        result = crc8(data)
        assert isinstance(result, int)
        assert 0 <= result <= 255

    def test_crc8_known_value(self):
        """Test CRC-8 known value"""
        data = bytes([0x00, 0x00, 0x00, 0xBC, 0x06, 0x18, 0x00, 0x00, 0x00])
        result = crc8(data)
        assert result == 0x08


class TestCRC32:
    def test_crc32_basic(self):
        """Test CRC-32 basic calculation"""
        data = b"123456789"
        result = crc32(data)
        assert isinstance(result, int)
        assert 0 <= result <= 0xFFFFFFFF

    def test_crc32_known_value(self):
        """Test CRC-32 known value"""
        data = b"123456789"
        result = crc32(data)
        assert result == 0xCBF43926
