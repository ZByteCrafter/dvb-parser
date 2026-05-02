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

        # Pad TS payload
        ts_payload = pat_data + bytes([0xFF] * (184 - len(pat_data)))
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

        pat = PATParser.parse(ts_packets[0].payload)
        assert 1 in pat.programs
        assert pat.programs[1] == 0x100
