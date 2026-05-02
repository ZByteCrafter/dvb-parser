import pytest
from dvb_parser.nip.parser import NIPParser
from dvb_parser.nip.models import NIPDataUnit, NIPStreaming


class TestNIPParser:
    def test_parse_data_piping(self):
        """测试解析数据管道"""
        data = bytes([0x01, 0x02, 0x03, 0x04])

        nip = NIPParser.parse_piping(data)

        assert nip.method == "piping"
        assert nip.payload == data

    def test_parse_data_piping_with_offset(self):
        """测试解析数据管道（带偏移）"""
        data = bytes([0xFF, 0x01, 0x02, 0x03, 0x04])

        nip = NIPParser.parse_piping(data, offset=1)

        assert nip.method == "piping"
        assert nip.payload == bytes([0x01, 0x02, 0x03, 0x04])

    def test_parse_data_streaming(self):
        """测试解析数据流"""
        streaming_data = bytes([
            0x01,                    # synchronous=1
            0x00, 0x01,              # data_identifier
            0x02, 0x03, 0x04         # payload
        ])

        nip = NIPParser.parse_streaming(streaming_data)

        assert nip.synchronous == True
        assert nip.data_identifier == 1
        assert len(nip.payload) == 3

    def test_parse_data_streaming_not_synchronous(self):
        """测试解析异步数据流"""
        streaming_data = bytes([
            0x00,                    # synchronous=0
            0x00, 0x02,              # data_identifier
            0x05, 0x06               # payload
        ])

        nip = NIPParser.parse_streaming(streaming_data)

        assert nip.synchronous == False
        assert nip.data_identifier == 2
        assert nip.payload == bytes([0x05, 0x06])

    def test_parse_data_streaming_insufficient_data(self):
        """测试数据流解析 - 数据不足"""
        data = bytes([0x01, 0x00])  # 只有2字节，不足5字节

        with pytest.raises(ValueError, match="数据不足"):
            NIPParser.parse_streaming(data)

    def test_parse_carousel(self):
        """测试解析数据循环"""
        carousel_data = bytes([
            0x00, 0x00, 0x00, 0x01,  # download_id=1
            0x00, 0x02,              # block_size=2
            0xAA, 0xBB,              # block 1
            0xCC, 0xDD               # block 2
        ])

        nip = NIPParser.parse_carousel(carousel_data)

        assert nip.download_id == 1
        assert nip.block_size == 2
        assert len(nip.blocks) == 2
        assert nip.blocks[0] == bytes([0xAA, 0xBB])
        assert nip.blocks[1] == bytes([0xCC, 0xDD])

    def test_parse_carousel_insufficient_data(self):
        """测试数据循环解析 - 数据不足"""
        data = bytes([0x00, 0x01])  # 只有2字节，不足8字节

        with pytest.raises(ValueError, match="数据不足"):
            NIPParser.parse_carousel(data)
