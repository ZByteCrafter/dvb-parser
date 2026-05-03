"""
EIT (Event Information Table) parser
"""

import struct
from typing import List

from dvb_parser.si.models import EIT, EITEvent
from dvb_parser.utils.crc import crc32


class EITParser:
    """EIT parser"""

    @staticmethod
    def parse(data: bytes, offset: int = 0) -> EIT:
        """
        Parse EIT section

        Args:
            data: Raw data
            offset: Start offset

        Returns:
            EIT object

        Raises:
            ValueError: CRC-32 check failure or invalid data
        """
        if len(data) - offset < 14:
            raise ValueError("Insufficient data")

        # Parse header
        table_id = data[offset]
        if table_id < 0x4E or table_id > 0x6F:
            raise ValueError("Not an EIT table")

        # Section syntax indicator and length
        syntax_length = struct.unpack('>H', data[offset + 1:offset + 3])[0]
        section_length = syntax_length & 0x0FFF

        # Service ID
        service_id = struct.unpack('>H', data[offset + 3:offset + 5])[0]

        # Version and current/next indicator
        version_current = data[offset + 5]
        version_number = (version_current >> 1) & 0x1F
        current_next_indicator = bool(version_current & 0x01)

        # Transport stream ID and original network ID
        ts_id = struct.unpack('>H', data[offset + 6:offset + 8])[0]
        original_network_id = struct.unpack('>H', data[offset + 8:offset + 10])[0]

        # Section numbers
        section_number = data[offset + 10]
        last_section_number = data[offset + 11]

        # Parse event list
        events = []
        events_end = offset + 3 + section_length - 4  # 4 bytes for CRC-32

        current_offset = offset + 12

        while current_offset < events_end:
            if current_offset + 12 > len(data):
                break

            # Parse event info
            event_id = struct.unpack('>H', data[current_offset:current_offset + 2])[0]

            # Parse start time (MJD + BCD)
            mjd = struct.unpack('>H', data[current_offset + 2:current_offset + 4])[0]
            bcd_time = data[current_offset + 4:current_offset + 7]
            start_time = EITParser._mjd_bcd_to_timestamp(mjd, bcd_time)

            # Parse duration (BCD)
            duration_bcd = data[current_offset + 7:current_offset + 10]
            duration = EITParser._bcd_to_duration(duration_bcd)

            # Running status and free CA mode
            running_free_ca = struct.unpack('>H', data[current_offset + 10:current_offset + 12])[0]
            running_status = (running_free_ca >> 13) & 0x07
            free_ca_mode = bool(running_free_ca & 0x1000)
            descriptors_length = running_free_ca & 0x0FFF

            # Extract descriptors
            descriptors = []
            desc_end = current_offset + 12 + descriptors_length
            desc_offset = current_offset + 12

            event_name = ""
            event_description = ""

            while desc_offset < desc_end and desc_offset + 2 <= len(data):
                desc_tag = data[desc_offset]
                desc_length = data[desc_offset + 1]
                desc_data = data[desc_offset:desc_offset + 2 + desc_length]
                descriptors.append(desc_data)

                # Parse short event descriptor (tag 0x4D)
                if desc_tag == 0x4D and desc_length >= 4 and desc_offset + 6 <= len(data):
                    language = data[desc_offset + 2:desc_offset + 5].decode('ascii', errors='replace')
                    name_length = data[desc_offset + 5]
                    if desc_offset + 6 + name_length <= desc_end:
                        event_name = data[desc_offset + 6:desc_offset + 6 + name_length].decode('utf-8', errors='replace')
                    desc_length_offset = desc_offset + 6 + name_length
                    if desc_length_offset < desc_end:
                        text_length = data[desc_length_offset]
                        if desc_length_offset + 1 + text_length <= desc_end:
                            event_description = data[desc_length_offset + 1:desc_length_offset + 1 + text_length].decode('utf-8', errors='replace')

                desc_offset += 2 + desc_length

            events.append(EITEvent(
                event_id=event_id,
                start_time=start_time,
                duration=duration,
                running_status=running_status,
                free_ca_mode=free_ca_mode,
                descriptors=descriptors,
                event_name=event_name,
                event_description=event_description
            ))

            current_offset = desc_end

        # Verify CRC-32
        section_data = data[offset:offset + 3 + section_length]
        if len(section_data) >= 4:
            expected_crc = struct.unpack('>I', section_data[-4:])[0]
            calculated_crc = crc32(section_data[:-4])
            if expected_crc != calculated_crc:
                raise ValueError("CRC-32 check failed")

        return EIT(
            table_id=table_id,
            service_id=service_id,
            transport_stream_id=ts_id,
            original_network_id=original_network_id,
            version_number=version_number,
            current_next_indicator=current_next_indicator,
            section_number=section_number,
            last_section_number=last_section_number,
            events=events
        )

    @staticmethod
    def _mjd_bcd_to_timestamp(mjd: int, bcd_time: bytes) -> int:
        """MJD + BCD time to UTC timestamp (seconds since midnight)"""
        # MJD to date
        y = int((mjd - 15078.2) / 365.25)
        m = int((mjd - 14956.1 - int(y * 365.25)) / 30.6001)
        d = mjd - 14956 - int(y * 365.25) - int(m * 30.6001)

        if m == 14 or m == 15:
            y += 1
            m -= 12

        y += 1900

        # BCD time
        hour = ((bcd_time[0] >> 4) * 10) + (bcd_time[0] & 0x0F)
        minute = ((bcd_time[1] >> 4) * 10) + (bcd_time[1] & 0x0F)
        second = ((bcd_time[2] >> 4) * 10) + (bcd_time[2] & 0x0F)

        # Simplified: return seconds since midnight
        return hour * 3600 + minute * 60 + second

    @staticmethod
    def _bcd_to_duration(bcd_duration: bytes) -> int:
        """BCD duration to seconds"""
        hour = ((bcd_duration[0] >> 4) * 10) + (bcd_duration[0] & 0x0F)
        minute = ((bcd_duration[1] >> 4) * 10) + (bcd_duration[1] & 0x0F)
        second = ((bcd_duration[2] >> 4) * 10) + (bcd_duration[2] & 0x0F)

        return hour * 3600 + minute * 60 + second
