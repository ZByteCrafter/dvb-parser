import pytest
from dvb_parser.pes.parser import PESParser
from dvb_parser.pes.models import (
    H264NALUHeader, H265NALUHeader,
    AACADTSHeader, MP3FrameHeader, AC3SyncHeader
)

class TestPESParser:
    def test_parse_valid_pes(self):
        """测试解析有效的 PES"""
        # 构造 PES 包
        pes_data = bytes([
            0x00, 0x00, 0x01,        # start_code
            0xE0,                    # stream_id (video stream 0)
            0x00, 0x10,              # pes_length=16
            # Optional header
            0b10000000,              # flags: PTS present
            0x05,                    # optional_fields_length=5
            # PTS (33-bit)
            0b00110001,              # PTS[32:30] + marker
            0x00, 0x01,              # PTS[29:15] + marker
            0x00, 0x01,              # PTS[14:0] + marker
            # Payload
            0x00, 0x00, 0x00, 0x01,  # H.264 NALU start code
            0x65,                    # NALU type=5 (IDR)
            0x00, 0x00, 0x00, 0x00   # padding
        ])

        pes = PESParser.parse(pes_data, stream_type=0x1B)

        assert pes.header.stream_id == 0xE0
        assert pes.header.pes_length == 16
        assert pes.header.pts is not None
        assert pes.es_frame_header is not None
        assert pes.es_frame_header.codec == "h264"

    def test_parse_h264_nalu_header(self):
        """测试解析 H.264 NALU 头"""
        payload = bytes([
            0x00, 0x00, 0x00, 0x01,  # start code
            0x65,                    # NALU: forbidden=0, ref_idc=3, type=5 (IDR)
            0x00, 0x00
        ])

        header = PESParser._parse_h264_h265_header(payload, 0x1B)

        assert header is not None
        assert header.codec == "h264"
        assert header.nal_unit_type == 5
        assert header.nal_ref_idc == 3
        assert header.forbidden_zero_bit == 0

    def test_parse_aac_adts_header(self):
        """测试解析 AAC ADTS 头"""
        payload = bytes([
            0xFF, 0xF1,              # sync word (0xFFF) + ID=0, layer=0
            0x50,                    # profile=2 (AAC-LC), sampling_freq_idx=4 (44100Hz)
            0x80,                    # channel_config=2 (stereo), frame_length[12:11]=00
            0x38,                    # frame_length[10:3] = 0x38
            0x00,                    # frame_length[2:0]=000
            0x00, 0x00
        ])

        header = PESParser._parse_aac_header(payload)

        assert header is not None
        assert header.codec == "aac"
        assert header.profile == 2  # AAC-LC
        assert header.sampling_frequency == 44100
        assert header.channel_configuration == 2
        assert header.frame_length == 448

    def test_parse_mp3_header(self):
        """测试解析 MP3 帧头"""
        payload = bytes([
            0xFF, 0xFB,              # sync word + version=11 (MPEG-1), layer=01 (Layer 3)
            0x90,                    # bitrate_idx=9 (128kbps), sampling_idx=0 (44100Hz)
            0xC0,                    # channel_mode=11 (stereo)
            0x00, 0x00
        ])

        header = PESParser._parse_mp3_header(payload)

        assert header is not None
        assert header.codec == "mp3"
        assert header.version == 3  # MPEG-1
        assert header.layer == 1  # Layer 3
        assert header.bitrate == 128000
        assert header.sampling_rate == 44100
        assert header.channel_mode == 3  # stereo

    def test_parse_ac3_header(self):
        """测试解析 AC3 同步头"""
        payload = bytes([
            0x0B, 0x77,              # sync word
            0x00, 0x00,              # CRC
            0x42,                    # sample_rate_idx=1 (44100Hz), bitstream_mode=0, acmod=2 (stereo)
            0x04,                    # frame_size_code=4
            0x00, 0x00
        ])

        header = PESParser._parse_ac3_header(payload, 0x81)

        assert header is not None
        assert header.codec == "ac3"
        assert header.sample_rate == 44100
        assert header.audio_coding_mode == 2
