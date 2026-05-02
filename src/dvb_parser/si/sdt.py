"""
SDT (Service Description Table) parser
"""

import struct
from typing import List

from dvb_parser.si.models import SDT, SDTService
from dvb_parser.utils.crc import crc32


class SDTParser:
    """SDT 解析器"""

    @staticmethod
    def parse(data: bytes, offset: int = 0) -> SDT:
        """
        解析 SDT section

        Args:
            data: 原始 section 数据
            offset: 起始偏移

        Returns:
            SDT 对象

        Raises:
            ValueError: CRC-32 校验失败或数据无效
        """
        if len(data) - offset < 12:
            raise ValueError("数据不足")

        # 解析表头
        table_id = data[offset]
        if table_id not in (0x42, 0x46):
            raise ValueError("不是 SDT 表")

        # Section syntax indicator 和 length
        syntax_length = struct.unpack('>H', data[offset + 1:offset + 3])[0]
        section_length = syntax_length & 0x0FFF

        # Transport stream ID
        ts_id = struct.unpack('>H', data[offset + 3:offset + 5])[0]

        # Version 和 current/next indicator
        version_current = data[offset + 5]
        version_number = (version_current >> 1) & 0x1F
        current_next_indicator = bool(version_current & 0x01)

        # Section numbers
        section_number = data[offset + 6]
        last_section_number = data[offset + 7]

        # Original network ID
        original_network_id = struct.unpack('>H', data[offset + 8:offset + 10])[0]

        # 解析业务列表
        services = []
        services_end = offset + 3 + section_length - 4  # 4 bytes for CRC-32

        current_offset = offset + 11  # 跳过固定头部

        while current_offset < services_end:
            if current_offset + 5 > len(data):
                break

            # 解析业务信息
            service_id = struct.unpack('>H', data[current_offset:current_offset + 2])[0]
            eit_schedule = bool(data[current_offset + 2] & 0x02)
            eit_present_following = bool(data[current_offset + 2] & 0x01)
            running_status = (data[current_offset + 3] >> 5) & 0x07
            free_ca_mode = bool(data[current_offset + 3] & 0x10)
            descriptors_length = struct.unpack('>H', data[current_offset + 3:current_offset + 5])[0] & 0x0FFF

            # 提取描述符
            descriptors = []
            desc_end = current_offset + 5 + descriptors_length
            desc_offset = current_offset + 5

            service_type = 0
            service_name = ""
            provider_name = ""

            while desc_offset < desc_end and desc_offset + 2 <= len(data):
                desc_tag = data[desc_offset]
                desc_length = data[desc_offset + 1]
                desc_data = data[desc_offset:desc_offset + 2 + desc_length]
                descriptors.append(desc_data)

                # 解析业务描述符
                if desc_tag == 0x48 and desc_length >= 3:  # Service descriptor
                    service_type = data[desc_offset + 2]
                    provider_length = data[desc_offset + 3]
                    if desc_offset + 4 + provider_length <= desc_end:
                        provider_name = data[desc_offset + 4:desc_offset + 4 + provider_length].decode('utf-8', errors='replace')
                    service_name_length = data[desc_offset + 4 + provider_length]
                    name_offset = desc_offset + 5 + provider_length
                    if name_offset + service_name_length <= desc_end:
                        service_name = data[name_offset:name_offset + service_name_length].decode('utf-8', errors='replace')

                desc_offset += 2 + desc_length

            services.append(SDTService(
                service_id=service_id,
                eit_schedule_flag=eit_schedule,
                eit_present_following_flag=eit_present_following,
                running_status=running_status,
                free_ca_mode=free_ca_mode,
                descriptors=descriptors,
                service_type=service_type,
                service_name=service_name,
                provider_name=provider_name
            ))

            current_offset = desc_end

        # 验证 CRC-32
        section_data = data[offset:offset + 3 + section_length]
        if len(section_data) >= 4:
            expected_crc = struct.unpack('>I', section_data[-4:])[0]
            calculated_crc = crc32(section_data[:-4])
            if expected_crc != calculated_crc:
                raise ValueError("CRC-32 校验失败")

        return SDT(
            table_id=table_id,
            transport_stream_id=ts_id,
            original_network_id=original_network_id,
            version_number=version_number,
            current_next_indicator=current_next_indicator,
            section_number=section_number,
            last_section_number=last_section_number,
            services=services
        )
