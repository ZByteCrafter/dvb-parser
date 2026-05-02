import pytest
from dvb_parser.mpe.parser import MPEParser
from dvb_parser.mpe.models import MPEDatagram

class TestMPEParser:
    def test_parse_valid_mpe(self):
        """测试解析有效的 MPE section"""
        # 构造 MPE section
        section_data = bytes([
            0x3E,                    # table_id
            0b10110000, 0x12,        # syntax_indicator=1, length=18
            # MAC address
            0x01, 0x02, 0x03, 0x04, 0x05, 0x06,
            # Payload (IP datagram)
            0x45, 0x00, 0x00, 0x08,  # IPv4 header
            0x00, 0x00, 0x00, 0x00,
            # CRC-32 placeholder
            0x00, 0x00, 0x00, 0x00
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')
        
        mpe = MPEParser.parse(section_data)
        
        assert mpe.table_id == 0x3E
        assert mpe.mac_address == bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06])
        assert mpe.mac_address_str == "01:02:03:04:05:06"
        assert len(mpe.payload) == 8
    
    def test_mac_address_parsing(self):
        """测试 MAC 地址解析"""
        section_data = bytes([
            0x3E, 0b10110000, 0x16,  # section_length = 22 (6 MAC + 12 payload + 4 CRC)
            0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,  # 广播地址
            0x45, 0x00, 0x00, 0x04,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')
        
        mpe = MPEParser.parse(section_data)
        
        assert mpe.is_broadcast == True
