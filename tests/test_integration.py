import pytest
from dvb_parser.bbframe.parser import BBFrameParser
from dvb_parser.ts.parser import TSPacketParser
from dvb_parser.psi.pat import PATParser


class TestIntegration:
    def test_bbframe_to_ts_to_pat(self):
        """测试从 BBFrame 到 PAT 的完整解析链"""
        # BBFrame header
        bb_header = bytes([
            0b00000000, 0b00000000,  # MATYPE (TS mode)
            0x00, 0xBC,              # UPL (188 bytes)
            0x06, 0x18,              # DFL (1560 bits = 195 bytes)
            0x00,                    # SYNC
            0x00, 0x00,              # SYNCD
            0x00                     # CRC-8 placeholder
        ])

        from dvb_parser.utils.crc import crc8
        crc_value = crc8(bb_header[:9])
        bb_header = bb_header[:9] + bytes([crc_value])

        # TS packet with PAT
        ts_header = bytes([
            0x47,                    # Sync byte
            0b00000000, 0x00,        # PID=0x0000 (PAT)
            0b00010000               # AFC=01, CC=0
        ])

        # PAT payload
        pat_data = bytes([
            0x00,                    # table_id
            0b10110000, 0x0D,        # syntax_indicator=1, length=13
            0x00, 0x01,              # transport_stream_id
            0b11000001,              # version=1, current_next=1
            0x00,                    # section_number
            0x00,                    # last_section_number
            0x00, 0x01,              # program_number=1
            0b11100001, 0x00,        # PID=0x100
        ])

        from dvb_parser.utils.crc import crc32
        crc_value = crc32(pat_data)
        pat_data = pat_data + crc_value.to_bytes(4, 'big')

        # TS payload: pointer_field (0x00) + PAT data + padding
        ts_payload = bytes([0x00]) + pat_data + bytes([0xFF] * (183 - len(pat_data)))
        ts_packet = ts_header + ts_payload

        # Repeat TS packet to fill BBFrame data field
        ts_data = ts_packet * (195 // 188 + 1)
        ts_data = ts_data[:195]  # Trim to exact size

        # Complete BBFrame
        bbframe_data = bb_header + ts_data

        # Parse
        bbframe = BBFrameParser.parse(bbframe_data)
        assert bbframe.header.is_ts_mode

        ts_packets = TSPacketParser.parse_all(bbframe.data_field)
        assert len(ts_packets) > 0
        assert ts_packets[0].pid == 0x0000

        pat = PATParser.parse(ts_packets[0].payload, offset=1)
        assert 1 in pat.programs
        assert pat.programs[1] == 0x100


from dvb_parser.si.sdt import SDTParser
from dvb_parser.si.nit import NITParser
from dvb_parser.pes.parser import PESParser


class TestIntegrationP1:
    def test_sdt_service_descriptor(self):
        """测试 SDT 服务描述符解析"""
        # 构造 SDT 数据
        # SDT section layout:
        #   bytes 0-2:   table_id + syntax_indicator + section_length
        #   bytes 3-4:   transport_stream_id
        #   byte 5:      version_number + current_next_indicator
        #   bytes 6-7:   section_number + last_section_number
        #   bytes 8-9:   original_network_id
        #   byte 10:     reserved_future_use
        #   bytes 11+:   service loop
        #   last 4 bytes: CRC-32
        sdt_data = bytes([
            0x42,                    # table_id
            0b10110000, 0x1A,        # syntax=1, section_length=26
            0x00, 0x01,              # transport_stream_id=1
            0b11000001,              # version=1, current_next=1
            0x00, 0x00,              # section_number=0, last_section_number=0
            0x00, 0x01,              # original_network_id=1
            0x00,                    # reserved_future_use
            # Service entry (starts at byte 11)
            0x00, 0x01,              # service_id=1 (matches PMT program_number)
            0b11111100,              # reserved + EIT flags
            0x80, 0x09,              # running_status=4, free_ca=0, desc_length=9
            # Service descriptor (9 bytes total)
            0x48, 0x07,              # tag=0x48, length=7
            0x01,                    # service_type=1
            0x02, 0x54, 0x56,        # provider_name_length=2, "TV"
            0x02, 0x48, 0x44,        # service_name_length=2, "HD"
            # CRC-32 placeholder
            0x00, 0x00, 0x00, 0x00
        ])

        from dvb_parser.utils.crc import crc32
        crc_value = crc32(sdt_data[:-4])
        sdt_data = sdt_data[:-4] + crc_value.to_bytes(4, 'big')

        sdt = SDTParser.parse(sdt_data)

        # 验证 SDT.service_id 对应 PMT.program_number
        assert sdt.services[0].service_id == 1
        assert sdt.services[0].service_name == "HD"
        assert sdt.services[0].provider_name == "TV"
        assert sdt.services[0].service_type == 1

    def test_nit_with_bbframe(self):
        """测试 NIT 获取传输参数"""
        # 构造 NIT 数据
        # NIT section layout:
        #   bytes 0-2:   table_id + syntax_indicator + section_length
        #   bytes 3-4:   network_id
        #   byte 5:      version_number + current_next_indicator
        #   bytes 6-7:   section_number + last_section_number
        #   bytes 8-9:   network_descriptors_length
        #   bytes 10-14: network descriptors (network_name "Sat")
        #   bytes 15-16: transport_stream_loop_length
        #   bytes 17+:   transport stream entries
        #   last 4 bytes: CRC-32
        nit_data = bytes([
            0x40,                    # table_id
            0b10110000, 0x25,        # syntax=1, section_length=37
            0x00, 0x01,              # network_id=1
            0b11000001,              # version=1, current_next=1
            0x00, 0x00,              # section_number=0, last_section_number=0
            # Network descriptors
            0b11110000, 0x05,        # desc_length=5
            0x40, 0x03,              # network_name_descriptor, length=3
            0x53, 0x61, 0x74,        # "Sat"
            # Transport stream loop
            0b11110000, 0x13,        # ts_loop_length=19
            0x00, 0x01, 0x00, 0x01,  # ts_id=1, original_network_id=1
            0b11110000, 0x0D,        # ts_desc_length=13
            # Satellite delivery system descriptor
            0x43, 0x0B,              # tag=0x43, length=11
            0x01, 0x18, 0x05, 0x68,  # frequency (BCD 1180568 * 10kHz)
            0x00, 0x00,              # orbital position
            0b11000000,              # polarization=3 (circular)
            0b00000010,              # modulation=2 (8PSK)
            0x02, 0x50, 0x00,        # symbol_rate (BCD 25000 * 10sym/s)
            # CRC-32 placeholder
            0x00, 0x00, 0x00, 0x00
        ])

        from dvb_parser.utils.crc import crc32
        crc_value = crc32(nit_data[:-4])
        nit_data = nit_data[:-4] + crc_value.to_bytes(4, 'big')

        nit = NITParser.parse(nit_data)

        # 验证从 NIT 获取的频率、调制方式可用于 BBFrame 解析
        assert nit.network_name == "Sat"
        assert nit.transport_streams[0].frequency == 11805680000  # Hz
        assert nit.transport_streams[0].symbol_rate == 25000000  # sym/s


from dvb_parser.gse.parser import GSEParser
from dvb_parser.mpe.parser import MPEParser
from dvb_parser.ule.parser import ULEParser
from dvb_parser.nip.parser import NIPParser
from dvb_parser.si.eit import EITParser
from dvb_parser.si.tdt import TDTParser


class TestIntegrationP2:
    def test_gse_with_bbframe(self):
        """测试 GSE 与 BBFrame 关联"""
        # 构造 GSE 数据
        # Start=1, End=1, Label Type=0, Protocol Type=0x0800 (IPv4)
        # Total Length=22 (header 6 + payload 16)
        gse_data = bytes([
            0b11000000, 0x00, 0x08, 0x00, 0x00, 0x16,
            0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
            0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
            0x00, 0x00, 0x00, 0x00  # CRC-32 placeholder
        ])

        from dvb_parser.utils.crc import crc32
        crc_value = crc32(gse_data[:-4])
        gse_data = gse_data[:-4] + crc_value.to_bytes(4, 'big')

        gse = GSEParser.parse(gse_data)

        assert gse.is_ipv4 == True
        assert gse.is_complete == True

    def test_eit_with_sdt(self):
        """测试 EIT 与 SDT 关联（事件对应节目）"""
        # 构造 EIT 数据
        eit_data = bytes([
            0x4E, 0b10110000, 0x19,  # section_length=25
            0x00, 0x01,  # service_id=1
            0b11000001,  # version=1
            0x00, 0x01, 0x00, 0x01,  # ts_id, original_network_id
            0x00, 0x00,  # section numbers
            0x00, 0x01,  # event_id
            0x58, 0x00,  # MJD
            0x12, 0x00, 0x00,  # 12:00:00
            0x01, 0x30, 0x00,  # 1h30m
            0x00, 0x00,  # running_status=0, free_ca=0, desc_length=0
            0x00, 0x00, 0x00, 0x00  # CRC-32
        ])

        from dvb_parser.utils.crc import crc32
        crc_value = crc32(eit_data[:-4])
        eit_data = eit_data[:-4] + crc_value.to_bytes(4, 'big')

        eit = EITParser.parse(eit_data)

        assert eit.service_id == 1  # 对应 SDT.service_id
        assert len(eit.events) == 1


from dvb_parser.parser import DVBParser


class TestDVBParserIntegration:
    def test_full_bbframe_to_si(self):
        """测试完整的 BBFrame → TS → SI 解析链"""
        from dvb_parser.bbframe.parser import BBFrameParser
        from dvb_parser.utils.crc import crc8, crc32

        # 构造包含 PAT 的 BBFrame
        bb_header = bytes([
            0b00000000, 0b00000000,  # MATYPE (TS mode)
            0x00, 0xBC,              # UPL (188 bytes)
            0x06, 0x18,              # DFL (1560 bits = 195 bytes)
            0x00,                    # SYNC
            0x00, 0x00,              # SYNCD
            0x00                     # CRC-8 placeholder
        ])
        crc_value = crc8(bb_header[:9])
        bb_header = bb_header[:9] + bytes([crc_value])

        # TS packet with PAT
        ts_header = bytes([0x47, 0b00000000, 0x00, 0b00010000])

        # PAT payload
        pat_data = bytes([
            0x00,                    # table_id
            0b10110000, 0x0D,        # syntax_indicator=1, length=13
            0x00, 0x01,              # transport_stream_id
            0b11000001,              # version=1, current_next=1
            0x00,                    # section_number
            0x00,                    # last_section_number
            0x00, 0x01,              # program_number=1
            0b11100001, 0x00,        # PID=0x100
        ])
        crc_value = crc32(pat_data)
        pat_data = pat_data + crc_value.to_bytes(4, 'big')

        # TS payload: pointer_field (0x00) + PAT data + padding
        ts_payload = bytes([0x00]) + pat_data + bytes([0xFF] * (183 - len(pat_data)))
        ts_packet = ts_header + ts_payload

        # Fill BBFrame data field
        ts_data = ts_packet * (195 // 188 + 1)
        ts_data = ts_data[:195]

        bbframe_data = bb_header + ts_data

        # 使用 DVBParser 自动解析
        parser = DVBParser()
        result = parser.parse(bbframe_data)

        assert result.format == "bbframe"
        assert len(result.bbframes) == 1
        assert len(result.ts_packets) > 0
        assert result.pat is not None
        assert 1 in result.pat.programs
        assert result.pat.programs[1] == 0x100

    def test_ts_with_pat(self):
        """测试 TS 格式自动解析 PAT"""
        from dvb_parser.utils.crc import crc32

        # 构造包含 PAT 的 TS 数据
        ts_header = bytes([0x47, 0b00000000, 0x00, 0b00010000])

        pat_data = bytes([
            0x00,                    # table_id
            0b10110000, 0x0D,        # syntax_indicator=1, length=13
            0x00, 0x01,              # transport_stream_id
            0b11000001,              # version=1, current_next=1
            0x00,                    # section_number
            0x00,                    # last_section_number
            0x00, 0x01,              # program_number=1
            0b11100001, 0x00,        # PID=0x100
        ])
        crc_value = crc32(pat_data)
        pat_data = pat_data + crc_value.to_bytes(4, 'big')

        ts_payload = bytes([0x00]) + pat_data + bytes([0xFF] * (183 - len(pat_data)))
        ts_data = ts_header + ts_payload

        # 使用 DVBParser 自动解析
        parser = DVBParser()
        result = parser.parse(ts_data)

        assert result.format == "ts"
        assert len(result.ts_packets) == 1
        assert result.pat is not None
        assert 1 in result.pat.programs
