"""ULE (Unidirectional Lightweight Encapsulation) parser"""

import struct
from typing import List

from dvb_parser.ule.models import ULESNDU
from dvb_parser.utils.crc import crc32


class ULEParser:
    """ULE 解析器"""

    @staticmethod
    def parse(data: bytes, offset: int = 0) -> ULESNDU:
        """
        解析 ULE SNDU

        Args:
            data: 原始数据
            offset: 起始偏移

        Returns:
            ULESNDU 对象

        Raises:
            ValueError: CRC-32 校验失败或数据无效
        """
        if len(data) - offset < 4:
            raise ValueError("数据不足")

        # 解析 Length/Type
        length_or_type = struct.unpack('>H', data[offset:offset + 2])[0]

        current_offset = offset + 2

        # 解析目标 MAC 地址（如果 Length/Type < 1536）
        destination_mac = None
        if length_or_type < 1536:
            if current_offset + 6 > len(data):
                raise ValueError("数据不足")
            destination_mac = data[current_offset:current_offset + 6]
            current_offset += 6

        # 解析扩展头（如果有）
        extension_headers: List[bytes] = []

        # 提取 payload
        # 对于 Type 模式，payload 延伸到 CRC-32 之前
        # 对于 Length 模式，payload 长度由 Length 决定
        crc_length = 4

        if length_or_type >= 1536:
            # Type 模式
            payload_length = len(data) - offset - (current_offset - offset) - crc_length
        else:
            # Length 模式: Length = MAC(6) + Payload + CRC(4)
            payload_length = length_or_type - (current_offset - offset - 2) - crc_length

        if payload_length < 0:
            raise ValueError("无效的包长度")

        payload = data[current_offset:current_offset + payload_length]
        current_offset += payload_length

        # 验证 CRC-32
        if current_offset + 4 > len(data):
            raise ValueError("数据不足，无法读取 CRC-32")

        crc32_value = struct.unpack('>I', data[current_offset:current_offset + 4])[0]
        calculated_crc = crc32(data[offset:current_offset])

        if crc32_value != calculated_crc:
            raise ValueError("CRC-32 校验失败")

        return ULESNDU(
            length_or_type=length_or_type,
            destination_mac=destination_mac,
            extension_headers=extension_headers,
            payload=payload,
            crc32=crc32_value
        )
