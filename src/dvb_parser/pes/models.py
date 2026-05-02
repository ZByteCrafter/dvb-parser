"""
PES data models
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PESHeader:
    """PES 包头"""
    stream_id: int
    pes_length: int
    pts: Optional[int] = None  # 33-bit PTS
    dts: Optional[int] = None  # 33-bit DTS
    escr: Optional[int] = None
    es_rate: Optional[int] = None


@dataclass
class ESFrameHeader:
    """ES 帧头基类"""
    frame_type: str  # "video" or "audio"
    codec: str  # "h264", "h265", "aac", "mp3", "ac3", "eac3"


@dataclass
class H264NALUHeader(ESFrameHeader):
    """H.264 NALU 头"""
    nal_unit_type: int
    nal_ref_idc: int
    forbidden_zero_bit: int


@dataclass
class H265NALUHeader(ESFrameHeader):
    """H.265 NALU 头"""
    nal_unit_type: int
    nuh_layer_id: int
    nuh_temporal_id_plus1: int


@dataclass
class AACADTSHeader(ESFrameHeader):
    """AAC ADTS 头"""
    profile: int
    sampling_frequency: int
    channel_configuration: int
    frame_length: int


@dataclass
class MP3FrameHeader(ESFrameHeader):
    """MP3 帧头"""
    version: int
    layer: int
    bitrate: int
    sampling_rate: int
    channel_mode: int


@dataclass
class AC3SyncHeader(ESFrameHeader):
    """AC3 同步头"""
    sample_rate: int
    bitstream_mode: int
    audio_coding_mode: int
    frame_size: int


@dataclass
class PESPacket:
    """PES 包"""
    header: PESHeader
    payload: bytes
    es_frame_header: Optional[ESFrameHeader] = None