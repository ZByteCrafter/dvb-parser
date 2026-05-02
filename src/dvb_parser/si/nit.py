"""
NIT (Network Information Table) parser
"""

import struct
from typing import List

from dvb_parser.si.models import NIT, NITTransportStream
from dvb_parser.utils.crc import crc32


class NITParser:
    """NIT 解析器"""

    @staticmethod
    def parse(data: bytes, offset: int = 0) -> NIT:
        """
        解析 NIT section

        Args:
            data: 原始 section 数据
            offset: 起始偏移

        Returns:
            NIT 对象

        Raises:
            ValueError: CRC-32 校验失败或数据无效
        """
        if len(data) - offset < 12:
            raise ValueError("数据不足")

        # 解析表头
        table_id = data[offset]
        if table_id not in (0x40, 0x41):
            raise ValueError("不是 NIT 表")

        # Section syntax indicator 和 length
        syntax_length = struct.unpack('>H', data[offset + 1:offset + 3])[0]
        section_length = syntax_length & 0x0FFF

        # Network ID
        network_id = struct.unpack('>H', data[offset + 3:offset + 5])[0]

        # Version 和 current/next indicator
        version_current = data[offset + 5]
        version_number = (version_current >> 1) & 0x1F
        current_next_indicator = bool(version_current & 0x01)

        # Section numbers
        section_number = data[offset + 6]
        last_section_number = data[offset + 7]

        # 解析网络描述符
        network_descriptors_length = struct.unpack('>H', data[offset + 8:offset + 10])[0] & 0x0FFF

        network_name = ""
        desc_offset = offset + 10
        desc_end = desc_offset + network_descriptors_length

        while desc_offset < desc_end and desc_offset + 2 <= len(data):
            desc_tag = data[desc_offset]
            desc_length = data[desc_offset + 1]

            # 解析网络名称描述符
            if desc_tag == 0x40 and desc_length > 0:
                network_name = data[desc_offset + 2:desc_offset + 2 + desc_length].decode('utf-8', errors='replace')

            desc_offset += 2 + desc_length

        # 解析传输流列表
        transport_streams = []
        ts_loop_length = struct.unpack('>H', data[desc_end:desc_end + 2])[0] & 0x0FFF

        current_offset = desc_end + 2
        ts_end = current_offset + ts_loop_length

        while current_offset < ts_end:
            if current_offset + 6 > len(data):
                break

            # 解析传输流信息
            ts_id = struct.unpack('>H', data[current_offset:current_offset + 2])[0]
            original_network_id = struct.unpack('>H', data[current_offset + 2:current_offset + 4])[0]
            ts_descriptors_length = struct.unpack('>H', data[current_offset + 4:current_offset + 6])[0] & 0x0FFF

            # 提取描述符
            descriptors = []
            ts_desc_end = current_offset + 6 + ts_descriptors_length
            ts_desc_offset = current_offset + 6

            frequency = 0
            modulation = 0
            symbol_rate = 0
            polarization = 0

            while ts_desc_offset < ts_desc_end and ts_desc_offset + 2 <= len(data):
                desc_tag = data[ts_desc_offset]
                desc_length = data[ts_desc_offset + 1]
                desc_data = data[ts_desc_offset:ts_desc_offset + 2 + desc_length]
                descriptors.append(desc_data)

                # 解析卫星传输系统描述符
                if desc_tag == 0x43 and desc_length >= 11:  # Satellite delivery system descriptor
                    # 频率 (BCD 编码, 4 bytes, units of 10 kHz)
                    freq_bcd = data[ts_desc_offset + 2:ts_desc_offset + 6]
                    frequency = NITParser._bcd_to_int(freq_bcd) * 10000  # 10 kHz → Hz

                    # 极化方式
                    polarization = (data[ts_desc_offset + 8] >> 6) & 0x03

                    # 调制方式
                    modulation = data[ts_desc_offset + 9] & 0x03

                    # 符号率 (BCD 编码, 3 bytes, units of 10 sym/s)
                    sr_bcd = data[ts_desc_offset + 10:ts_desc_offset + 13]
                    symbol_rate = NITParser._bcd_to_int(sr_bcd) * 1000  # 10 sym/s → sym/s

                ts_desc_offset += 2 + desc_length

            transport_streams.append(NITTransportStream(
                transport_stream_id=ts_id,
                original_network_id=original_network_id,
                descriptors=descriptors,
                frequency=frequency,
                modulation=modulation,
                symbol_rate=symbol_rate,
                polarization=polarization
            ))

            current_offset = ts_desc_end

        # 验证 CRC-32
        section_data = data[offset:offset + 3 + section_length]
        if len(section_data) >= 4:
            expected_crc = struct.unpack('>I', section_data[-4:])[0]
            calculated_crc = crc32(section_data[:-4])
            if expected_crc != calculated_crc:
                raise ValueError("CRC-32 校验失败")

        return NIT(
            table_id=table_id,
            network_id=network_id,
            version_number=version_number,
            current_next_indicator=current_next_indicator,
            section_number=section_number,
            last_section_number=last_section_number,
            network_name=network_name,
            transport_streams=transport_streams
        )

    @staticmethod
    def _bcd_to_int(bcd_bytes: bytes) -> int:
        """BCD 编码转整数"""
        result = 0
        for byte in bcd_bytes:
            result = result * 100 + (byte >> 4) * 10 + (byte & 0x0F)
        return result
