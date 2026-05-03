"""NIP (Network Independent Protocol) parser"""

import struct

from dvb_parser.nip.models import NIPDataUnit, NIPStreaming, NIPCarousel


class NIPParser:
    """NIP 解析器"""

    @staticmethod
    def parse_piping(data: bytes, offset: int = 0) -> NIPDataUnit:
        """
        解析数据管道

        Args:
            data: 原始数据
            offset: 起始偏移

        Returns:
            NIPDataUnit 对象
        """
        payload = data[offset:]

        return NIPDataUnit(
            method="piping",
            payload=payload
        )

    @staticmethod
    def parse_streaming(data: bytes, offset: int = 0) -> NIPStreaming:
        """
        解析数据流

        Args:
            data: 原始数据
            offset: 起始偏移

        Returns:
            NIPStreaming 对象

        Raises:
            ValueError: 数据无效
        """
        if len(data) - offset < 5:
            raise ValueError("数据不足")

        synchronous = bool(data[offset])
        data_identifier = struct.unpack('>H', data[offset + 1:offset + 3])[0]
        payload = data[offset + 3:]

        return NIPStreaming(
            synchronous=synchronous,
            data_identifier=data_identifier,
            payload=payload
        )

    @staticmethod
    def parse_carousel(data: bytes, offset: int = 0) -> NIPCarousel:
        """
        解析数据循环

        Args:
            data: 原始数据
            offset: 起始偏移

        Returns:
            NIPCarousel 对象

        Raises:
            ValueError: 数据无效
        """
        if len(data) - offset < 8:
            raise ValueError("数据不足")

        download_id = struct.unpack('>I', data[offset:offset + 4])[0]
        block_size = struct.unpack('>H', data[offset + 4:offset + 6])[0]

        if block_size == 0:
            raise ValueError("block_size cannot be 0")

        blocks = []
        current_offset = offset + 6

        while current_offset + block_size <= len(data):
            block = data[current_offset:current_offset + block_size]
            blocks.append(block)
            current_offset += block_size

        return NIPCarousel(
            download_id=download_id,
            block_size=block_size,
            blocks=blocks
        )
