# DVB Parser P1 扩展实施计划

> **致自动化代理：** 必须使用子代理驱动开发（推荐）或执行计划子技能来逐任务实施本计划。步骤使用复选框（`- [ ]`）语法进行跟踪。

**目标：** 在 MVP 基础上扩展实现 SDT、NIT、PES 三个解析器

**架构：** 遵循现有 MVP 的分层解析器链架构，每个协议层有独立的 Parser 类，返回结构化 dataclass 对象。PES 解析器额外支持 ES 帧头解析（H.264/H.265/AAC/MP3/AC3/E-AC3）。

**技术栈：** Python 3.8+, dataclasses, struct, pytest

---

## 文件结构

```
dvb-parser/
├── src/dvb_parser/
│   ├── si/                    # 新增
│   │   ├── __init__.py
│   │   ├── models.py          # SDT, NIT 数据模型
│   │   ├── sdt.py             # SDT 解析器
│   │   └── nit.py             # NIT 解析器
│   ├── pes/                   # 新增
│   │   ├── __init__.py
│   │   ├── models.py          # PES, ES 帧头数据模型
│   │   └── parser.py          # PES 解析器
│   └── __init__.py            # 更新导入
├── tests/
│   ├── test_si.py             # 新增
│   └── test_pes.py            # 新增
└── ...
```

---

## 任务 1：SI 数据模型

**文件：**
- 创建：`src/dvb_parser/si/__init__.py`
- 创建：`src/dvb_parser/si/models.py`

- [ ] **步骤 1：创建 si/__init__.py**

```python
"""SI (Service Information) parser module"""
```

- [ ] **步骤 2：实现 SI 数据模型**

```python
# src/dvb_parser/si/models.py
"""
SI data models (SDT, NIT)
"""

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

- [ ] **步骤 3：提交**

```bash
git add src/dvb_parser/si/
git commit -m "feat: add SI data models (SDT, NIT)"
```

---

## 任务 2：SDT 解析器

**文件：**
- 创建：`src/dvb_parser/si/sdt.py`
- 创建：`tests/test_si.py`

- [ ] **步骤 1：编写 SDT 解析器测试**

```python
# tests/test_si.py
import pytest
from dvb_parser.si.sdt import SDTParser

class TestSDTParser:
    def test_parse_valid_sdt(self):
        """测试解析有效的 SDT"""
        # 构造 SDT section
        section_data = bytes([
            0x42,                    # table_id (current TS)
            0b10110000, 0x1F,        # syntax_indicator=1, length=31
            0x00, 0x01,              # transport_stream_id
            0b11000001,              # version=1, current_next=1
            0x00,                    # original_network_id high
            0x01,                    # original_network_id low
            0x00,                    # section_number
            0x00,                    # last_section_number
            # Service entry
            0x00, 0x01,              # service_id=1
            0b11111100,              # reserved, EIT flags
            0b00000001,              # running_status=0, free_ca=0, descriptors_length=1
            # Service descriptor (tag=0x48, length=5)
            0x48, 0x05,              # descriptor_tag, descriptor_length
            0x01,                    # service_type=1 (SD TV)
            0x02,                    # provider_name_length=2
            0x54, 0x56,              # provider_name="TV"
            0x02,                    # service_name_length=2
            0x48, 0x44,              # service_name="HD"
            # CRC-32 placeholder
            0x00, 0x00, 0x00, 0x00
        ])
        
        # Calculate correct CRC-32
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')
        
        sdt = SDTParser.parse(section_data)
        
        assert sdt.table_id == 0x42
        assert sdt.transport_stream_id == 1
        assert sdt.original_network_id == 1
        assert len(sdt.services) == 1
        assert sdt.services[0].service_id == 1
        assert sdt.services[0].service_type == 1
        assert sdt.services[0].provider_name == "TV"
        assert sdt.services[0].service_name == "HD"
    
    def test_parse_sdt_other_ts(self):
        """测试解析其他 TS 的 SDT"""
        section_data = bytes([
            0x46,                    # table_id (other TS)
            0b10110000, 0x0F,        # syntax_indicator=1, length=15
            0x00, 0x02,              # transport_stream_id
            0b11000001,              # version=1, current_next=1
            0x00, 0x01,              # original_network_id
            0x00,                    # section_number
            0x00,                    # last_section_number
            # Service entry
            0x00, 0x01,              # service_id=1
            0b11111100,              # reserved, EIT flags
            0b00000001,              # running_status=0, free_ca=0, descriptors_length=1
            # Empty descriptor
            0x00, 0x00,              # descriptor_tag=0, length=0
            # CRC-32 placeholder
            0x00, 0x00, 0x00, 0x00
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')
        
        sdt = SDTParser.parse(section_data)
        
        assert sdt.table_id == 0x46
        assert len(sdt.services) == 1
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/test_si.py -v
```

预期：FAIL - 模块不存在

- [ ] **步骤 3：实现 SDT 解析器**

```python
# src/dvb_parser/si/sdt.py
"""
SDT (Service Description Table) parser
"""

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

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/test_si.py -v
```

预期：PASS

- [ ] **步骤 5：提交**

```bash
git add src/dvb_parser/si/sdt.py tests/test_si.py
git commit -m "feat: add SDT parser with service descriptor parsing"
```

---

## 任务 3：NIT 解析器

**文件：**
- 创建：`src/dvb_parser/si/nit.py`
- 修改：`tests/test_si.py`

- [ ] **步骤 1：添加 NIT 解析器测试**

```python
# tests/test_si.py (追加)
from dvb_parser.si.nit import NITParser

class TestNITParser:
    def test_parse_valid_nit(self):
        """测试解析有效的 NIT"""
        # 构造 NIT section
        section_data = bytes([
            0x40,                    # table_id (current network)
            0b10110000, 0x20,        # syntax_indicator=1, length=32
            0x00, 0x01,              # network_id
            0b11000001,              # version=1, current_next=1
            0x00,                    # section_number
            0x00,                    # last_section_number
            # Network descriptors
            0b11110000, 0x07,        # descriptors_length=7
            # Network name descriptor
            0x40, 0x05,              # descriptor_tag=0x40, length=5
            0x53, 0x61, 0x74, 0x65, 0x6C,  # "Satel"
            # Transport stream loop
            0b11110000, 0x11,        # ts_loop_length=17
            # Transport stream entry
            0x00, 0x01,              # transport_stream_id
            0x00, 0x01,              # original_network_id
            0b11110000, 0x0D,        # descriptors_length=13
            # Satellite delivery system descriptor
            0x43, 0x0B,              # descriptor_tag=0x43, length=11
            0x01, 0x18, 0x05, 0x68,  # frequency (BCD: 11805.68 MHz)
            0x00, 0x00,              # orbital position
            0b11000000,              # polarization (horizontal)
            0b00000010,              # modulation (8PSK)
            0x02, 0x58, 0x00,        # symbol_rate (BCD: 25000 ksym/s)
            # CRC-32 placeholder
            0x00, 0x00, 0x00, 0x00
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')
        
        nit = NITParser.parse(section_data)
        
        assert nit.table_id == 0x40
        assert nit.network_id == 1
        assert nit.network_name == "Satel"
        assert len(nit.transport_streams) == 1
        assert nit.transport_streams[0].transport_stream_id == 1
        assert nit.transport_streams[0].frequency == 11805680000  # Hz
        assert nit.transport_streams[0].symbol_rate == 25000000  # sym/s
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/test_si.py::TestNITParser -v
```

预期：FAIL - 模块不存在

- [ ] **步骤 3：实现 NIT 解析器**

```python
# src/dvb_parser/si/nit.py
"""
NIT (Network Information Table) parser
"""

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

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/test_si.py -v
```

预期：PASS

- [ ] **步骤 5：提交**

```bash
git add src/dvb_parser/si/nit.py tests/test_si.py
git commit -m "feat: add NIT parser with satellite delivery system descriptor"
```

---

## 任务 4：PES 数据模型

**文件：**
- 创建：`src/dvb_parser/pes/__init__.py`
- 创建：`src/dvb_parser/pes/models.py`

- [ ] **步骤 1：创建 pes/__init__.py**

```python
"""PES (Packetized Elementary Stream) parser module"""
```

- [ ] **步骤 2：实现 PES 数据模型**

```python
# src/dvb_parser/pes/models.py
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
```

- [ ] **步骤 3：提交**

```bash
git add src/dvb_parser/pes/
git commit -m "feat: add PES data models with ES frame header types"
```

---

## 任务 5：PES 解析器

**文件：**
- 创建：`src/dvb_parser/pes/parser.py`
- 创建：`tests/test_pes.py`

- [ ] **步骤 1：编写 PES 解析器测试**

```python
# tests/test_pes.py
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
            0x50,                    # profile=1 (AAC-LC), sampling_freq_idx=4 (44100Hz)
            0x80,                    # channel_config=2 (stereo)
            0x00, 0x01, 0xC0,        # frame_length=448
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
            0x60,                    # sample_rate_idx=1 (44100Hz), bitstream_mode=0
            0x04,                    # audio_coding_mode=2 (stereo), frame_size_code=4
            0x00, 0x00
        ])
        
        header = PESParser._parse_ac3_header(payload, 0x81)
        
        assert header is not None
        assert header.codec == "ac3"
        assert header.sample_rate == 44100
        assert header.audio_coding_mode == 2
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/test_pes.py -v
```

预期：FAIL - 模块不存在

- [ ] **步骤 3：实现 PES 解析器**

```python
# src/dvb_parser/pes/parser.py
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
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/test_pes.py -v
```

预期：PASS

- [ ] **步骤 5：提交**

```bash
git add src/dvb_parser/pes/parser.py tests/test_pes.py
git commit -m "feat: add PES parser with ES frame header support"
```

---

## 任务 6：完善包导入

**文件：**
- 修改：`src/dvb_parser/__init__.py`
- 修改：`src/dvb_parser/si/__init__.py`
- 修改：`src/dvb_parser/pes/__init__.py`

- [ ] **步骤 1：更新 si/__init__.py**

```python
"""SI (Service Information) parser module"""

from dvb_parser.si.sdt import SDTParser
from dvb_parser.si.nit import NITParser
from dvb_parser.si.models import SDT, SDTService, NIT, NITTransportStream

__all__ = [
    "SDTParser",
    "NITParser",
    "SDT",
    "SDTService",
    "NIT",
    "NITTransportStream",
]
```

- [ ] **步骤 2：更新 pes/__init__.py**

```python
"""PES (Packetized Elementary Stream) parser module"""

from dvb_parser.pes.parser import PESParser
from dvb_parser.pes.models import (
    PESPacket, PESHeader, ESFrameHeader,
    H264NALUHeader, H265NALUHeader,
    AACADTSHeader, MP3FrameHeader, AC3SyncHeader
)

__all__ = [
    "PESParser",
    "PESPacket",
    "PESHeader",
    "ESFrameHeader",
    "H264NALUHeader",
    "H265NALUHeader",
    "AACADTSHeader",
    "MP3FrameHeader",
    "AC3SyncHeader",
]
```

- [ ] **步骤 3：更新 dvb_parser/__init__.py**

```python
"""
DVB Parser - DVB protocol parser for satellite signal analysis
"""

__version__ = "0.2.0"

from dvb_parser.bbframe.parser import BBFrameParser
from dvb_parser.bbframe.models import BBFrame, BBFrameHeader, StreamType
from dvb_parser.ts.parser import TSPacketParser
from dvb_parser.ts.models import TSPacket, AdaptationField
from dvb_parser.psi.pat import PATParser
from dvb_parser.psi.pmt import PMTParser
from dvb_parser.psi.models import PAT, PMT, PATEntry, PMTStream
from dvb_parser.si.sdt import SDTParser
from dvb_parser.si.nit import NITParser
from dvb_parser.si.models import SDT, SDTService, NIT, NITTransportStream
from dvb_parser.pes.parser import PESParser
from dvb_parser.pes.models import (
    PESPacket, PESHeader, ESFrameHeader,
    H264NALUHeader, H265NALUHeader,
    AACADTSHeader, MP3FrameHeader, AC3SyncHeader
)

__all__ = [
    # BBFrame
    "BBFrameParser",
    "BBFrame",
    "BBFrameHeader",
    "StreamType",
    # MPEG-TS
    "TSPacketParser",
    "TSPacket",
    "AdaptationField",
    # PSI
    "PATParser",
    "PMTParser",
    "PAT",
    "PMT",
    "PATEntry",
    "PMTStream",
    # SI
    "SDTParser",
    "NITParser",
    "SDT",
    "SDTService",
    "NIT",
    "NITTransportStream",
    # PES
    "PESParser",
    "PESPacket",
    "PESHeader",
    "ESFrameHeader",
    "H264NALUHeader",
    "H265NALUHeader",
    "AACADTSHeader",
    "MP3FrameHeader",
    "AC3SyncHeader",
]
```

- [ ] **步骤 4：运行所有测试**

```bash
pytest -v
```

预期：所有测试通过

- [ ] **步骤 5：提交**

```bash
git add src/dvb_parser/__init__.py src/dvb_parser/si/__init__.py src/dvb_parser/pes/__init__.py
git commit -m "feat: complete P1 package imports"
```

---

## 任务 7：集成测试

**文件：**
- 修改：`tests/test_integration.py`

- [ ] **步骤 1：添加 P1 集成测试**

```python
# tests/test_integration.py (追加)
from dvb_parser.si.sdt import SDTParser
from dvb_parser.si.nit import NITParser
from dvb_parser.pes.parser import PESParser

class TestIntegrationP1:
    def test_sdt_with_pmt(self):
        """测试 SDT 与 PMT 关联"""
        # 构造 SDT 数据
        sdt_data = bytes([
            0x42,                    # table_id
            0b10110000, 0x1F,        # length
            0x00, 0x01,              # transport_stream_id
            0b11000001,              # version=1
            0x00, 0x01,              # original_network_id
            0x00, 0x00,              # section numbers
            # Service entry
            0x00, 0x01,              # service_id=1 (matches PMT program_number)
            0b11111100,
            0b00000001,
            # Service descriptor
            0x48, 0x05,
            0x01,                    # service_type
            0x02, 0x54, 0x56,        # provider="TV"
            0x02, 0x48, 0x44,        # service_name="HD"
            # CRC-32
            0x00, 0x00, 0x00, 0x00
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(sdt_data[:-4])
        sdt_data = sdt_data[:-4] + crc_value.to_bytes(4, 'big')
        
        sdt = SDTParser.parse(sdt_data)
        
        # 验证 SDT.service_id 对应 PMT.program_number
        assert sdt.services[0].service_id == 1
        assert sdt.services[0].service_name == "HD"
    
    def test_nit_with_bbframe(self):
        """测试 NIT 获取传输参数"""
        # 构造 NIT 数据
        nit_data = bytes([
            0x40,                    # table_id
            0b10110000, 0x20,        # length
            0x00, 0x01,              # network_id
            0b11000001,              # version=1
            0x00, 0x00,              # section numbers
            # Network descriptors
            0b11110000, 0x05,
            0x40, 0x03,              # network_name="Sat"
            0x53, 0x61, 0x74,
            # Transport stream loop
            0b11110000, 0x11,
            0x00, 0x01, 0x00, 0x01,  # ts_id, original_network_id
            0b11110000, 0x0D,
            # Satellite descriptor
            0x43, 0x0B,
            0x01, 0x18, 0x05, 0x68,  # frequency
            0x00, 0x00,              # orbital position
            0b11000000,              # polarization
            0b00000010,              # modulation (8PSK)
            0x02, 0x58, 0x00,        # symbol_rate
            # CRC-32
            0x00, 0x00, 0x00, 0x00
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(nit_data[:-4])
        nit_data = nit_data[:-4] + crc_value.to_bytes(4, 'big')
        
        nit = NITParser.parse(nit_data)
        
        # 验证从 NIT 获取的频率、调制方式可用于 BBFrame 解析
        assert nit.transport_streams[0].frequency == 11805680000  # Hz
        assert nit.transport_streams[0].symbol_rate == 25000000  # sym/s
```

- [ ] **步骤 2：运行集成测试**

```bash
pytest tests/test_integration.py -v
```

预期：PASS

- [ ] **步骤 3：提交**

```bash
git add tests/test_integration.py
git commit -m "test: add P1 integration tests for SDT, NIT"
```

---

## 任务 8：最终验证

- [ ] **步骤 1：运行完整测试套件**

```bash
pytest -v --cov=src/dvb_parser
```

预期：所有测试通过，覆盖率 > 80%

- [ ] **步骤 2：验证包安装**

```bash
pip install -e .
python -c "from dvb_parser import SDTParser, NITParser, PESParser; print('Import successful')"
```

预期：Import successful

- [ ] **步骤 3：最终提交**

```bash
git add .
git commit -m "feat: complete P1 expansion - SDT, NIT, PES parsers"
```

---

## 后续任务（P2 优先级）

以下任务在 P1 完成后实施：

- GSE 解析器 - 通用流封装
- MPE 解析器 - 多协议封装
- ULE 解析器 - 单向轻量封装
- NIP 解析器 - 网络无关协议
- EIT 解析器 - 事件信息表
- TDT 解析器 - 时间日期表
