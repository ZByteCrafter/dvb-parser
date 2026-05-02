# DVB Parser P1 扩展设计规范

**日期**: 2026-05-03
**状态**: 草稿
**作者**: AI Assistant

## 1. 扩展概述

### 1.1 目标

在 MVP（BBFrame、MPEG-TS、PAT、PMT）基础上，扩展实现 P1 优先级的三个解析器：
- SDT Parser - 业务描述表
- NIT Parser - 网络信息表
- PES Parser - 包化基本流（含 ES 帧头解析）

### 1.2 范围

- **SDT Parser**: 解析业务描述表，获取节目名称、提供商、业务类型
- **NIT Parser**: 解析网络信息表，获取频率、调制方式、符号率等参数
- **PES Parser**: 解析 PES 包头（PTS/DTS）+ ES 帧头（H.264/H.265/AAC/MP3/AC3/E-AC3）

### 1.3 依赖关系

```
MVP 已完成:
├── BBFrame Parser (P0)
├── MPEG-TS Parser (P0)
├── PAT Parser (P0)
└── PMT Parser (P0)

P1 扩展:
├── SDT Parser → 依赖 TS Parser
├── NIT Parser → 依赖 TS Parser
└── PES Parser → 依赖 TS Parser, PAT, PMT
```

## 2. SDT 解析器设计

### 2.1 协议规范

**协议出处**: ETSI EN 300 468 §6.2.3

**表结构**:
- Table ID: 0x42 (当前 TS) / 0x46 (其他 TS)
- Section Syntax Indicator: 1
- Section Length: 可变
- Transport Stream ID: 传输流标识
- Original Network ID: 原始网络标识
- Version Number: 5 bits
- Current/Next Indicator: 1 bit
- Section Number: 8 bits
- Last Section Number: 8 bits
- Service Loop: 业务列表
  - Service ID: 16 bits (对应 PMT 的 program_number)
  - EIT Schedule Flag: 1 bit
  - EIT Present/Following Flag: 1 bit
  - Running Status: 3 bits
  - Free CA Mode: 1 bit
  - Descriptors Loop Length: 12 bits
  - Descriptors: 可变长描述符

### 2.2 数据模型

```python
# src/dvb_parser/si/models.py

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SDTService:
    """SDT 业务条目"""
    service_id: int
    eit_schedule_flag: bool
    eit_present_following_flag: bool
    running_status: int
    free_ca_mode: bool
    descriptors: List[bytes]
    # 从描述符中解析的字段
    service_type: int = 0
    service_name: str = ""
    provider_name: str = ""


@dataclass
class SDT:
    """业务描述表"""
    table_id: int
    transport_stream_id: int
    original_network_id: int
    version_number: int
    current_next_indicator: bool
    section_number: int
    last_section_number: int
    services: List[SDTService]
```

### 2.3 解析器实现

```python
# src/dvb_parser/si/sdt.py

import struct
from typing import List

from dvb_parser.si.models import SDT, SDTService
from dvb_parser.utils.crc import crc32


class SDTParser:
    """SDT 解析器"""
    
    @staticmethod
    def parse(data: bytes, offset: int = 0) -> SDT:
        """
        解析 SDT section
        
        Args:
            data: 原始 section 数据
            offset: 起始偏移
        
        Returns:
            SDT 对象
        
        Raises:
            ValueError: CRC-32 校验失败或数据无效
        """
        if len(data) - offset < 12:
            raise ValueError("数据不足")
        
        # 解析表头
        table_id = data[offset]
        if table_id not in (0x42, 0x46):
            raise ValueError("不是 SDT 表")
        
        # Section syntax indicator 和 length
        syntax_length = struct.unpack('>H', data[offset + 1:offset + 3])[0]
        section_length = syntax_length & 0x0FFF
        
        # Transport stream ID
        ts_id = struct.unpack('>H', data[offset + 3:offset + 5])[0]
        
        # Original network ID
        original_network_id = struct.unpack('>H', data[offset + 5:offset + 7])[0]
        
        # Version 和 current/next indicator
        version_current = data[offset + 7]
        version_number = (version_current >> 1) & 0x1F
        current_next_indicator = bool(version_current & 0x01)
        
        # Section numbers
        section_number = data[offset + 8]
        last_section_number = data[offset + 9]
        
        # 解析业务列表
        services = []
        services_end = offset + 3 + section_length - 4  # 4 bytes for CRC-32
        
        current_offset = offset + 11  # 跳过固定头部
        
        while current_offset < services_end:
            if current_offset + 5 > len(data):
                break
            
            # 解析业务信息
            service_id = struct.unpack('>H', data[current_offset:current_offset + 2])[0]
            eit_schedule = bool(data[current_offset + 2] & 0x02)
            eit_present_following = bool(data[current_offset + 2] & 0x01)
            running_status = (data[current_offset + 3] >> 5) & 0x07
            free_ca_mode = bool(data[current_offset + 3] & 0x10)
            descriptors_length = struct.unpack('>H', data[current_offset + 3:current_offset + 5])[0] & 0x0FFF
            
            # 提取描述符
            descriptors = []
            desc_end = current_offset + 5 + descriptors_length
            desc_offset = current_offset + 5
            
            service_type = 0
            service_name = ""
            provider_name = ""
            
            while desc_offset < desc_end and desc_offset + 2 <= len(data):
                desc_tag = data[desc_offset]
                desc_length = data[desc_offset + 1]
                desc_data = data[desc_offset:desc_offset + 2 + desc_length]
                descriptors.append(desc_data)
                
                # 解析业务描述符
                if desc_tag == 0x48 and desc_length >= 3:  # Service descriptor
                    service_type = data[desc_offset + 2]
                    provider_length = data[desc_offset + 3]
                    if desc_offset + 4 + provider_length <= desc_end:
                        provider_name = data[desc_offset + 4:desc_offset + 4 + provider_length].decode('utf-8', errors='replace')
                    service_name_length = data[desc_offset + 4 + provider_length]
                    name_offset = desc_offset + 5 + provider_length
                    if name_offset + service_name_length <= desc_end:
                        service_name = data[name_offset:name_offset + service_name_length].decode('utf-8', errors='replace')
                
                desc_offset += 2 + desc_length
            
            services.append(SDTService(
                service_id=service_id,
                eit_schedule_flag=eit_schedule,
                eit_present_following_flag=eit_present_following,
                running_status=running_status,
                free_ca_mode=free_ca_mode,
                descriptors=descriptors,
                service_type=service_type,
                service_name=service_name,
                provider_name=provider_name
            ))
            
            current_offset = desc_end
        
        # 验证 CRC-32
        section_data = data[offset:offset + 3 + section_length]
        if len(section_data) >= 4:
            expected_crc = struct.unpack('>I', section_data[-4:])[0]
            calculated_crc = crc32(section_data[:-4])
            if expected_crc != calculated_crc:
                raise ValueError("CRC-32 校验失败")
        
        return SDT(
            table_id=table_id,
            transport_stream_id=ts_id,
            original_network_id=original_network_id,
            version_number=version_number,
            current_next_indicator=current_next_indicator,
            section_number=section_number,
            last_section_number=last_section_number,
            services=services
        )
```

### 2.4 解析难点

| 难点 | 说明 |
|------|------|
| **描述符循环** | 需要递归解析 descriptor_tag + descriptor_length |
| **字符编码** | ISO 6937/UTF-8 编码支持 |
| **多语言** | 业务名称可能有多种语言版本 |
| **业务类型** | 需要映射到标准业务类型（SD TV、HD TV、UHD TV 等） |

## 3. NIT 解析器设计

### 3.1 协议规范

**协议出处**: ETSI EN 300 468 §6.2.1

**表结构**:
- Table ID: 0x40 (当前网络) / 0x41 (其他网络)
- Section Syntax Indicator: 1
- Section Length: 可变
- Network ID: 网络标识
- Version Number: 5 bits
- Current/Next Indicator: 1 bit
- Section Number: 8 bits
- Last Section Number: 8 bits
- Network Descriptors Loop: 网络描述符
- Transport Stream Loop: 传输流列表
  - Transport Stream ID: 16 bits
  - Original Network ID: 16 bits
  - Transport Descriptors Loop: 传输流描述符

### 3.2 数据模型

```python
# src/dvb_parser/si/models.py (追加)

@dataclass
class NITTransportStream:
    """NIT 传输流条目"""
    transport_stream_id: int
    original_network_id: int
    descriptors: List[bytes]
    # 从描述符中解析的字段
    frequency: int = 0  # Hz
    modulation: int = 0  # QPSK, 8PSK, 16APSK 等
    symbol_rate: int = 0
    polarization: int = 0  # 水平/垂直


@dataclass
class NIT:
    """网络信息表"""
    table_id: int
    network_id: int
    version_number: int
    current_next_indicator: bool
    section_number: int
    last_section_number: int
    network_name: str
    transport_streams: List[NITTransportStream]
```

### 3.3 解析器实现

```python
# src/dvb_parser/si/nit.py

import struct
from typing import List

from dvb_parser.si.models import NIT, NITTransportStream
from dvb_parser.utils.crc import crc32


class NITParser:
    """NIT 解析器"""
    
    @staticmethod
    def parse(data: bytes, offset: int = 0) -> NIT:
        """
        解析 NIT section
        
        Args:
            data: 原始 section 数据
            offset: 起始偏移
        
        Returns:
            NIT 对象
        
        Raises:
            ValueError: CRC-32 校验失败或数据无效
        """
        if len(data) - offset < 12:
            raise ValueError("数据不足")
        
        # 解析表头
        table_id = data[offset]
        if table_id not in (0x40, 0x41):
            raise ValueError("不是 NIT 表")
        
        # Section syntax indicator 和 length
        syntax_length = struct.unpack('>H', data[offset + 1:offset + 3])[0]
        section_length = syntax_length & 0x0FFF
        
        # Network ID
        network_id = struct.unpack('>H', data[offset + 3:offset + 5])[0]
        
        # Version 和 current/next indicator
        version_current = data[offset + 5]
        version_number = (version_current >> 1) & 0x1F
        current_next_indicator = bool(version_current & 0x01)
        
        # Section numbers
        section_number = data[offset + 6]
        last_section_number = data[offset + 7]
        
        # 解析网络描述符
        network_descriptors_length = struct.unpack('>H', data[offset + 8:offset + 10])[0] & 0x0FFF
        
        network_name = ""
        desc_offset = offset + 10
        desc_end = desc_offset + network_descriptors_length
        
        while desc_offset < desc_end and desc_offset + 2 <= len(data):
            desc_tag = data[desc_offset]
            desc_length = data[desc_offset + 1]
            
            # 解析网络名称描述符
            if desc_tag == 0x40 and desc_length > 0:
                network_name = data[desc_offset + 2:desc_offset + 2 + desc_length].decode('utf-8', errors='replace')
            
            desc_offset += 2 + desc_length
        
        # 解析传输流列表
        transport_streams = []
        ts_loop_length = struct.unpack('>H', data[desc_end:desc_end + 2])[0] & 0x0FFF
        
        current_offset = desc_end + 2
        ts_end = current_offset + ts_loop_length
        
        while current_offset < ts_end:
            if current_offset + 6 > len(data):
                break
            
            # 解析传输流信息
            ts_id = struct.unpack('>H', data[current_offset:current_offset + 2])[0]
            original_network_id = struct.unpack('>H', data[current_offset + 2:current_offset + 4])[0]
            ts_descriptors_length = struct.unpack('>H', data[current_offset + 4:current_offset + 6])[0] & 0x0FFF
            
            # 提取描述符
            descriptors = []
            ts_desc_end = current_offset + 6 + ts_descriptors_length
            ts_desc_offset = current_offset + 6
            
            frequency = 0
            modulation = 0
            symbol_rate = 0
            polarization = 0
            
            while ts_desc_offset < ts_desc_end and ts_desc_offset + 2 <= len(data):
                desc_tag = data[ts_desc_offset]
                desc_length = data[ts_desc_offset + 1]
                desc_data = data[ts_desc_offset:ts_desc_offset + 2 + desc_length]
                descriptors.append(desc_data)
                
                # 解析卫星传输系统描述符
                if desc_tag == 0x43 and desc_length >= 11:  # Satellite delivery system descriptor
                    # 频率 (BCD 编码, 4 bytes)
                    freq_bcd = data[ts_desc_offset + 2:ts_desc_offset + 6]
                    frequency = NITParser._bcd_to_int(freq_bcd) * 10  # kHz → Hz
                    
                    # 轨道位置 (BCD 编码, 2 bytes)
                    # orbital_position = struct.unpack('>H', data[ts_desc_offset + 6:ts_desc_offset + 8])[0]
                    
                    # 极化方式
                    polarization = (data[ts_desc_offset + 8] >> 6) & 0x03
                    
                    # 调制方式
                    modulation = data[ts_desc_offset + 9] & 0x03
                    
                    # 符号率 (BCD 编码, 3 bytes)
                    sr_bcd = data[ts_desc_offset + 10:ts_desc_offset + 13]
                    symbol_rate = NITParser._bcd_to_int(sr_bcd) * 100  # ksym/s → sym/s
                
                ts_desc_offset += 2 + desc_length
            
            transport_streams.append(NITTransportStream(
                transport_stream_id=ts_id,
                original_network_id=original_network_id,
                descriptors=descriptors,
                frequency=frequency,
                modulation=modulation,
                symbol_rate=symbol_rate,
                polarization=polarization
            ))
            
            current_offset = ts_desc_end
        
        # 验证 CRC-32
        section_data = data[offset:offset + 3 + section_length]
        if len(section_data) >= 4:
            expected_crc = struct.unpack('>I', section_data[-4:])[0]
            calculated_crc = crc32(section_data[:-4])
            if expected_crc != calculated_crc:
                raise ValueError("CRC-32 校验失败")
        
        return NIT(
            table_id=table_id,
            network_id=network_id,
            version_number=version_number,
            current_next_indicator=current_next_indicator,
            section_number=section_number,
            last_section_number=last_section_number,
            network_name=network_name,
            transport_streams=transport_streams
        )
    
    @staticmethod
    def _bcd_to_int(bcd_bytes: bytes) -> int:
        """BCD 编码转整数"""
        result = 0
        for byte in bcd_bytes:
            result = result * 100 + (byte >> 4) * 10 + (byte & 0x0F)
        return result
```

### 3.4 解析难点

| 难点 | 说明 |
|------|------|
| **BCD 编码** | 频率和符号率使用 BCD 编码 |
| **卫星描述符** | 需要解析卫星传输系统描述符 |
| **极化方式** | 水平/垂直/左旋/右旋 |
| **调制方式** | QPSK、8PSK、16APSK 等 |
| **多种传输系统** | 卫星、地面、有线描述符格式不同 |

## 4. PES 解析器设计

### 4.1 协议规范

**协议出处**: ISO/IEC 13818-1 §2.4.3

**PES 包结构**:
- Packet Start Code Prefix: 24 bits (0x000001)
- Stream ID: 8 bits
- PES Packet Length: 16 bits
- Optional PES Header:
  - PTS/DTS Flags: 2 bits
  - PTS: 33 bits (可选)
  - DTS: 33 bits (可选)
  - ESCR: 48 bits (可选)
  - ES Rate: 24 bits (可选)
- PES Payload: ES 数据

### 4.2 数据模型

```python
# src/dvb_parser/pes/models.py

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
```

### 4.3 解析器实现

```python
# src/dvb_parser/pes/parser.py

import struct
from typing import Optional

from dvb_parser.pes.models import (
    PESPacket, PESHeader, ESFrameHeader,
    H264NALUHeader, H265NALUHeader,
    AACADTSHeader, MP3FrameHeader, AC3SyncHeader
)


class PESParser:
    """PES 解析器"""
    
    # Stream ID 映射
    STREAM_ID_MAP = {
        0xBC: "program_stream_map",
        0xBD: "private_stream_1",
        0xBE: "padding_stream",
        0xBF: "private_stream_2",
        0xC0: "audio_stream_0",
        0xE0: "video_stream_0",
    }
    
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
        # 4 bits marker + 3 bits PTS[32:30] + 1 bit marker
        # 15 bits PTS[29:15] + 1 bit marker
        # 15 bits PTS[14:0] + 1 bit marker
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
```

### 4.4 解析难点

| 难点 | 说明 |
|------|------|
| **PTS/DTS 解析** | 33-bit 扩展时间戳，需要跨字节提取 |
| **ES 帧头定位** | 需要在 PES payload 中搜索同步字 |
| **多种编码格式** | H.264/H.265/AAC/MP3/AC3 帧头格式不同 |
| **跨包重组** | ES 帧可能跨多个 PES 包 |
| **比特率计算** | MP3 比特率需要查表 |

## 5. 项目结构更新

```
dvb-parser/
├── src/dvb_parser/
│   ├── __init__.py
│   ├── bbframe/
│   ├── ts/
│   ├── psi/
│   ├── si/                    # 新增
│   │   ├── __init__.py
│   │   ├── sdt.py             # 新增
│   │   ├── nit.py             # 新增
│   │   └── models.py          # 新增
│   ├── pes/                   # 新增
│   │   ├── __init__.py
│   │   ├── parser.py          # 新增
│   │   └── models.py          # 新增
│   └── utils/
├── tests/
│   ├── test_si.py             # 新增
│   └── test_pes.py            # 新增
└── ...
```

## 6. 测试策略

### 6.1 单元测试

每个解析器独立测试：

```python
# tests/test_si.py
class TestSDTParser:
    def test_parse_valid_sdt(self):
        """测试解析有效的 SDT"""
        # 构造包含业务名称的 SDT 数据
        # 验证 service_name, provider_name 解析正确
    
    def test_parse_sdt_with_multiple_services(self):
        """测试解析包含多个业务的 SDT"""
        # 验证多个 service 正确解析

class TestNITParser:
    def test_parse_valid_nit(self):
        """测试解析有效的 NIT"""
        # 构造包含卫星传输系统描述符的 NIT 数据
        # 验证 frequency, modulation, symbol_rate 解析正确

# tests/test_pes.py
class TestPESParser:
    def test_parse_pes_with_pts_dts(self):
        """测试解析包含 PTS/DTS 的 PES"""
        # 验证 PTS, DTS 解析正确
    
    def test_parse_h264_nalu_header(self):
        """测试解析 H.264 NALU 头"""
        # 验证 nal_unit_type, nal_ref_idc 解析正确
    
    def test_parse_aac_adts_header(self):
        """测试解析 AAC ADTS 头"""
        # 验证 profile, sampling_frequency, channel_configuration 解析正确
```

### 6.2 集成测试

```python
# tests/test_integration.py (追加)
class TestIntegrationP1:
    def test_sdt_with_pmt(self):
        """测试 SDT 与 PMT 关联"""
        # 验证 SDT.service_id 对应 PMT.program_number
    
    def test_nit_with_bbframe(self):
        """测试 NIT 获取传输参数"""
        # 验证从 NIT 获取的频率、调制方式可用于 BBFrame 解析
    
    def test_pes_with_pmt(self):
        """测试 PES 与 PMT 关联"""
        # 验证 PES.stream_type 对应 PMT.stream_type
```

## 7. 未来扩展

### 7.1 P2 解析器

在 P1 完成后，可继续实现 P2 解析器：
- GSE Parser - 通用流封装
- MPE Parser - 多协议封装
- ULE Parser - 单向轻量封装
- NIP Parser - 网络无关协议
- EIT Parser - 事件信息表
- TDT Parser - 时间日期表

### 7.2 功能增强

- 流式解析支持
- 描述符递归解析
- 多语言字符编码支持
- ES 帧重组
