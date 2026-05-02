"""
PES (Packetized Elementary Stream) parser
"""

import struct
from typing import Optional

from dvb_parser.pes.models import (
    PESPacket, PESHeader, ESFrameHeader,
    H264NALUHeader, H265NALUHeader,
    AACADTSHeader, MP3FrameHeader, AC3SyncHeader
)


class PESParser:
    """PES 解析器"""
    
    @staticmethod
    def parse(data: bytes, offset: int = 0, stream_type: int = 0) -> PESPacket:
        """
        解析 PES 包
        
        Args:
            data: 原始数据
            offset: 起始偏移
            stream_type: 流类型（用于 ES 帧头解析）
        
        Returns:
            PESPacket 对象
        
        Raises:
            ValueError: 数据无效
        """
        if len(data) - offset < 6:
            raise ValueError("数据不足")
        
        # 验证起始码
        start_code = (data[offset] << 16) | (data[offset + 1] << 8) | data[offset + 2]
        if start_code != 0x000001:
            raise ValueError("无效的 PES 起始码")
        
        # 解析 stream_id
        stream_id = data[offset + 3]
        
        # 解析 PES length
        pes_length = struct.unpack('>H', data[offset + 4:offset + 6])[0]
        
        # 解析可选头部
        pts = None
        dts = None
        escr = None
        es_rate = None
        
        current_offset = offset + 6
        
        # 检查是否有可选头部
        if stream_id not in (0xBC, 0xBE, 0xBF, 0xF0, 0xF1, 0xFF, 0xF2, 0xF8):
            if current_offset + 3 > len(data):
                raise ValueError("数据不足")
            
            # 解析标志位
            flags = data[current_offset]
            pts_dts_flags = (flags >> 6) & 0x03
            
            # 解析 PTS
            if pts_dts_flags & 0x02:  # PTS present
                pts = PESParser._parse_pts(data, current_offset)
                current_offset += 5
            
            # 解析 DTS
            if pts_dts_flags & 0x01:  # DTS present
                dts = PESParser._parse_pts(data, current_offset)
                current_offset += 5
            
            # 跳过其他可选字段
            optional_fields_length = data[current_offset]
            current_offset += 1 + optional_fields_length
        
        # 提取 payload
        payload = data[current_offset:offset + 6 + pes_length if pes_length > 0 else len(data)]
        
        # 解析 ES 帧头
        es_frame_header = None
        if stream_type in (0x1B, 0x24):  # H.264 or H.265
            es_frame_header = PESParser._parse_h264_h265_header(payload, stream_type)
        elif stream_type == 0x0F:  # AAC
            es_frame_header = PESParser._parse_aac_header(payload)
        elif stream_type in (0x03, 0x04):  # MP3
            es_frame_header = PESParser._parse_mp3_header(payload)
        elif stream_type in (0x81, 0x87):  # AC3/E-AC3
            es_frame_header = PESParser._parse_ac3_header(payload, stream_type)
        
        header = PESHeader(
            stream_id=stream_id,
            pes_length=pes_length,
            pts=pts,
            dts=dts,
            escr=escr,
            es_rate=es_rate
        )
        
        return PESPacket(
            header=header,
            payload=payload,
            es_frame_header=es_frame_header
        )
    
    @staticmethod
    def _parse_pts(data: bytes, offset: int) -> int:
        """解析 33-bit PTS"""
        pts = 0
        pts |= ((data[offset] >> 1) & 0x07) << 30
        pts |= struct.unpack('>H', data[offset + 1:offset + 3])[0] >> 1 << 15
        pts |= struct.unpack('>H', data[offset + 3:offset + 5])[0] >> 1
        return pts
    
    @staticmethod
    def _parse_h264_h265_header(payload: bytes, stream_type: int) -> Optional[ESFrameHeader]:
        """解析 H.264/H.265 NALU 头"""
        if len(payload) < 4:
            return None
        
        # 搜索 NALU 起始码 (0x00000001 or 0x000001)
        for i in range(len(payload) - 3):
            if payload[i:i + 3] == b'\x00\x00\x01' or (i + 4 <= len(payload) and payload[i:i + 4] == b'\x00\x00\x00\x01'):
                nalu_offset = i + 3 if payload[i:i + 3] == b'\x00\x00\x01' else i + 4
                if nalu_offset >= len(payload):
                    break
                
                nalu_byte = payload[nalu_offset]
                
                if stream_type == 0x1B:  # H.264
                    return H264NALUHeader(
                        frame_type="video",
                        codec="h264",
                        forbidden_zero_bit=(nalu_byte >> 7) & 0x01,
                        nal_ref_idc=(nalu_byte >> 5) & 0x03,
                        nal_unit_type=nalu_byte & 0x1F
                    )
                else:  # H.265
                    if nalu_offset + 1 >= len(payload):
                        break
                    nalu_byte2 = payload[nalu_offset + 1]
                    return H265NALUHeader(
                        frame_type="video",
                        codec="h265",
                        nal_unit_type=(nalu_byte >> 1) & 0x3F,
                        nuh_layer_id=((nalu_byte & 0x01) << 5) | ((nalu_byte2 >> 3) & 0x1F),
                        nuh_temporal_id_plus1=nalu_byte2 & 0x07
                    )
        
        return None
    
    @staticmethod
    def _parse_aac_header(payload: bytes) -> Optional[AACADTSHeader]:
        """解析 AAC ADTS 头"""
        if len(payload) < 7:
            return None
        
        # 搜索 ADTS 同步字 (0xFFF)
        for i in range(len(payload) - 7):
            if payload[i] == 0xFF and (payload[i + 1] & 0xF0) == 0xF0:
                # 解析 ADTS 头
                profile = ((payload[i + 2] >> 6) & 0x03) + 1
                sampling_freq_idx = (payload[i + 2] >> 2) & 0x0F
                channel_config = ((payload[i + 2] & 0x01) << 2) | ((payload[i + 3] >> 6) & 0x03)
                frame_length = ((payload[i + 3] & 0x03) << 11) | (payload[i + 4] << 3) | ((payload[i + 5] >> 5) & 0x07)
                
                # 采样率映射
                sampling_rates = [96000, 88200, 64000, 48000, 44100, 32000, 24000, 22050, 16000, 12000, 11025, 8000, 7350]
                sampling_freq = sampling_rates[sampling_freq_idx] if sampling_freq_idx < len(sampling_rates) else 0
                
                return AACADTSHeader(
                    frame_type="audio",
                    codec="aac",
                    profile=profile,
                    sampling_frequency=sampling_freq,
                    channel_configuration=channel_config,
                    frame_length=frame_length
                )
        
        return None
    
    @staticmethod
    def _parse_mp3_header(payload: bytes) -> Optional[MP3FrameHeader]:
        """解析 MP3 帧头"""
        if len(payload) < 4:
            return None
        
        # 搜索 MP3 同步字 (0xFFE0)
        for i in range(len(payload) - 4):
            if payload[i] == 0xFF and (payload[i + 1] & 0xE0) == 0xE0:
                # 解析 MP3 帧头
                version = (payload[i + 1] >> 3) & 0x03
                layer = (payload[i + 1] >> 1) & 0x03
                bitrate_idx = (payload[i + 2] >> 4) & 0x0F
                sampling_idx = (payload[i + 2] >> 2) & 0x03
                channel_mode = (payload[i + 3] >> 6) & 0x03
                
                # 比特率映射 (MPEG-1 Layer 3)
                bitrates = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
                bitrate = bitrates[bitrate_idx] * 1000 if bitrate_idx < len(bitrates) else 0
                
                # 采样率映射
                sampling_rates = [44100, 48000, 32000]
                sampling_rate = sampling_rates[sampling_idx] if sampling_idx < len(sampling_rates) else 0
                
                return MP3FrameHeader(
                    frame_type="audio",
                    codec="mp3",
                    version=version,
                    layer=layer,
                    bitrate=bitrate,
                    sampling_rate=sampling_rate,
                    channel_mode=channel_mode
                )
        
        return None
    
    @staticmethod
    def _parse_ac3_header(payload: bytes, stream_type: int) -> Optional[AC3SyncHeader]:
        """解析 AC3/E-AC3 同步头"""
        if len(payload) < 5:
            return None
        
        # 搜索 AC3 同步字 (0x0B77)
        for i in range(len(payload) - 5):
            if payload[i] == 0x0B and payload[i + 1] == 0x77:
                # 解析 AC3 头
                sample_rate_idx = (payload[i + 4] >> 6) & 0x03
                bitstream_mode = (payload[i + 4] >> 3) & 0x07
                audio_coding_mode = payload[i + 4] & 0x07
                
                # 采样率映射
                sample_rates = [48000, 44100, 32000]
                sample_rate = sample_rates[sample_rate_idx] if sample_rate_idx < len(sample_rates) else 0
                
                # 帧大小计算
                frame_size_code = payload[i + 5] & 0x3F
                frame_sizes = [64, 64, 80, 80, 96, 96, 112, 112, 128, 128, 160, 160, 192, 192, 224, 224,
                              256, 256, 320, 320, 384, 384, 448, 448, 512, 512, 640, 640, 768, 768, 896, 896,
                              1024, 1024, 1152, 1152, 1280, 1280, 1536, 1536]
                frame_size = frame_sizes[frame_size_code] * 2 if frame_size_code < len(frame_sizes) else 0
                
                return AC3SyncHeader(
                    frame_type="audio",
                    codec="eac3" if stream_type == 0x87 else "ac3",
                    sample_rate=sample_rate,
                    bitstream_mode=bitstream_mode,
                    audio_coding_mode=audio_coding_mode,
                    frame_size=frame_size
                )
        
        return None
