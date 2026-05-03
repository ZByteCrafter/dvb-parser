"""
GSE (Generic Stream Encapsulation) parser
"""

import struct
from typing import Optional

from dvb_parser.gse.models import GSEPacket
from dvb_parser.utils.crc import crc32


class GSEParser:
    """GSE 解析器"""
    
    @staticmethod
    def parse(data: bytes, offset: int = 0) -> GSEPacket:
        """
        解析 GSE 包
        
        Args:
            data: 原始数据
            offset: 起始偏移
        
        Returns:
            GSEPacket 对象
        
        Raises:
            ValueError: CRC-32 校验失败或数据无效
        """
        if len(data) - offset < 6:
            raise ValueError("数据不足")
        
        # 解析第一个字节
        first_byte = data[offset]
        start = bool(first_byte & 0x80)
        end = bool(first_byte & 0x40)
        label_type = (first_byte >> 4) & 0x03
        
        # 保留字节
        # data[offset + 1] is reserved
        
        # 解析协议类型
        protocol_type = struct.unpack('>H', data[offset + 2:offset + 4])[0]
        
        # 解析总长度（如果存在）
        total_length = None
        current_offset = offset + 4
        
        if start:
            total_length = struct.unpack('>H', data[current_offset:current_offset + 2])[0]
            current_offset += 2
        
        # 解析 Label（如果存在）
        label = None
        if label_type == 1:  # 6 字节 Label
            if len(data) - current_offset < 6:
                raise ValueError("数据不足，无法读取 6 字节 Label")
            label = data[current_offset:current_offset + 6]
            current_offset += 6
        elif label_type == 2:  # 3 字节 Label
            if len(data) - current_offset < 3:
                raise ValueError("数据不足，无法读取 3 字节 Label")
            label = data[current_offset:current_offset + 3]
            current_offset += 3
        elif label_type == 3:  # Label Extension
            if len(data) - current_offset < 1:
                raise ValueError("数据不足，无法读取 Label Extension 长度")
            ext_length = data[current_offset]
            current_offset += 1
            if len(data) - current_offset < ext_length:
                raise ValueError("数据不足，无法读取 Label Extension 数据")
            label = data[current_offset:current_offset + ext_length]
            current_offset += ext_length
        
        # 计算 payload 长度
        # total_length = header + label + payload (excluding CRC)
        header_length = current_offset - offset
        crc_length = 4
        
        if total_length is not None:
            payload_length = total_length - header_length
        else:
            # 对于分片包，payload 延伸到 CRC-32 之前
            payload_length = len(data) - offset - header_length - crc_length
        
        if payload_length < 0:
            raise ValueError("无效的包长度")
        
        # 验证 payload 长度不超过实际数据
        if current_offset + payload_length > len(data):
            raise ValueError("数据不足，无法读取 payload")
        
        # 提取 payload
        payload = data[current_offset:current_offset + payload_length]
        current_offset += payload_length
        
        # 验证 CRC-32
        if current_offset + 4 > len(data):
            raise ValueError("数据不足，无法读取 CRC-32")
        
        crc32_value = struct.unpack('>I', data[current_offset:current_offset + 4])[0]
        calculated_crc = crc32(data[offset:current_offset])
        
        if crc32_value != calculated_crc:
            raise ValueError("CRC-32 校验失败")
        
        return GSEPacket(
            start=start,
            end=end,
            label_type=label_type,
            protocol_type=protocol_type,
            total_length=total_length,
            label=label,
            payload=payload,
            crc32=crc32_value
        )
