"""
PAT (Program Association Table) parser
"""

import struct
from typing import List

from dvb_parser.psi.models import PAT, PATEntry
from dvb_parser.utils.crc import crc32


class PATParser:
    """PAT parser"""

    @staticmethod
    def parse(data: bytes, offset: int = 0) -> PAT:
        """
        Parse PAT section

        Args:
            data: Raw section data
            offset: Start offset

        Returns:
            PAT object

        Raises:
            ValueError: CRC-32 checksum failure or invalid data
        """
        if len(data) - offset < 12:
            raise ValueError("数据不足")

        # Parse header
        table_id = data[offset]
        if table_id != 0x00:
            raise ValueError("不是 PAT 表")

        # Section syntax indicator and length
        syntax_length = struct.unpack('>H', data[offset + 1:offset + 3])[0]
        syntax_indicator = (syntax_length >> 15) & 0x01
        section_length = syntax_length & 0x0FFF

        # Transport stream ID
        ts_id = struct.unpack('>H', data[offset + 3:offset + 5])[0]

        # Version and current/next indicator
        version_current = data[offset + 5]
        version_number = (version_current >> 1) & 0x1F
        current_next_indicator = bool(version_current & 0x01)

        # Section numbers
        section_number = data[offset + 6]
        last_section_number = data[offset + 7]

        # Parse entries (excluding CRC-32)
        entries: List[PATEntry] = []
        entries_end = offset + 3 + section_length - 4  # 4 bytes for CRC-32

        current_offset = offset + 8
        while current_offset < entries_end:
            if current_offset + 4 > len(data):
                break

            program_number = struct.unpack('>H', data[current_offset:current_offset + 2])[0]
            pid = struct.unpack('>H', data[current_offset + 2:current_offset + 4])[0] & 0x1FFF

            entries.append(PATEntry(
                program_number=program_number,
                pid=pid
            ))
            current_offset += 4

        # Verify CRC-32
        section_data = data[offset:offset + 3 + section_length]
        if len(section_data) >= 4:
            expected_crc = struct.unpack('>I', section_data[-4:])[0]
            calculated_crc = crc32(section_data[:-4])
            if expected_crc != calculated_crc:
                raise ValueError("CRC-32 校验失败")

        return PAT(
            table_id=table_id,
            transport_stream_id=ts_id,
            version_number=version_number,
            current_next_indicator=current_next_indicator,
            section_number=section_number,
            last_section_number=last_section_number,
            entries=entries
        )
