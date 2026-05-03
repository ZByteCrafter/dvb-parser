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
        # Type 模式下，bit 0 为 Extension Present 标志
        extension_headers: List[bytes] = []
        has_extension = length_or_type >= 1536 and (length_or_type & 0x01) != 0
        if has_extension:
            # 扩展头链: [type(1)][length(1)][data(length)] ... 直到 type==0x00
            while current_offset < len(data):
                ext_type = data[current_offset]
                current_offset += 1
                if ext_type == 0x00:
                    break
                if current_offset >= len(data):
                    raise ValueError("扩展头数据不足")
                ext_length = data[current_offset]
                current_offset += 1
                if current_offset + ext_length > len(data):
                    raise ValueError("扩展头数据不足")
                ext_data = data[current_offset:current_offset + ext_length]
                current_offset += ext_length
                extension_headers.append(bytes([ext_type, ext_length]) + ext_data)
            # 清除 Extension Present 位，存储实际协议类型
            length_or_type &= 0xFFFE

        # 提取 payload
        # 对于 Type 模式，payload 延伸到 CRC-32 之前
        # 对于 Length 模式，payload 长度由 Length 决定
        crc_length = 4

        if length_or_type >= 1536:
            # Type 模式
            if current_offset + crc_length > len(data):
                raise ValueError("Type 模式数据不足，无法读取 CRC-32")
            payload_length = len(data) - current_offset - crc_length
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
