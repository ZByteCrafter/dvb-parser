import pytest
from dvb_parser.ule.parser import ULEParser
from dvb_parser.ule.models import ULESNDU


class TestULEParser:
    def test_parse_sndu_with_type(self):
        """测试解析包含协议类型的 SNDU (Type mode: no destination MAC)"""
        # Type mode (Length/Type >= 1536): [Type][Payload][CRC-32]
        # Length/Type=0x0800 (IPv4)
        # Payload=8 bytes
        # CRC-32 placeholder
        sndu_data = bytes([
            0x08, 0x00,              # Protocol Type (IPv4)
            # Payload (no MAC in Type mode)
            0x45, 0x00, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00,
            # CRC-32 placeholder
            0x00, 0x00, 0x00, 0x00
        ])

        from dvb_parser.utils.crc import crc32
        crc_value = crc32(sndu_data[:-4])
        sndu_data = sndu_data[:-4] + crc_value.to_bytes(4, 'big')

        sndu = ULEParser.parse(sndu_data)

        assert sndu.length_or_type == 0x0800
        assert sndu.is_type == True
        assert sndu.protocol_type == 0x0800
        assert sndu.is_ipv4 == True
        assert sndu.destination_mac is None
        assert len(sndu.payload) == 8

    def test_parse_sndu_with_length(self):
        """测试解析包含长度的 SNDU (Length mode: MAC + Payload + CRC)"""
        # Length mode (Length/Type < 1536): [Length][MAC][Payload][CRC-32]
        # Length=16 means MAC(6) + Payload(6) + CRC(4) = 16
        # Length/Type=16 (长度)
        # Destination MAC=6 bytes
        # Payload=6 bytes
        # CRC-32 placeholder
        sndu_data = bytes([
            0x00, 0x10,              # Length=16
            0x01, 0x02, 0x03, 0x04, 0x05, 0x06,  # Destination MAC
            # Payload (6 bytes)
            0x00, 0x01, 0x02, 0x03, 0x04, 0x05,
            # CRC-32 placeholder
            0x00, 0x00, 0x00, 0x00
        ])

        from dvb_parser.utils.crc import crc32
        crc_value = crc32(sndu_data[:-4])
        sndu_data = sndu_data[:-4] + crc_value.to_bytes(4, 'big')

        sndu = ULEParser.parse(sndu_data)

        assert sndu.length_or_type == 16
        assert sndu.is_type == False
        assert sndu.length == 16
        assert sndu.destination_mac == bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06])
        assert len(sndu.payload) == 6
