import pytest
from dvb_parser.si.tdt import TDTParser
from dvb_parser.si.models import TDT, TOT


class TestTDTParser:
    def test_parse_tdt(self):
        """Test parsing TDT"""
        section_data = bytes([
            0x70,                    # table_id (TDT)
            0b10110000, 0x05,        # syntax_indicator=1, length=5
            # UTC time (MJD + BCD)
            0x58, 0x00,              # MJD
            0x12, 0x30, 0x00         # 12:30:00
        ])

        tdt = TDTParser.parse(section_data)

        assert tdt.table_id == 0x70
        assert tdt.utc_time == 12 * 3600 + 30 * 60  # 45000 seconds

    def test_parse_tot(self):
        """Test parsing TOT"""
        section_data = bytes([
            0x73,                    # table_id (TOT)
            0b10110000, 0x10,        # syntax_indicator=1, length=16
            # UTC time (MJD + BCD)
            0x58, 0x00,              # MJD
            0x15, 0x00, 0x00,        # 15:00:00
            # Descriptors
            0b11110000, 0x05,        # descriptors_length=5
            # Time offset descriptor
            0x58, 0x03,              # descriptor_tag=0x58, length=3
            0x43, 0x48, 0x4E,        # "CHN"
            # CRC-32 placeholder
            0x00, 0x00, 0x00, 0x00
        ])

        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')

        tot = TDTParser.parse(section_data)

        assert tot.table_id == 0x73
        assert tot.utc_time == 15 * 3600  # 54000 seconds
        assert len(tot.descriptors) == 1

    def test_parse_tdt_midnight(self):
        """Test parsing TDT at midnight"""
        section_data = bytes([
            0x70,                    # table_id (TDT)
            0b10110000, 0x05,        # syntax_indicator=1, length=5
            0x58, 0x00,              # MJD
            0x00, 0x00, 0x00         # 00:00:00
        ])

        tdt = TDTParser.parse(section_data)
        assert tdt.utc_time == 0

    def test_parse_tdt_end_of_day(self):
        """Test parsing TDT at 23:59:59"""
        section_data = bytes([
            0x70,                    # table_id (TDT)
            0b10110000, 0x05,        # syntax_indicator=1, length=5
            0x58, 0x00,              # MJD
            0x23, 0x59, 0x59         # 23:59:59
        ])

        tdt = TDTParser.parse(section_data)
        assert tdt.utc_time == 23 * 3600 + 59 * 60 + 59

    def test_parse_tot_multiple_descriptors(self):
        """Test parsing TOT with multiple descriptors"""
        section_data = bytes([
            0x73,                    # table_id (TOT)
            0b10110000, 0x15,        # syntax_indicator=1, length=21
            # UTC time (MJD + BCD)
            0x58, 0x00,              # MJD
            0x10, 0x00, 0x00,        # 10:00:00
            # Descriptors
            0b11110000, 0x0A,        # descriptors_length=10
            # Descriptor 1
            0x58, 0x03,              # descriptor_tag=0x58, length=3
            0x43, 0x48, 0x4E,        # "CHN"
            # Descriptor 2
            0x59, 0x03,              # descriptor_tag=0x59, length=3
            0x55, 0x53, 0x41,        # "USA"
            # CRC-32 placeholder
            0x00, 0x00, 0x00, 0x00
        ])

        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')

        tot = TDTParser.parse(section_data)

        assert tot.table_id == 0x73
        assert len(tot.descriptors) == 2

    def test_parse_insufficient_data(self):
        """Test that insufficient data raises ValueError"""
        section_data = bytes([0x70, 0x00])
        with pytest.raises(ValueError):
            TDTParser.parse(section_data)

    def test_parse_invalid_table_id(self):
        """Test that invalid table_id raises ValueError"""
        section_data = bytes([
            0x00,                    # invalid table_id
            0b10110000, 0x05,
            0x58, 0x00,
            0x12, 0x00, 0x00
        ])
        with pytest.raises(ValueError):
            TDTParser.parse(section_data)

    def test_parse_tot_crc_failure(self):
        """Test that CRC failure raises ValueError"""
        section_data = bytes([
            0x73,                    # table_id (TOT)
            0b10110000, 0x10,        # syntax_indicator=1, length=16
            0x58, 0x00,              # MJD
            0x15, 0x00, 0x00,        # 15:00:00
            0b11110000, 0x05,        # descriptors_length=5
            0x58, 0x03,              # descriptor_tag=0x58, length=3
            0x43, 0x48, 0x4E,        # "CHN"
            0xFF, 0xFF, 0xFF, 0xFF   # wrong CRC
        ])

        with pytest.raises(ValueError):
            TDTParser.parse(section_data)
