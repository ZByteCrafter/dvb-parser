import pytest
from dvb_parser.si.sdt import SDTParser


class TestSDTParser:
    def _make_sdt_section(self, table_id, ts_id, version, original_network_id, services_bytes):
        """Build a valid SDT section with correct CRC.

        SDT section layout:
        - byte 0: table_id
        - bytes 1-2: syntax_indicator(1) + reserved(3) + section_length(12)
        - bytes 3-4: transport_stream_id
        - byte 5: reserved(2) + version_number(5) + current_next_indicator(1)
        - byte 6: section_number
        - byte 7: last_section_number
        - bytes 8-9: original_network_id
        - byte 10: reserved_future_use
        - bytes 11+: service entries
        - last 4 bytes: CRC-32
        """
        from dvb_parser.utils.crc import crc32

        # section_length = everything after bytes 1-2: ts_id(2) + version(1) + section_number(1)
        #   + last_section_number(1) + original_network_id(2) + reserved(1) + services + CRC(4)
        section_length = 2 + 1 + 1 + 1 + 2 + 1 + len(services_bytes) + 4

        header = bytes([
            table_id,
            0b10110000 | (section_length >> 8), section_length & 0xFF,
            ts_id >> 8, ts_id & 0xFF,
            (version << 1) | 0x01,
            0x00,  # section_number
            0x00,  # last_section_number
            original_network_id >> 8, original_network_id & 0xFF,
            0xFF,  # reserved_future_use
        ])
        data_before_crc = header + services_bytes
        crc_value = crc32(data_before_crc)
        return data_before_crc + crc_value.to_bytes(4, 'big')

    def _make_service_entry(self, service_id, descriptors_bytes, eit_schedule=False, eit_pf=True,
                            running_status=0, free_ca=False):
        """Build a service entry for the SDT services loop."""
        eit_flags = 0
        if eit_schedule:
            eit_flags |= 0x02
        if eit_pf:
            eit_flags |= 0x01

        status_free_desc = (running_status << 5) | (0x10 if free_ca else 0x00) | (len(descriptors_bytes) >> 8)
        return bytes([
            service_id >> 8, service_id & 0xFF,
            0xFC | eit_flags,  # reserved(6) + EIT flags(2)
            status_free_desc, len(descriptors_bytes) & 0xFF,
        ]) + descriptors_bytes

    def _make_service_descriptor(self, service_type, provider_name, service_name):
        """Build a service descriptor (tag=0x48)."""
        provider_bytes = provider_name.encode('utf-8')
        name_bytes = service_name.encode('utf-8')
        desc_data = bytes([service_type, len(provider_bytes)]) + provider_bytes + bytes([len(name_bytes)]) + name_bytes
        return bytes([0x48, len(desc_data)]) + desc_data

    def test_parse_valid_sdt(self):
        """测试解析有效的 SDT"""
        descriptor = self._make_service_descriptor(1, "TV", "HD")
        service = self._make_service_entry(1, descriptor)
        section_data = self._make_sdt_section(
            table_id=0x42, ts_id=1, version=1, original_network_id=1,
            services_bytes=service
        )

        sdt = SDTParser.parse(section_data)

        assert sdt.table_id == 0x42
        assert sdt.transport_stream_id == 1
        assert sdt.original_network_id == 1
        assert sdt.version_number == 1
        assert sdt.current_next_indicator is True
        assert sdt.section_number == 0
        assert sdt.last_section_number == 0
        assert len(sdt.services) == 1
        assert sdt.services[0].service_id == 1
        assert sdt.services[0].eit_present_following_flag is True
        assert sdt.services[0].service_type == 1
        assert sdt.services[0].provider_name == "TV"
        assert sdt.services[0].service_name == "HD"

    def test_parse_sdt_other_ts(self):
        """测试解析其他 TS 的 SDT"""
        empty_descriptor = bytes([0x00, 0x00])  # unknown descriptor, tag=0, length=0
        service = self._make_service_entry(1, empty_descriptor)
        section_data = self._make_sdt_section(
            table_id=0x46, ts_id=2, version=1, original_network_id=1,
            services_bytes=service
        )

        sdt = SDTParser.parse(section_data)

        assert sdt.table_id == 0x46
        assert sdt.transport_stream_id == 2
        assert len(sdt.services) == 1
        assert sdt.services[0].service_id == 1
        assert sdt.services[0].service_type == 0  # no service descriptor

    def test_parse_invalid_table_id(self):
        """测试无效的 table_id"""
        section_data = bytes([0x00] * 12)

        with pytest.raises(ValueError, match="不是 SDT 表"):
            SDTParser.parse(section_data)

    def test_parse_insufficient_data(self):
        """测试数据不足"""
        section_data = bytes([0x42, 0x00])

        with pytest.raises(ValueError, match="数据不足"):
            SDTParser.parse(section_data)

    def test_parse_crc_error(self):
        """测试 CRC 校验失败"""
        descriptor = self._make_service_descriptor(1, "TV", "HD")
        service = self._make_service_entry(1, descriptor)
        section_data = bytearray(self._make_sdt_section(
            table_id=0x42, ts_id=1, version=1, original_network_id=1,
            services_bytes=service
        ))
        # Corrupt CRC
        section_data[-1] ^= 0xFF

        with pytest.raises(ValueError, match="CRC-32 校验失败"):
            SDTParser.parse(bytes(section_data))

    def test_parse_multiple_services(self):
        """测试解析多个业务"""
        desc1 = self._make_service_descriptor(1, "TV", "HD")
        desc2 = self._make_service_descriptor(2, "ABC", "X")
        service1 = self._make_service_entry(1, desc1)
        service2 = self._make_service_entry(2, desc2)
        section_data = self._make_sdt_section(
            table_id=0x42, ts_id=1, version=1, original_network_id=1,
            services_bytes=service1 + service2
        )

        sdt = SDTParser.parse(section_data)

        assert len(sdt.services) == 2
        assert sdt.services[0].service_id == 1
        assert sdt.services[0].service_name == "HD"
        assert sdt.services[0].provider_name == "TV"
        assert sdt.services[1].service_id == 2
        assert sdt.services[1].service_type == 2
        assert sdt.services[1].provider_name == "ABC"
        assert sdt.services[1].service_name == "X"

    def test_parse_with_offset(self):
        """测试带偏移量解析"""
        descriptor = self._make_service_descriptor(1, "Provider", "Channel")
        service = self._make_service_entry(42, descriptor)
        sdt_bytes = self._make_sdt_section(
            table_id=0x42, ts_id=100, version=3, original_network_id=200,
            services_bytes=service
        )
        # Prepend padding to test offset
        padded = bytes(5) + sdt_bytes

        sdt = SDTParser.parse(padded, offset=5)

        assert sdt.table_id == 0x42
        assert sdt.transport_stream_id == 100
        assert sdt.original_network_id == 200
        assert sdt.version_number == 3
        assert len(sdt.services) == 1
        assert sdt.services[0].service_id == 42
        assert sdt.services[0].provider_name == "Provider"
        assert sdt.services[0].service_name == "Channel"
