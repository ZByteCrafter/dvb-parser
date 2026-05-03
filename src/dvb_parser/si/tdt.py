"""
TDT (Time and Date Table) and TOT (Time Offset Table) parser
"""

import struct
from typing import Union

from dvb_parser.si.models import TDT, TOT
from dvb_parser.utils.crc import crc32


class TDTParser:
    """TDT/TOT parser"""

    @staticmethod
    def parse(data: bytes, offset: int = 0) -> Union[TDT, TOT]:
        """
        Parse TDT or TOT section

        Args:
            data: Raw data
            offset: Start offset

        Returns:
            TDT or TOT object

        Raises:
            ValueError: Invalid data or CRC check failure
        """
        if len(data) - offset < 7:
            raise ValueError("Insufficient data")

        # Parse header
        table_id = data[offset]

        if table_id not in (0x70, 0x73):
            raise ValueError("Not a TDT or TOT table")

        # Section syntax indicator and length
        syntax_length = struct.unpack('>H', data[offset + 1:offset + 3])[0]
        section_length = syntax_length & 0x0FFF

        # Parse UTC time (MJD + BCD)
        mjd = struct.unpack('>H', data[offset + 3:offset + 5])[0]
        bcd_time = data[offset + 5:offset + 8]
        utc_time = TDTParser._mjd_bcd_to_timestamp(mjd, bcd_time)

        if table_id == 0x70:  # TDT
            return TDT(
                table_id=table_id,
                utc_time=utc_time
            )
        elif table_id == 0x73:  # TOT
            # Parse descriptors
            descriptors = []
            descriptors_length = struct.unpack('>H', data[offset + 8:offset + 10])[0] & 0x0FFF

            current_offset = offset + 10
            desc_end = current_offset + descriptors_length

            while current_offset < desc_end and current_offset + 2 <= len(data):
                desc_tag = data[current_offset]
                desc_length = data[current_offset + 1]
                desc_data = data[current_offset:current_offset + 2 + desc_length]
                descriptors.append(desc_data)
                current_offset += 2 + desc_length

            # Verify CRC-32
            section_data = data[offset:offset + 3 + section_length]
            if len(section_data) >= 4:
                expected_crc = struct.unpack('>I', section_data[-4:])[0]
                calculated_crc = crc32(section_data[:-4])
                if expected_crc != calculated_crc:
                    raise ValueError("CRC-32 check failed")

            return TOT(
                table_id=table_id,
                utc_time=utc_time,
                descriptors=descriptors
            )

        raise ValueError("Not a TDT or TOT table")

    @staticmethod
    def _mjd_bcd_to_timestamp(mjd: int, bcd_time: bytes) -> int:
        """MJD + BCD time to UTC timestamp (seconds since midnight)"""
        # BCD time
        hour = ((bcd_time[0] >> 4) * 10) + (bcd_time[0] & 0x0F)
        minute = ((bcd_time[1] >> 4) * 10) + (bcd_time[1] & 0x0F)
        second = ((bcd_time[2] >> 4) * 10) + (bcd_time[2] & 0x0F)

        # Simplified: return seconds since midnight
        return hour * 3600 + minute * 60 + second
