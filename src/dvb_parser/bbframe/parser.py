"""BBFrame parser."""

import struct

from dvb_parser.bbframe.models import BBFrame, BBFrameHeader
from dvb_parser.utils.crc import crc8


class BBFrameParser:
    """BBFrame parser."""

    HEADER_SIZE = 10

    @staticmethod
    def parse(data: bytes, offset: int = 0) -> BBFrame:
        """
        Parse BBFrame.

        Args:
            data: Raw data.
            offset: Start offset.

        Returns:
            BBFrame object.

        Raises:
            ValueError: CRC-8 checksum failure or insufficient data.
        """
        if len(data) - offset < BBFrameParser.HEADER_SIZE:
            raise ValueError("数据不足")

        header_data = data[offset:offset + BBFrameParser.HEADER_SIZE]
        matype = header_data[0:2]
        upl = struct.unpack('>H', header_data[2:4])[0]
        dfl = struct.unpack('>H', header_data[4:6])[0]
        sync = header_data[6]
        syncd = struct.unpack('>H', header_data[7:9])[0]
        crc8_value = header_data[9]

        if crc8(header_data[:9]) != crc8_value:
            raise ValueError("CRC-8 校验失败")

        header = BBFrameHeader(
            matype=matype,
            upl=upl,
            dfl=dfl,
            sync=sync,
            syncd=syncd,
            crc8=crc8_value,
        )

        data_start = offset + BBFrameParser.HEADER_SIZE
        data_end = data_start + (dfl // 8)
        data_field = data[data_start:data_end]
        padding = data[data_end:]

        return BBFrame(
            header=header,
            data_field=data_field,
            padding=padding,
        )

    @staticmethod
    def parse_multiple(data: bytes) -> list:
        """
        Parse multiple BBFrames from data.

        Args:
            data: Raw data containing multiple BBFrames.

        Returns:
            List of BBFrame objects.
        """
        frames = []
        offset = 0

        while offset < len(data):
            try:
                frame = BBFrameParser.parse(data, offset)
                frames.append(frame)
                offset += BBFrameParser.HEADER_SIZE + (frame.header.dfl // 8)
            except ValueError:
                offset += 1

        return frames
