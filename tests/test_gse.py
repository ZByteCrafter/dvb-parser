import pytest
from dvb_parser.gse.parser import GSEParser
from dvb_parser.gse.models import GSEPacket


class TestGSEParser:
    def test_parse_complete_packet(self):
        """测试解析完整 GSE 包（无分片）"""
        # 构造 GSE 包
        # Start=1, End=1, Label Type=0 (无 Label)
        # Protocol Type=0x0800 (IPv4)
        # Total Length=22 (header 6 + payload 16)
        # Payload=16 bytes
        # CRC-32 placeholder
        gse_data = bytes([
            0b11000000,              # Start=1, End=1, Label Type=0
            0x00,                    # Reserved
            0x08, 0x00,              # Protocol Type (IPv4)
            0x00, 0x16,              # Total Length=22 (header 6 + payload 16)
            # Payload
            0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
            0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
            # CRC-32 placeholder
            0x00, 0x00, 0x00, 0x00
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(gse_data[:-4])
        gse_data = gse_data[:-4] + crc_value.to_bytes(4, 'big')
        
        packet = GSEParser.parse(gse_data)
        
        assert packet.start == True
        assert packet.end == True
        assert packet.label_type == 0
        assert packet.protocol_type == 0x0800
        assert packet.total_length == 22
        assert len(packet.payload) == 16
        assert packet.is_ipv4 == True
        assert packet.is_complete == True
    
    def test_parse_fragment_start(self):
        """测试解析分片开始"""
        # Start=1, End=0, Label Type=1 (6 字节 Label)
        # Total Length=28 (header 6 + label 6 + payload 16)
        gse_data = bytes([
            0b10010000,              # Start=1, End=0, Label Type=1
            0x00,                    # Reserved
            0x08, 0x00,              # Protocol Type (IPv4)
            0x00, 0x1C,              # Total Length=28 (header 6 + label 6 + payload 16)
            # Label (6 bytes)
            0x01, 0x02, 0x03, 0x04, 0x05, 0x06,
            # Payload (16 bytes)
            0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
            0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
            # CRC-32 placeholder
            0x00, 0x00, 0x00, 0x00
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(gse_data[:-4])
        gse_data = gse_data[:-4] + crc_value.to_bytes(4, 'big')
        
        packet = GSEParser.parse(gse_data)
        
        assert packet.start == True
        assert packet.end == False
        assert packet.label_type == 1
        assert packet.label == bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06])
        assert packet.is_fragment_start == True
    
    def test_crc32_validation(self):
        """测试 CRC-32 校验失败"""
        gse_data = bytes([
            0b11000000, 0x00, 0x08, 0x00, 0x00, 0x10,
            0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
            0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
            0xFF, 0xFF, 0xFF, 0xFF  # 错误的 CRC-32
        ])
        
        with pytest.raises(ValueError, match="CRC-32 校验失败"):
            GSEParser.parse(gse_data)
