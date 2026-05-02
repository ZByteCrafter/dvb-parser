import pytest
from dvb_parser.psi.pat import PATParser
from dvb_parser.psi.pmt import PMTParser


class TestPATParser:
    def test_parse_valid_pat(self):
        """测试解析有效的 PAT"""
        # 构造 PAT section
        # table_id=0x00, section_syntax_indicator=1, section_length=17
        # transport_stream_id=0x0001, version_number=1, current_next_indicator=1
        # section_number=0, last_section_number=0
        # program_number=1, PID=0x100
        # CRC-32 placeholder
        section_data = bytes([
            0x00,                    # table_id
            0b10000000, 0x0D,        # syntax_indicator=1, length=13
            0x00, 0x01,              # transport_stream_id
            0b11000011,              # version=1, current_next=1
            0x00,                    # section_number
            0x00,                    # last_section_number
            0x00, 0x01,              # program_number=1
            0b11100001, 0x00,        # PID=0x100
            0x00, 0x00, 0x00, 0x00   # CRC-32 placeholder
        ])

        # Calculate correct CRC-32
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')

        pat = PATParser.parse(section_data)

        assert pat.table_id == 0x00
        assert pat.version_number == 1
        assert pat.current_next_indicator is True
        assert 1 in pat.programs
        assert pat.programs[1] == 0x100

    def test_parse_pat_with_multiple_programs(self):
        """测试解析包含多个节目的 PAT"""
        section_data = bytes([
            0x00,                    # table_id
            0b10010000, 0x11,        # syntax_indicator=1, length=17
            0x00, 0x02,              # transport_stream_id
            0b11000101,              # version=2, current_next=1
            0x00,                    # section_number
            0x00,                    # last_section_number
            0x00, 0x01,              # program_number=1
            0b11100001, 0x00,        # PID=0x100
            0x00, 0x02,              # program_number=2
            0b11100010, 0x00,        # PID=0x200
            0x00, 0x00, 0x00, 0x00   # CRC-32 placeholder
        ])

        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')

        pat = PATParser.parse(section_data)

        assert pat.version_number == 2
        assert len(pat.entries) == 2
        assert pat.programs[1] == 0x100
        assert pat.programs[2] == 0x200

    def test_parse_pat_invalid_table_id(self):
        """测试无效 table_id"""
        section_data = bytes([
            0x01,                    # table_id (invalid)
            0b10000000, 0x09,        # syntax_indicator=1, length=9
            0x00, 0x01,              # transport_stream_id
            0b11000001,              # version=1, current_next=1
            0x00,                    # section_number
            0x00,                    # last_section_number
            0x00, 0x00, 0x00, 0x00   # CRC-32 placeholder
        ])

        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')

        with pytest.raises(ValueError, match="不是 PAT 表"):
            PATParser.parse(section_data)

    def test_parse_pat_crc_error(self):
        """测试 CRC-32 校验失败"""
        section_data = bytes([
            0x00,                    # table_id
            0b10000000, 0x0D,        # syntax_indicator=1, length=13
            0x00, 0x01,              # transport_stream_id
            0b11000001,              # version=1, current_next=1
            0x00,                    # section_number
            0x00,                    # last_section_number
            0x00, 0x01,              # program_number=1
            0b11100001, 0x00,        # PID=0x100
            0xFF, 0xFF, 0xFF, 0xFF   # Wrong CRC
        ])

        with pytest.raises(ValueError, match="CRC-32 校验失败"):
            PATParser.parse(section_data)

    def test_parse_pat_insufficient_data(self):
        """测试数据不足"""
        with pytest.raises(ValueError, match="数据不足"):
            PATParser.parse(bytes([0x00, 0x00]))

    def test_parse_pat_with_offset(self):
        """测试带偏移量的解析"""
        # Add padding at the beginning
        padding = bytes([0xFF, 0xFF, 0xFF])
        section_data = bytes([
            0x00,                    # table_id
            0b10000000, 0x0D,        # syntax_indicator=1, length=13
            0x00, 0x01,              # transport_stream_id
            0b11000001,              # version=1, current_next=1
            0x00,                    # section_number
            0x00,                    # last_section_number
            0x00, 0x01,              # program_number=1
            0b11100001, 0x00,        # PID=0x100
            0x00, 0x00, 0x00, 0x00   # CRC-32 placeholder
        ])

        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')

        full_data = padding + section_data
        pat = PATParser.parse(full_data, offset=3)

        assert pat.table_id == 0x00
        assert pat.programs[1] == 0x100

    def test_parse_pat_network_pid(self):
        """测试解析网络 PID (program_number=0)"""
        section_data = bytes([
            0x00,                    # table_id
            0b10000000, 0x0D,        # syntax_indicator=1, length=13
            0x00, 0x01,              # transport_stream_id
            0b11000001,              # version=1, current_next=1
            0x00,                    # section_number
            0x00,                    # last_section_number
            0x00, 0x00,              # program_number=0 (network)
            0b00010000, 0x00,        # PID=0x1000
            0x00, 0x00, 0x00, 0x00   # CRC-32 placeholder
        ])

        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')

        pat = PATParser.parse(section_data)

        assert 0 in pat.programs
        assert pat.programs[0] == 0x1000


class TestPMTParser:
    def test_parse_valid_pmt(self):
        """测试解析有效的 PMT"""
        # 构造 PMT section
        # table_id=0x02, section_syntax_indicator=1, section_length=22
        # program_number=1, version_number=1, current_next_indicator=1
        # section_number=0, last_section_number=0
        # PCR_PID=0x100, program_info_length=0
        # stream_type=0x1B (H.264), PID=0x101
        # CRC-32 placeholder
        section_data = bytes([
            0x02,                    # table_id
            0b10110000, 0x16,        # syntax_indicator=1, length=22
            0x00, 0x01,              # program_number=1
            0b11000001,              # version=1, current_next=1
            0x00,                    # section_number
            0x00,                    # last_section_number
            0b11100001, 0x00,        # PCR_PID=0x100
            0b11110000, 0x00,        # program_info_length=0
            0x1B,                    # stream_type=H.264
            0b11100001, 0x01,        # PID=0x101
            0b11110000, 0x00,        # ES_info_length=0
            0x00, 0x00, 0x00, 0x00   # CRC-32 placeholder
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')
        
        pmt = PMTParser.parse(section_data)
        
        assert pmt.table_id == 0x02
        assert pmt.program_number == 1
        assert pmt.pcr_pid == 0x100
        assert len(pmt.streams) == 1
        assert pmt.streams[0].stream_type == 0x1B
        assert pmt.streams[0].pid == 0x101
