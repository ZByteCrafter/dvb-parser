import pytest
from dvb_parser.si.eit import EITParser
from dvb_parser.si.models import EIT, EITEvent


class TestEITParser:
    def test_parse_present_following(self):
        """Test parsing present/following events"""
        # Construct EIT section
        section_data = bytes([
            0x4E,                    # table_id (present/following, current TS)
            0b10110000, 0x24,        # syntax_indicator=1, length=36
            0x00, 0x01,              # service_id
            0b11000001,              # version=1, current_next=1
            0x00, 0x01,              # transport_stream_id
            0x00, 0x01,              # original_network_id
            0x00,                    # section_number
            0x00,                    # last_section_number
            # Event entry
            0x00, 0x01,              # event_id
            # Start time (MJD + BCD)
            0x58, 0x00,              # MJD
            0x12, 0x00, 0x00,        # BCD time (12:00:00)
            # Duration (BCD)
            0x01, 0x30, 0x00,        # 1h30m
            0b00000101, 0b11000000,  # running_status=1, free_ca=0, descriptors_length=9
            # Short event descriptor
            0x4D, 0x07,              # descriptor_tag=0x4D, length=7
            0x65, 0x6E, 0x67,        # language_code="eng"
            0x03,                    # event_name_length=3
            0x45, 0x56, 0x54,        # event_name="EVT"
            0x00,                    # text_length=0
            # CRC-32 placeholder
            0x00, 0x00, 0x00, 0x00
        ])

        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')

        eit = EITParser.parse(section_data)

        assert eit.table_id == 0x4E
        assert eit.service_id == 1
        assert len(eit.events) == 1
        assert eit.events[0].event_id == 1
        assert eit.events[0].event_name == "EVT"

    def test_parse_schedule(self):
        """Test parsing schedule events"""
        section_data = bytes([
            0x50,                    # table_id (schedule, current TS)
            0b10110000, 0x1A,        # syntax_indicator=1, length=26
            0x00, 0x01,              # service_id
            0b11000001,              # version=1, current_next=1
            0x00, 0x01,              # transport_stream_id
            0x00, 0x01,              # original_network_id
            0x00,                    # section_number
            0x00,                    # last_section_number
            # Event entry
            0x00, 0x01,              # event_id
            0x58, 0x00,              # MJD
            0x15, 0x30, 0x00,        # 15:30:00
            0x00, 0x45, 0x00,        # 45m
            0b00000001, 0b00000000,  # running_status=0, free_ca=0, descriptors_length=1
            0x00,                    # Empty descriptor placeholder
            # CRC-32
            0x00, 0x00, 0x00, 0x00
        ])

        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')

        eit = EITParser.parse(section_data)

        assert eit.table_id == 0x50
        assert len(eit.events) == 1

    def test_parse_invalid_table_id(self):
        """Test that invalid table_id raises ValueError"""
        section_data = bytes([
            0x00,  # Invalid table_id
            0b10110000, 0x10,
            0x00, 0x01,
            0b11000001,
            0x00, 0x01,
            0x00, 0x01,
            0x00,
            0x00,
            0x00, 0x00, 0x00, 0x00
        ])

        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')

        with pytest.raises(ValueError):
            EITParser.parse(section_data)

    def test_parse_insufficient_data(self):
        """Test that insufficient data raises ValueError"""
        section_data = bytes([0x4E, 0x00])
        with pytest.raises(ValueError):
            EITParser.parse(section_data)

    def test_parse_duration_conversion(self):
        """Test BCD duration conversion"""
        assert EITParser._bcd_to_duration(bytes([0x01, 0x30, 0x00])) == 5400  # 1h30m = 5400s
        assert EITParser._bcd_to_duration(bytes([0x00, 0x45, 0x00])) == 2700  # 45m = 2700s
        assert EITParser._bcd_to_duration(bytes([0x02, 0x15, 0x30])) == 8130  # 2h15m30s

    def test_parse_multiple_events(self):
        """Test parsing multiple events"""
        section_data = bytes([
            0x50,                    # table_id (schedule, current TS)
            0b10110000, 0x2E,        # syntax_indicator=1, length=46
            0x00, 0x01,              # service_id
            0b11000001,              # version=1, current_next=1
            0x00, 0x01,              # transport_stream_id
            0x00, 0x01,              # original_network_id
            0x00,                    # section_number
            0x00,                    # last_section_number
            # Event 1
            0x00, 0x01,              # event_id
            0x58, 0x00,              # MJD
            0x12, 0x00, 0x00,        # 12:00:00
            0x01, 0x00, 0x00,        # 1h
            0b00000000, 0b00000000,  # running_status=0, free_ca=0, descriptors_length=0
            # Event 2
            0x00, 0x02,              # event_id
            0x58, 0x00,              # MJD
            0x13, 0x00, 0x00,        # 13:00:00
            0x01, 0x30, 0x00,        # 1h30m
            0b00000000, 0b00000000,  # running_status=0, free_ca=0, descriptors_length=0
            # CRC-32
            0x00, 0x00, 0x00, 0x00
        ])

        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')

        eit = EITParser.parse(section_data)

        assert len(eit.events) == 2
        assert eit.events[0].event_id == 1
        assert eit.events[1].event_id == 2
