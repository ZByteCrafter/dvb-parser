# DVB Parser P2 扩展设计规范

**日期**: 2026-05-03
**状态**: 草稿
**作者**: AI Assistant

## 1. 扩展概述

### 1.1 目标

在 P0（BBFrame、MPEG-TS、PAT、PMT）和 P1（SDT、NIT、PES）基础上，扩展实现 P2 优先级的六个解析器：
- GSE Parser - 通用流封装
- MPE Parser - 多协议封装
- ULE Parser - 单向轻量封装
- NIP Parser - 网络无关协议
- EIT Parser - 事件信息表
- TDT Parser - 时间日期表

### 1.2 依赖关系

```
P0 已完成:
├── BBFrame Parser
├── MPEG-TS Parser
├── PAT Parser
└── PMT Parser

P1 已完成:
├── SDT Parser
├── NIT Parser
└── PES Parser

P2 扩展:
├── GSE Parser → 依赖 BBFrame Parser
├── MPE Parser → 依赖 TS Parser
├── ULE Parser → 依赖 TS Parser
├── NIP Parser → 依赖 TS Parser
├── EIT Parser → 依赖 TS Parser
└── TDT Parser → 依赖 TS Parser
```

## 2. GSE 解析器设计

### 2.1 协议规范

**协议出处**: ETSI EN 102 772

**包结构**:
- Start/End 标志: 2 bits
- Label: 0/3/6 bytes（可选）
- Protocol Type: 16 bits（如 0x0800 = IPv4, 0x86DD = IPv6）
- Total Length: 16 bits（可选）
- Payload: IP 数据报（可能分片）
- CRC-32: 32 bits

**分片机制**:
- Start=1, End=1: 完整包（无分片）
- Start=1, End=0: 分片开始
- Start=0, End=0: 分片中间
- Start=0, End=1: 分片结束

### 2.2 数据模型

```python
# src/dvb_parser/gse/models.py

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class GSEPacket:
    """GSE 包"""
    start: bool
    end: bool
    label_type: int  # 0=无, 1=6字节, 2=3字节, 3=未使用
    protocol_type: int
    total_length: Optional[int]
    label: Optional[bytes]
    payload: bytes
    crc32: int
    
    @property
    def is_complete(self) -> bool:
        """是否为完整包（无分片）"""
        return self.start and self.end
    
    @property
    def is_fragment_start(self) -> bool:
        """是否为分片开始"""
        return self.start and not self.end
    
    @property
    def is_fragment_continue(self) -> bool:
        """是否为分片中间"""
        return not self.start and not self.end
    
    @property
    def is_fragment_end(self) -> bool:
        """是否为分片结束"""
        return not self.start and self.end
    
    @property
    def is_ipv4(self) -> bool:
        """是否为 IPv4 数据报"""
        return self.protocol_type == 0x0800
    
    @property
    def is_ipv6(self) -> bool:
        """是否为 IPv6 数据报"""
        return self.protocol_type == 0x86DD
```

### 2.3 解析难点

| 难点 | 说明 |
|------|------|
| **变长包** | 无固定包长，需通过 Start/End 标志和 Total Length 定位 |
| **分片重组** | 大 IP 包被分片，需要缓冲和重组 |
| **CRC-32** | 每个 GSE 包末尾有 CRC-32 校验 |
| **Label 类型** | 0/3/6 字节三种 Label 长度 |
| **跨 BBFrame 边界** | GSE 包可能跨越 BBFrame 边界 |

## 3. MPE 解析器设计

### 3.1 协议规范

**协议出处**: ETSI EN 301 192

**Section 结构**:
- Table ID: 8 bits (0x3E)
- Section Syntax Indicator: 1 bit
- Private Indicator: 1 bit
- Section Length: 12 bits
- MAC Address: 48 bits (6 bytes)
- Payload: IP 数据报
- CRC-32: 32 bits

### 3.2 数据模型

```python
# src/dvb_parser/mpe/models.py

from dataclasses import dataclass


@dataclass
class MPEDatagram:
    """MPE 数据报"""
    table_id: int
    mac_address: bytes  # 6 bytes
    payload: bytes  # IP 数据报
    crc32: int
    
    @property
    def mac_address_str(self) -> str:
        """MAC 地址字符串表示"""
        return ':'.join(f'{b:02x}' for b in self.mac_address)
    
    @property
    def is_broadcast(self) -> bool:
        """是否为广播地址"""
        return self.mac_address[0] & 0x01 == 1
    
    @property
    def is_multicast(self) -> bool:
        """是否为组播地址"""
        return self.mac_address[0] == 0x01 and self.mac_address[1] == 0x00 and self.mac_address[2] == 0x5E
```

### 3.3 解析难点

| 难点 | 说明 |
|------|------|
| **DSM-CC Section** | 基于 section 语法，需要与 PSI/SI 统一处理 |
| **MAC 地址** | 6 字节 MAC 地址过滤 |
| **CRC-32** | section 末尾 CRC-32 校验 |
| **section 拼接** | 长 IP 包可能需要多个 section |

## 4. ULE 解析器设计

### 4.1 协议规范

**协议出处**: RFC 4326

**SNDU 结构**:
- Length/Type: 16 bits（≥1536 为协议类型，<1536 为长度）
- Destination MAC: 48 bits（可选）
- Extension Headers: 可变长（可选）
- Payload: IP 数据报
- CRC-32: 32 bits

### 4.2 数据模型

```python
# src/dvb_parser/ule/models.py

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ULESNDU:
    """ULE SNDU"""
    length_or_type: int
    destination_mac: Optional[bytes]  # 6 bytes
    extension_headers: List[bytes]
    payload: bytes  # IP 数据报
    crc32: int
    
    @property
    def is_type(self) -> bool:
        """是否为协议类型（≥1536）"""
        return self.length_or_type >= 1536
    
    @property
    def length(self) -> int:
        """SNDU 长度（如果 Length/Type < 1536）"""
        return self.length_or_type if not self.is_type else 0
    
    @property
    def protocol_type(self) -> int:
        """协议类型（如果 Length/Type ≥ 1536）"""
        return self.length_or_type if self.is_type else 0
    
    @property
    def is_ipv4(self) -> bool:
        """是否为 IPv4 数据报"""
        return self.is_type and self.protocol_type == 0x0800
    
    @property
    def is_ipv6(self) -> bool:
        """是否为 IPv6 数据报"""
        return self.is_type and self.protocol_type == 0x86DD
```

### 4.3 解析难点

| 难点 | 说明 |
|------|------|
| **CRC-32** | SNDU 末尾的 CRC-32 校验 |
| **扩展头链** | 可变长的扩展头链，需要逐个解析 |
| **Type/Length** | 2 字段共用同一位置，≥1536 为 Type，<1536 为 Length |
| **跨 TS 包** | SNDU 可能跨越多个 TS 包 |

## 5. NIP 解析器设计

### 5.1 协议规范

**协议出处**: ETSI EN 301 192 (DVB Data Broadcasting)

**数据广播方法**:
- Data Piping: 直接数据传输，无封装
- Data Streaming: 同步/异步数据流
- Data Carousel: 循环数据传输（基于 DSM-CC）
- Object Carousel: 对象化数据传输（基于 DSM-CC）

### 5.2 数据模型

```python
# src/dvb_parser/nip/models.py

from dataclasses import dataclass
from typing import Optional


@dataclass
class NIPDataUnit:
    """NIP 数据单元"""
    method: str  # "piping", "streaming", "carousel", "object_carousel"
    payload: bytes
    
@dataclass
class NIPStreaming:
    """NIP 数据流"""
    synchronous: bool
    data_identifier: int
    payload: bytes

@dataclass
class NIPCarousel:
    """NIP 数据循环"""
    download_id: int
    block_size: int
    blocks: list
```

### 5.3 解析难点

| 难点 | 说明 |
|------|------|
| **多种方法** | 4 种数据广播方法，语法不同 |
| **DSM-CC** | Data Carousel 和 Object Carousel 基于 DSM-CC |
| **数据标识** | 需要根据 data_identifier 识别内容类型 |

## 6. EIT 解析器设计

### 6.1 协议规范

**协议出处**: ETSI EN 300 468 §6.2.4

**表结构**:
- Table ID: 0x4E-0x6F（不同含义）
  - 0x4E: 当前 TS，当前/后续事件
  - 0x4F: 其他 TS，当前/后续事件
  - 0x50-0x5F: 当前 TS，时间表
  - 0x60-0x6F: 其他 TS，时间表
- Service ID: 16 bits
- Transport Stream ID: 16 bits
- Original Network ID: 16 bits
- Event Loop:
  - Event ID: 16 bits
  - Start Time: 40 bits (MJD + BCD)
  - Duration: 24 bits (BCD)
  - Running Status: 3 bits
  - Free CA Mode: 1 bit
  - Descriptors: 事件名称、描述等

### 6.2 数据模型

```python
# src/dvb_parser/si/models.py (追加)

@dataclass
class EITEvent:
    """EIT 事件"""
    event_id: int
    start_time: int  # UTC timestamp
    duration: int  # 秒
    running_status: int
    free_ca_mode: bool
    descriptors: List[bytes]
    # 从描述符中解析的字段
    event_name: str = ""
    event_description: str = ""

@dataclass
class EIT:
    """事件信息表"""
    table_id: int
    service_id: int
    transport_stream_id: int
    original_network_id: int
    version_number: int
    current_next_indicator: bool
    section_number: int
    last_section_number: int
    events: List[EITEvent]
```

### 6.3 解析难点

| 难点 | 说明 |
|------|------|
| **多 section 表** | 一个 EIT 可能分布在多个 section 中 |
| **事件循环** | 需要解析多个事件条目 |
| **时间解析** | MJD + BCD 格式的 UTC 时间 |
| **描述符** | 事件名称和描述的多语言支持 |

## 7. TDT 解析器设计

### 7.1 协议规范

**协议出处**: ETSI EN 300 468 §6.2.5

**表结构**:
- Table ID: 0x70 (TDT) / 0x73 (TOT)
- UTC Time: 40 bits (MJD + BCD)
- Descriptors (仅 TOT): 时间偏移信息

### 7.2 数据模型

```python
# src/dvb_parser/si/models.py (追加)

@dataclass
class TDT:
    """时间日期表"""
    table_id: int
    utc_time: int  # UTC timestamp

@dataclass
class TOT:
    """时间偏移表"""
    table_id: int
    utc_time: int  # UTC timestamp
    descriptors: List[bytes]
```

### 7.3 解析难点

| 难点 | 说明 |
|------|------|
| **UTC 时间** | MJD + BCD 格式解析 |
| **时间偏移** | TOT 中的时区偏移描述符 |

## 8. 项目结构更新

```
dvb-parser/
├── src/dvb_parser/
│   ├── gse/                   # 新增
│   │   ├── __init__.py
│   │   ├── parser.py
│   │   └── models.py
│   ├── mpe/                   # 新增
│   │   ├── __init__.py
│   │   ├── parser.py
│   │   └── models.py
│   ├── ule/                   # 新增
│   │   ├── __init__.py
│   │   ├── parser.py
│   │   └── models.py
│   ├── nip/                   # 新增
│   │   ├── __init__.py
│   │   ├── parser.py
│   │   └── models.py
│   └── si/                    # 扩展
│       ├── models.py          # 追加 EIT, TDT, TOT 模型
│       ├── eit.py             # 新增
│       └── tdt.py             # 新增
├── tests/
│   ├── test_gse.py            # 新增
│   ├── test_mpe.py            # 新增
│   ├── test_ule.py            # 新增
│   ├── test_nip.py            # 新增
│   ├── test_eit.py            # 新增
│   └── test_tdt.py            # 新增
└── ...
```

## 9. 测试策略

### 9.1 单元测试

每个解析器独立测试：

```python
# tests/test_gse.py
class TestGSEParser:
    def test_parse_complete_packet(self):
        """测试解析完整 GSE 包（无分片）"""
    
    def test_parse_fragment_start(self):
        """测试解析分片开始"""
    
    def test_parse_fragment_continue(self):
        """测试解析分片中间"""
    
    def test_parse_fragment_end(self):
        """测试解析分片结束"""
    
    def test_crc32_validation(self):
        """测试 CRC-32 校验"""

# tests/test_mpe.py
class TestMPEParser:
    def test_parse_valid_mpe(self):
        """测试解析有效的 MPE section"""
    
    def test_mac_address_parsing(self):
        """测试 MAC 地址解析"""

# tests/test_ule.py
class TestULEParser:
    def test_parse_sndu_with_type(self):
        """测试解析包含协议类型的 SNDU"""
    
    def test_parse_sndu_with_length(self):
        """测试解析包含长度的 SNDU"""
    
    def test_extension_headers(self):
        """测试扩展头解析"""

# tests/test_nip.py
class TestNIPParser:
    def test_parse_data_piping(self):
        """测试解析数据管道"""
    
    def test_parse_data_streaming(self):
        """测试解析数据流"""

# tests/test_eit.py
class TestEITParser:
    def test_parse_present_following(self):
        """测试解析当前/后续事件"""
    
    def test_parse_schedule(self):
        """测试解析时间表事件"""

# tests/test_tdt.py
class TestTDTParser:
    def test_parse_tdt(self):
        """测试解析 TDT"""
    
    def test_parse_tot(self):
        """测试解析 TOT"""
```

### 9.2 集成测试

```python
# tests/test_integration.py (追加)
class TestIntegrationP2:
    def test_gse_with_bbframe(self):
        """测试 GSE 与 BBFrame 关联"""
    
    def test_mpe_with_ts(self):
        """测试 MPE 与 TS 关联"""
    
    def test_eit_with_sdt(self):
        """测试 EIT 与 SDT 关联（事件对应节目）"""
```

## 10. 未来扩展

P2 完成后，可考虑：
- 流式解析支持
- 描述符递归解析库
- 多语言字符编码支持
- ES 帧重组
- 性能优化
