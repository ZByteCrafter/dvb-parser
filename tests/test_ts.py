import pytest
from dvb_parser.ts.parser import TSPacketParser
from dvb_parser.ts.models import AdaptationFieldControl, ScramblingControl


class TestTSPacketParser:
    def test_parse_valid_ts_packet(self):
        header = bytes([
            0x47,
            0b00000001, 0x00,
            0b00010000
        ])
        payload = bytes([0x00] * 184)
        ts_data = header + payload

        packet = TSPacketParser.parse(ts_data)

        assert packet.pid == 0x100
        assert packet.cc == 0
        assert packet.afc == AdaptationFieldControl.PAYLOAD_ONLY
        assert packet.scrambling == ScramblingControl.NOT_SCRAMBLED
        assert len(packet.payload) == 184
        assert packet.fec is None

    def test_parse_204_byte_packet(self):
        header = bytes([
            0x47,
            0b00000001, 0x00,
            0b00010000
        ])
        payload = bytes([0x00] * 184)
        fec = bytes([0x00] * 16)
        ts_data = header + payload + fec

        packet = TSPacketParser.parse(ts_data, packet_size=204)

        assert packet.pid == 0x100
        assert len(packet.payload) == 184
        assert packet.fec is not None
        assert len(packet.fec) == 16

    def test_parse_invalid_sync(self):
        header = bytes([
            0x00,
            0b00000001, 0x00,
            0b00010000
        ])
        payload = bytes([0x00] * 184)
        ts_data = header + payload

        with pytest.raises(ValueError, match="同步字错误"):
            TSPacketParser.parse(ts_data)

    def test_detect_packet_size(self):
        header = bytes([
            0x47,
            0b00000001, 0x00,
            0b00010000
        ])
        payload = bytes([0x00] * 184)
        ts_data = header + payload + header + payload

        detected_size = TSPacketParser.detect_packet_size(ts_data)
        assert detected_size == 188

    def test_parse_multiple_packets(self):
        header = bytes([
            0x47,
            0b00000001, 0x00,
            0b00010000
        ])
        payload = bytes([0x00] * 184)
        ts_data = header + payload + header + payload

        packets = TSPacketParser.parse_all(ts_data)

        assert len(packets) == 2
        assert packets[0].pid == 0x100
        assert packets[1].pid == 0x100
