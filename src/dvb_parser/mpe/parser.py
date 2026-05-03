"""
MPE (Multi-Protocol Encapsulation) parser
"""

import struct

from dvb_parser.mpe.models import MPEDatagram
from dvb_parser.utils.crc import crc32


class MPEParser:
    """MPE 解析器"""
    
    @staticmethod
    def parse(data: bytes, offset: int = 0) -> MPEDatagram:
        """
        解析 MPE section
        
        Args:
            data: 原始数据
            offset: 起始偏移
        
        Returns:
            MPEDatagram 对象
        
        Raises:
            ValueError: CRC-32 校验失败或数据无效
        """
        if len(data) - offset < 13:
            raise ValueError("数据不足")
        
        # 解析表头
        table_id = data[offset]
        if table_id != 0x3E:
            raise ValueError("不是 MPE 表")
        
        # Section syntax indicator 和 length
        syntax_length = struct.unpack('>H', data[offset + 1:offset + 3])[0]
        section_length = syntax_length & 0x0FFF
        
        # 验证 section 数据完整性
        if offset + 3 + section_length > len(data):
            raise ValueError("section 数据不完整")
        
        # MAC 地址
        mac_address = data[offset + 3:offset + 9]
        
        # 提取 payload（排除 CRC-32）
        payload = data[offset + 9:offset + 3 + section_length - 4]
        
        # 验证 CRC-32
        section_data = data[offset:offset + 3 + section_length]
        expected_crc = 0
        if len(section_data) >= 4:
            expected_crc = struct.unpack('>I', section_data[-4:])[0]
            calculated_crc = crc32(section_data[:-4])
            if expected_crc != calculated_crc:
                raise ValueError("CRC-32 校验失败")
        
        return MPEDatagram(
            table_id=table_id,
            mac_address=mac_address,
            payload=payload,
            crc32=expected_crc
        )
