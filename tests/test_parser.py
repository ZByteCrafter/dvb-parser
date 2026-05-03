import pytest
from dvb_parser.parser import DVBParser
from dvb_parser.models import ParseResult


class TestDVBParser:
    def test_parse_bbframe_auto_detect(self):
        """测试 BBFrame 格式自动检测"""
        from dvb_parser.utils.crc import crc8

        bb_header = bytes([
            0b00000000, 0b00000000,
            0x00, 0xBC,
            0x06, 0x18,
            0x00,
            0x00, 0x00,
            0x00
        ])
        crc_value = crc8(bb_header[:9])
        bb_header = bb_header[:9] + bytes([crc_value])

        ts_header = bytes([0x47, 0b00000000, 0x00, 0b00010000])
        ts_payload = bytes([0xFF] * 184)
        ts_packet = ts_header + ts_payload

        ts_data = ts_packet * (195 // 188 + 1)
        ts_data = ts_data[:195]

        bbframe_data = bb_header + ts_data

        parser = DVBParser()
        result = parser.parse(bbframe_data)

        assert result.format == "bbframe"
        assert len(result.bbframes) == 1
        assert len(result.ts_packets) > 0

    def test_parse_ts_auto_detect(self):
        """测试 TS 格式自动检测"""
        ts_header = bytes([0x47, 0b00000000, 0x00, 0b00010000])
        ts_payload = bytes([0xFF] * 184)
        ts_data = ts_header + ts_payload

        parser = DVBParser()
        result = parser.parse(ts_data)

        assert result.format == "ts"
        assert len(result.ts_packets) == 1

    def test_parse_with_manual_format(self):
        """测试手动指定格式"""
        ts_header = bytes([0x47, 0b00000000, 0x00, 0b00010000])
        ts_payload = bytes([0xFF] * 184)
        ts_data = ts_header + ts_payload

        parser = DVBParser()
        result = parser.parse(ts_data, format="ts")

        assert result.format == "ts"
        assert len(result.ts_packets) == 1

    def test_parse_with_errors(self):
        """测试容错处理"""
        ts_header = bytes([0x00, 0b00000000, 0x00, 0b00010000])
        ts_payload = bytes([0xFF] * 184)
        ts_data = ts_header + ts_payload

        parser = DVBParser()
        result = parser.parse(ts_data, format="ts")

        assert result.format == "ts"
        assert len(result.errors) > 0

    def test_parse_result_summary(self):
        """测试解析摘要"""
        result = ParseResult(format="ts")
        summary = result.summary()

        assert "输入格式: ts" in summary
        assert "BBFrame: 0" in summary
        assert "TS 包: 0" in summary
