"""
PMT (Program Map Table) parser
"""

import struct
from typing import List

from dvb_parser.psi.models import PMT, PMTStream
from dvb_parser.utils.crc import crc32


class PMTParser:
    """PMT parser"""
    
    @staticmethod
    def parse(data: bytes, offset: int = 0) -> PMT:
        """
        Parse PMT section
        
        Args:
            data: Raw section data
            offset: Start offset
        
        Returns:
            PMT object
        
        Raises:
            ValueError: CRC-32 checksum failure or invalid data
        """
        if len(data) - offset < 16:
            raise ValueError("数据不足")
        
        # Parse header
        table_id = data[offset]
        if table_id != 0x02:
            raise ValueError("不是 PMT 表")
        
        # Section syntax indicator and length
        syntax_length = struct.unpack('>H', data[offset + 1:offset + 3])[0]
        section_length = syntax_length & 0x0FFF
        
        # Program number
        program_number = struct.unpack('>H', data[offset + 3:offset + 5])[0]
        
        # Version and current/next indicator
        version_current = data[offset + 5]
        version_number = (version_current >> 1) & 0x1F
        current_next_indicator = bool(version_current & 0x01)
        
        # Section numbers
        section_number = data[offset + 6]
        last_section_number = data[offset + 7]
        
        # PCR PID
        pcr_pid = struct.unpack('>H', data[offset + 8:offset + 10])[0] & 0x1FFF
        
        # Program info length
        info_length = struct.unpack('>H', data[offset + 10:offset + 12])[0] & 0x03FF
        
        # Parse program-level descriptors
        descriptors = []
        desc_offset = offset + 12
        desc_end = desc_offset + info_length
        
        while desc_offset < desc_end and desc_offset + 2 <= len(data):
            desc_tag = data[desc_offset]
            desc_length = data[desc_offset + 1]
            desc_data = data[desc_offset:desc_offset + 2 + desc_length]
            descriptors.append(desc_data)
            desc_offset += 2 + desc_length
        
        # Skip program descriptors
        current_offset = offset + 12 + info_length
        
        # Parse streams
        streams = []
        streams_end = offset + 3 + section_length - 4  # 4 bytes for CRC-32
        
        while current_offset < streams_end:
            if current_offset + 5 > len(data):
                break
            
            stream_type = data[current_offset]
            pid = struct.unpack('>H', data[current_offset + 1:current_offset + 3])[0] & 0x1FFF
            es_info_length = struct.unpack('>H', data[current_offset + 3:current_offset + 5])[0] & 0x03FF
            
            # Parse ES descriptors
            descriptors = []
            desc_end = current_offset + 5 + es_info_length
            desc_offset = current_offset + 5
            
            while desc_offset < desc_end and desc_offset + 2 <= len(data):
                desc_tag = data[desc_offset]
                desc_length = data[desc_offset + 1]
                desc_data = data[desc_offset:desc_offset + 2 + desc_length]
                descriptors.append(desc_data)
                desc_offset += 2 + desc_length
            
            streams.append(PMTStream(
                stream_type=stream_type,
                pid=pid,
                descriptors=descriptors
            ))
            
            current_offset = desc_end
        
        # Verify CRC-32
        section_data = data[offset:offset + 3 + section_length]
        if len(section_data) < 3 + section_length:
            raise ValueError("数据截断，无法完成 CRC-32 校验")
        expected_crc = struct.unpack('>I', section_data[-4:])[0]
        calculated_crc = crc32(section_data[:-4])
        if expected_crc != calculated_crc:
            raise ValueError("CRC-32 校验失败")
        
        return PMT(
            table_id=table_id,
            version_number=version_number,
            current_next_indicator=current_next_indicator,
            section_number=section_number,
            last_section_number=last_section_number,
            program_number=program_number,
            pcr_pid=pcr_pid,
            descriptors=descriptors,  # Program-level descriptors
            streams=streams
        )
