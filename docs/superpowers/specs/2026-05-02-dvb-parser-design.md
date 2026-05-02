# DVB Parser 设计规范

**日期**: 2026-05-02
**状态**: 草稿
**作者**: AI Assistant

## 1. 项目概述

### 1.1 目标

开发一个 Python 库，用于解析 DVB-S2/S2X 卫星信号中的信源封装格式。输入为接收机解调译码后的 BBFrame 二进制文件，输出为结构化的 Python 对象。

### 1.2 范围

- **聚焦层**: BBFrame 及以上层（不关注 FECFrame/PLFrame 物理层）
- **输入格式**: 任何封装格式的二进制数据（BBFrame、TS、GSE 等）
- **输出格式**: 结构化 Python 对象（dataclass）
- **处理模式**: 逐包解析（packet-by-packet）

### 1.3 关键约束

- Python 3.8+ 兼容
- 最小化外部依赖
- 模块化设计，支持未来扩展

## 2. 协议调研

### 2.1 DVB-S2/S2X 协议栈封装格式

#### 2.1.1 BBFrame (Baseband Frame)

**协议出处**: ETSI EN 302 307-1 §5 (DVB-S2), EN 302 307-2 (DVB-S2X)

**定位**: DVB-S2/S2X 基带帧，最外层数据容器

**帧结构**:
- **Header**: 10 bytes
  - MATYPE (2B): 流类型指示（TS/GSE/GCS、SIS/MIS、NPD、ROLL、ISI）
  - UPL (2B): 用户包长度
  - DFL (2B): 数据域长度
  - SYNC (1B): 同步字
  - SYNCD (2B): 到下一个包头的距离
  - CRC-8 (1B): 帧头校验（多项式 0xD5）
- **Data Field**: 可变长，取决于 FEC 率（3072~64800 bits）
- **Padding**: CBGF 指示的填充字节

**输入流模式**:
| MATYPE[1] TS/GS | MATYPE[1] SIS/MIS | 含义 | 载荷内容 |
|------------------|-------------------|------|----------|
| `00` (TS) | `0` (SIS) | 传输流，单输入流 | 连续的 188 字节 TS 包 |
| `00` (TS) | `1` (MIS) | 传输流，多输入流 | 多个 TS 流复用 |
| `01` (GSE) | `0`/`1` | 通用流封装 | GSE 包（变长） |
| `10` (GCS) | `0`/`1` | 通用连续流 | 原始字节流（无分包） |

**典型应用场景**: 所有 DVB-S2/S2X 卫星广播的基础承载格式

#### 2.1.2 MPEG-TS (Transport Stream)

**协议出处**: ISO/IEC 13818-1 / ITU-T H.222.0

**定位**: 固定 188 字节传输流包，数字电视广播的标准承载格式

**包结构**:
- **Header**: 4 bytes
  - Sync Byte (1B): 固定 0x47
  - PID (13 bits): 包标识符
  - Continuity Counter (4 bits): 连续性计数器
  - Adaptation Field Control (2 bits): 适应字段控制
  - Transport Scrambling Control (2 bits): 加扰控制
- **Payload**: 184 bytes（当 AFC=01 时）

**包长度变体**:
- **188 bytes**: 标准 TS 包（无外编码）
- **204 bytes**: TS 包 + 16 bytes Reed-Solomon FEC（外编码）
- **208 bytes**: TS 包 + 20 bytes（某些系统使用）

**PID 分配**:
- 0x0000: PAT (节目关联表)
- 0x0001: CAT (条件接收表)
- 0x0010: NIT (网络信息表)
- 其他: PMT、音视频 ES、MPE/ULE 等

**典型应用场景**: 数字电视广播的标准传输格式

#### 2.1.3 GSE (Generic Stream Encapsulation)

**协议出处**: ETSI EN 102 772

**定位**: 通用流封装，用于 DVB-S2/S2X 原生 IP 数据封装

**包结构**:
- **Header**: 2-12 bytes（取决于标志位）
  - Start/End 标志: 指示分片状态
  - Label: 可选的标签字段
  - Protocol Type: 协议类型（如 0x0800 = IPv4）
- **Payload**: IP 数据报（可能分片）
- **CRC-32**: 包尾校验

**分片机制**:
- Start=1, End=1: 完整包（无分片）
- Start=1, End=0: 分片开始
- Start=0, End=0: 分片中间
- Start=0, End=1: 分片结束

**典型应用场景**: 纯 IP 数据广播

#### 2.1.4 ULE (Unidirectional Lightweight Encapsulation)

**协议出处**: RFC 4326

**定位**: 单向轻量封装，用于 TS 流内承载 IP 数据报

**包结构** (SNDU - Sub-Network Data Unit):
- **Length/Type** (2B): ≥1536 为协议类型，<1536 为长度
- **Destination MAC** (6B, 可选): 目的 MAC 地址
- **Extension Headers**: 可变长扩展头链
- **Payload**: IP 数据报
- **CRC-32**: 包尾校验

**典型应用场景**: TS 流内承载 IP 数据（较新方案）

#### 2.1.5 MPE (Multi-Protocol Encapsulation)

**协议出处**: ETSI EN 301 192

**定位**: 多协议封装，用于 TS 流内承载 IP 数据报

**包结构** (DSM-CC Section):
- **Section Header**: table_id=0x3E
- **MAC Address** (6B): 目的 MAC 地址
- **Payload**: IP 数据报
- **CRC-32**: Section 尾校验

**典型应用场景**: TS 流内承载 IP 数据（传统方案）

#### 2.1.6 SIS/GCS (Stream Input Stream / Generic Continuous Stream)

**协议出处**: ETSI EN 302 307-1 §5.1

**定位**: 连续流输入，无分包

**特点**:
- 无包结构，原始字节流
- 恒比特率
- 用于特定应用场景（如专业视频传输）

**典型应用场景**: 专业视频传输、恒比特率流

#### 2.1.7 PES (Packetized Elementary Stream)

**协议出处**: ISO/IEC 13818-1 §2.4

**定位**: 包化基本流，TS 内承载音视频 ES 数据

**包结构**:
- **PES Header** (3B):
  - Start Code (3B): 0x000001
  - Stream ID (1B): 流类型标识
  - PES Length (2B): 包长度
- **Optional PES Header**:
  - PTS/DTS (5B each): 时间戳
  - Other flags: ESCR, ES rate, etc.
- **PES Payload**: 音视频 ES 数据

**Stream ID 分配**:
- 0xBC: Program Stream Map
- 0xBD: Private Stream 1
- 0xBE: Padding Stream
- 0xBF: Private Stream 2
- 0xC0-0xDF: Audio Stream 0-31
- 0xE0-0xEF: Video Stream 0-15

**典型应用场景**: 音视频基本流传输

#### 2.1.8 PSI (Program Specific Information)

**协议出处**: ISO/IEC 13818-1 §2.4.4

**定位**: 节目特定信息

**表类型**:
| Table | Table ID | 功能 |
|-------|----------|------|
| PAT | 0x00 | 节目关联表，program_number → PMT PID 映射 |
| PMT | 0x02 | 节目映射表，stream_type → ES PID 映射 |
| CAT | 0x01 | 条件接收表 |

**Section 结构**:
- **Table ID** (1B): 表类型标识
- **Section Syntax Indicator** (1 bit): 语法标志
- **Section Length** (12 bits): Section 长度
- **Table ID Extension** (2B): 表扩展标识
- **Version Number** (5 bits): 版本号
- **Section Number** (1B): Section 编号
- **Last Section Number** (1B): 最后 Section 编号
- **CRC-32** (4B): Section 尾校验

#### 2.1.9 SI (Service Information)

**协议出处**: ETSI EN 300 468

**定位**: 业务信息

**表类型**:
| Table | Table ID | 功能 |
|-------|----------|------|
| NIT | 0x40/0x41 | 网络信息表 |
| SDT | 0x42/0x46 | 业务描述表 |
| EIT | 0x4E-0x6F | 事件信息表 |
| TDT | 0x70 | 时间日期表 |
| TOT | 0x73 | 时间偏移表 |

**描述符**: 可变长描述符链，用于携带扩展信息

#### 2.1.10 NIP (Network Independent Protocol)

**协议出处**: ETSI EN 301 192 (DVB Data Broadcasting)

**定位**: DVB 数据广播中的网络无关协议，用于数据管道和数据流传输

**数据广播方法**:
- **Data Piping**: 直接数据传输，无封装
- **Data Streaming**: 同步/异步数据流
- **Data Carousel**: 循环数据传输
- **Object Carousel**: 对象化数据传输（基于 DSM-CC）

**典型应用场景**: 数据广播、软件更新、交互式服务

#### 2.1.11 DSM-CC (Digital Storage Media Command and Control)

**协议出处**: ISO/IEC 13818-6

**定位**: 数字存储媒体命令与控制，用于数据广播和交互服务

**主要功能**:
- **MPE**: 多协议封装（已覆盖）
- **SSU**: 系统软件更新
- **Object Carousel**: 对象化数据传输
- **User-to-Network**: 用户到网络交互

**典型应用场景**: 数据广播、软件更新、交互式服务

### 2.2 封装嵌套关系

#### 2.2.1 DVB 协议族全景嵌套结构

DVB 协议族中，除了 DVB-S2/S2X 的三种模式外，还有其他系统的嵌套结构：

**卫星系统**:
- **DVB-S** (旧标准): 直接使用 MPEG-TS，无 BBFrame 层
- **DVB-S2/S2X + TS**: 最常见的模式（见下文）
- **DVB-S2/S2X + GSE**: 纯 IP 数据广播（见下文）
- **DVB-S2/S2X + GCS**: 连续流（见下文）

**地面广播系统** (DVB-T/T2):
- 直接使用 MPEG-TS（无 BBFrame）
- DVB-T2 可选择使用 BBFrame 或直接 TS

**有线广播系统** (DVB-C/C2):
- 直接使用 MPEG-TS（无 BBFrame）

**其他可能的嵌套**:
- **TS over IP**: MPEG-TS 封装在 UDP/IP 中
- **Multi-Protocol**: 一个 BBFrame 内混合 TS 和 GSE（MIS 模式）
- **Data Piping**: 原始数据管道（无分包）

**总结**: 对于 DVB-S2/S2X，以下三种模式覆盖了绝大多数实际应用场景。其他系统（DVB-S/T/C）不使用 BBFrame，但它们的 TS 层解析逻辑是通用的。

#### 2.2.2 TS 模式嵌套（最常见）

```
BBFrame (MATYPE 指示 TS 模式)
└── MPEG-TS 包 (188 bytes each)
    ├── TS Header (4B)
    └── TS Payload (184B)
        ├── PSI Section
        │   ├── PAT (table_id=0x00)
        │   ├── PMT (table_id=0x02)
        │   └── CAT (table_id=0x01)
        ├── SI Section
        │   ├── NIT (table_id=0x40/0x41)
        │   ├── SDT (table_id=0x42/0x46)
        │   ├── EIT (table_id=0x4E-0x6F)
        │   └── TDT (table_id=0x70)
        ├── PES Packet
        │   ├── PES Header
        │   └── ES Data (Audio/Video)
        ├── MPE Section (table_id=0x3E)
        │   ├── MAC Address
        │   ├── IP Datagram
        │   └── CRC-32
        └── ULE SNDU
            ├── Length/Type
            ├── Extension Headers
            ├── IP Datagram
            └── CRC-32
```

#### 2.2.3 GSE 模式嵌套

```
BBFrame (MATYPE 指示 GSE 模式)
└── GSE Packet (变长)
    ├── GSE Header
    ├── IP Datagram (可能分片)
    └── CRC-32
```

#### 2.2.3 GCS 模式嵌套

```
BBFrame (MATYPE 指示 GCS 模式)
└── Raw Byte Stream (无分包)
```

### 2.3 二进制解析难点

#### 2.3.1 BBFrame 解析难点

| 难点 | 说明 |
|------|------|
| **变长帧** | 帧长取决于 FEC 率（3072~64800 bits），需要从外部参数或帧头推断 |
| **CRC-8 校验** | 帧头使用 CRC-8 (多项式 0xD5)，校验失败需丢弃 |
| **MATYPE 解码** | 2 字节包含 TS/GS、SIS/MIS、NPD、ROLL、ISI 等多个标志位 |
| **填充检测** | CBGF (Concatenation Flag) 指示是否有填充字节 |
| **SYNCD 字段** | 指向下一个 UPL 边界的距离，用于定位包边界 |

#### 2.3.2 MPEG-TS 解析难点

| 难点 | 说明 |
|------|------|
| **同步字检测** | 需要在流中找到 0x47 同步字，处理误同步 |
| **连续性计数器** | CC 字段 (4 bits) 需要逐包验证，检测丢包 |
| **适应字段** | AFC=10/11 时存在，长度可变，包含 PCR/OPCR 等 |
| **PCR 提取** | 42-bit PCR = 33-bit base × 300 + 9-bit extension |
| **负载起始** | AFC 决定 payload 偏移：`00`=无, `01`=纯 payload, `10`=纯适应, `11`=适应+payload |
| **加扰指示** | TS header 的 scrambling_control 字段 (2 bits) |
| **多包拼接** | PES/Section 可能跨多个 TS 包，需要 PID 级别的缓冲 |
| **包长度变体** | 支持 188/204/208 字节包长，需检测外编码是否存在 |

#### 2.3.3 GSE 解析难点

| 难点 | 说明 |
|------|------|
| **变长包** | 无固定包长，需通过 Length 字段或 Start/End 标志定位 |
| **分片重组** | 大 IP 包被分片（Start=1, End=0 开始；Start=0, End=1 结束） |
| **CRC-32** | 每个 GSE 包末尾有 CRC-32 校验 |
| **扩展头** | 可选的 Label、Protocol Type 等扩展字段 |
| **BBFrame 边界** | GSE 包可能跨越 BBFrame 边界（跨帧重组） |

#### 2.3.4 ULE 解析难点

| 难点 | 说明 |
|------|------|
| **CRC-32** | SNDU 末尾的 CRC-32 校验 |
| **扩展头链** | 可变长的扩展头链，需要逐个解析 |
| **Type/Length** | 2 字段共用同一位置，≥1536 为 Type，<1536 为 Length |
| **跨 TS 包** | SNDU 可能跨越多个 TS 包 |

#### 2.3.5 MPE 解析难点

| 难点 | 说明 |
|------|------|
| **DSM-CC Section** | 基于 section 语法，table_id=0x3E |
| **MAC 地址** | 6 字节 MAC 地址过滤 |
| **CRC-32** | section 末尾 CRC-32 校验 |
| **section 拼接** | 长 IP 包可能需要多个 section |

#### 2.3.6 PSI/SI 解析难点

| 难点 | 说明 |
|------|------|
| **section 语法** | 短 section (table_id < 0x40) 和长 section (≥ 0x40) 语法不同 |
| **CRC-32** | 长 section 末尾 CRC-32 校验 |
| **多 section 表** | 一个表可能分布在多个 section 中（如 EIT） |
| **版本控制** | version_number 字段用于检测表更新 |
| **描述符循环** | 可变长描述符链，需要递归解析 |

## 3. 架构设计

### 3.1 整体架构

采用分层解析器链（Layered Parser Chain）架构：

```
用户代码
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  BBFrameParser.parse(data) → BBFrame                    │
│    │                                                    │
│    ▼ (根据 MATYPE 分发)                                  │
│  ┌─ TSPacketParser → list[TSHeader]                     │
│  │    │                                                 │
│  │    ▼ (按 PID 分发)                                    │
│  │  ├─ PESParser → PESPacket                            │
│  │  ├─ SectionParser → Section                          │
│  │  │    ├─ PATParser → PAT                             │
│  │  │    ├─ PMTParser → PMT                             │
│  │  │    ├─ SDTParser → SDT                             │
│  │  │    └─ ...                                         │
│  │  ├─ MPEParser → MPEDatagram                          │
│  │  └─ ULEParser → ULESNDU                              │
│  │                                                      │
│  └─ GSEParser → GSEPacket                               │
└─────────────────────────────────────────────────────────┘
```

### 3.2 独立使用设计

每个 Parser 都是自包含的，不依赖上层或下层 Parser。用户可以：

```python
# 场景 1：直接解析原始 TS 文件（无 BBFrame）
from dvb_parser.ts.parser import TSPacketParser

with open("stream.ts", "rb") as f:
    ts_data = f.read()

ts_packets = TSPacketParser.parse_all(ts_data)  # 直接使用

# 场景 2：直接解析原始 BBFrame（不深入 TS 层）
from dvb_parser.bbframe.parser import BBFrameParser

with open("stream.bb", "rb") as f:
    bb_data = f.read()

bbframe = BBFrameParser.parse(bb_data)  # 只解析 BBFrame 头

# 场景 3：解析 BBFrame 后提取 TS 包，但不解析 PSI/SI
from dvb_parser.bbframe.parser import BBFrameParser
from dvb_parser.ts.parser import TSPacketParser

bbframe = BBFrameParser.parse(bb_data)
ts_packets = TSPacketParser.parse_all(bbframe.data_field)  # 停在 TS 层

# 场景 4：使用 GSE 解析器（未来支持）
from dvb_parser.gse.parser import GSEParser

gse_packets = GSEParser.parse_all(bbframe.data_field)  # 独立使用
```

**设计原则**: 每个 Parser 都是独立的，用户可以选择：
- 只使用 BBFrame Parser
- 只使用 TS Parser（直接输入 TS 数据）
- 组合使用多个 Parser（从 BBFrame 到 PSI/SI）

### 3.3 核心组件

#### 3.3.1 Parser 接口

每个 Parser 实现统一接口：

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ParseResult:
    """解析结果基类"""
    offset: int  # 解析起始偏移
    length: int  # 解析的字节数
    data: bytes  # 原始数据

class BaseParser:
    """Parser 基类"""
    
    @staticmethod
    def parse(data: bytes, offset: int = 0) -> ParseResult:
        """解析数据，返回结构化对象"""
        raise NotImplementedError
```

#### 3.3.2 数据模型

每个协议层定义对应的 dataclass：

```python
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional

class StreamType(IntEnum):
    """BBFrame 输入流类型"""
    TS = 0b00    # 传输流
    GSE = 0b01   # 通用流封装
    GCS = 0b10   # 通用连续流

@dataclass
class BBFrameHeader:
    """BBFrame 帧头"""
    matype: bytes        # 2 bytes
    upl: int             # 用户包长度
    dfl: int             # 数据域长度
    sync: int            # 同步字
    syncd: int           # 到下一个包头的距离
    crc8: int            # CRC-8 校验值
    
    @property
    def stream_type(self) -> StreamType:
        """获取流类型"""
        return StreamType((self.matype[0] >> 6) & 0x03)
    
    @property
    def is_ts_mode(self) -> bool:
        """是否为 TS 模式"""
        return self.stream_type == StreamType.TS
    
    @property
    def is_gse_mode(self) -> bool:
        """是否为 GSE 模式"""
        return self.stream_type == StreamType.GSE

@dataclass
class BBFrame:
    """完整的 BBFrame"""
    header: BBFrameHeader
    data_field: bytes    # 数据域
    padding: bytes       # 填充字节
```

#### 3.3.3 解析器实现

每个解析器独立实现：

```python
import struct
from typing import List

class BBFrameParser:
    """BBFrame 解析器"""
    
    HEADER_SIZE = 10  # BBFrame 头固定 10 字节
    CRC8_POLYNOMIAL = 0xD5
    
    @staticmethod
    def parse(data: bytes, offset: int = 0) -> BBFrame:
        """
        解析 BBFrame
        
        Args:
            data: 原始数据
            offset: 起始偏移
        
        Returns:
            BBFrame 对象
        
        Raises:
            ValueError: CRC-8 校验失败或数据不足
        """
        if len(data) - offset < BBFrameParser.HEADER_SIZE:
            raise ValueError("数据不足")
        
        # 解析帧头
        header_data = data[offset:offset + BBFrameParser.HEADER_SIZE]
        matype = header_data[0:2]
        upl = struct.unpack('>H', header_data[2:4])[0]
        dfl = struct.unpack('>H', header_data[4:6])[0]
        sync = header_data[6]
        syncd = struct.unpack('>H', header_data[7:9])[0]
        crc8 = header_data[9]
        
        # 验证 CRC-8
        if not BBFrameParser._verify_crc8(header_data[:9], crc8):
            raise ValueError("CRC-8 校验失败")
        
        header = BBFrameHeader(
            matype=matype,
            upl=upl,
            dfl=dfl,
            sync=sync,
            syncd=syncd,
            crc8=crc8
        )
        
        # 提取数据域
        data_start = offset + BBFrameParser.HEADER_SIZE
        data_end = data_start + (dfl // 8)  # dfl 是 bit 数
        data_field = data[data_start:data_end]
        
        # 提取填充
        padding = data[data_end:offset + BBFrameParser.HEADER_SIZE + (dfl // 8)]
        
        return BBFrame(
            header=header,
            data_field=data_field,
            padding=padding
        )
    
    @staticmethod
    def _verify_crc8(data: bytes, expected: int) -> bool:
        """验证 CRC-8"""
        crc = 0
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ BBFrameParser.CRC8_POLYNOMIAL
                else:
                    crc <<= 1
                crc &= 0xFF
        return crc == expected

class TSPacketParser:
    """MPEG-TS 包解析器"""
    
    PACKET_SIZE_188 = 188  # 标准 TS 包
    PACKET_SIZE_204 = 204  # 带 16 字节 FEC
    PACKET_SIZE_208 = 208  # 带 20 字节 FEC
    SYNC_BYTE = 0x47
    
    @staticmethod
    def parse(data: bytes, offset: int = 0, packet_size: int = 188) -> 'TSPacket':
        """
        解析单个 TS 包
        
        Args:
            data: 原始数据
            offset: 起始偏移
            packet_size: 包大小（188/204/208）
        """
        if len(data) - offset < packet_size:
            raise ValueError("数据不足")
        
        # 验证同步字
        if data[offset] != TSPacketParser.SYNC_BYTE:
            raise ValueError("同步字错误")
        
        # 解析包头
        header = data[offset:offset + 4]
        
        # 提取字段
        pid = ((header[1] & 0x1F) << 8) | header[2]
        cc = header[3] & 0x0F
        afc = (header[3] >> 4) & 0x03
        scrambling = (header[3] >> 6) & 0x03
        
        # 解析适应字段
        adaptation_field = None
        payload_offset = offset + 4
        
        if afc in (0b10, 0b11):  # 有适应字段
            adaptation_length = data[payload_offset]
            adaptation_field = data[payload_offset:payload_offset + 1 + adaptation_length]
            payload_offset += 1 + adaptation_length
        
        # 提取负载（188 字节包内的 payload）
        payload = data[payload_offset:offset + TSPacketParser.PACKET_SIZE_188]
        
        # 提取外编码（如果存在）
        fec = None
        if packet_size > TSPacketParser.PACKET_SIZE_188:
            fec = data[offset + TSPacketParser.PACKET_SIZE_188:offset + packet_size]
        
        return TSPacket(
            pid=pid,
            cc=cc,
            afc=afc,
            scrambling=scrambling,
            adaptation_field=adaptation_field,
            payload=payload,
            fec=fec
        )
    
    @staticmethod
    def detect_packet_size(data: bytes, offset: int = 0) -> int:
        """
        检测 TS 包大小
        
        通过检查同步字的位置来判断包大小
        """
        if len(data) - offset < 208:
            return TSPacketParser.PACKET_SIZE_188
        
        # 检查 188 字节后的同步字
        if data[offset + 188] == TSPacketParser.SYNC_BYTE:
            return TSPacketParser.PACKET_SIZE_188
        
        # 检查 204 字节后的同步字
        if data[offset + 204] == TSPacketParser.SYNC_BYTE:
            return TSPacketParser.PACKET_SIZE_204
        
        # 检查 208 字节后的同步字
        if data[offset + 208] == TSPacketParser.SYNC_BYTE:
            return TSPacketParser.PACKET_SIZE_208
        
        return TSPacketParser.PACKET_SIZE_188
    
    @staticmethod
    def parse_all(data: bytes, packet_size: int = 0) -> List['TSPacket']:
        """
        解析多个 TS 包
        
        Args:
            data: 原始数据
            packet_size: 包大小（0=自动检测）
        """
        if packet_size == 0:
            packet_size = TSPacketParser.detect_packet_size(data)
        
        packets = []
        offset = 0
        while offset + packet_size <= len(data):
            try:
                packet = TSPacketParser.parse(data, offset, packet_size)
                packets.append(packet)
            except ValueError:
                # 跳过无效包
                pass
            offset += packet_size
        return packets

@dataclass
class TSPacket:
    """TS 包"""
    pid: int
    cc: int
    afc: int
    scrambling: int
    adaptation_field: Optional[bytes]
    payload: bytes
    fec: Optional[bytes] = None  # 外编码（16/20 字节）
```

### 3.4 分发机制

上层解析器根据下层数据分发到对应的子解析器：

```python
class DVBS2Parser:
    """DVB-S2/S2X 解析器（组合模式）"""
    
    def __init__(self):
        self.bbframe_parser = BBFrameParser()
        self.ts_parser = TSPacketParser()
        self.pat_parser = PATParser()
        self.pmt_parser = PMTParser()
        # ... 其他解析器
    
    def parse_bbframe(self, data: bytes) -> BBFrame:
        """解析 BBFrame"""
        return self.bbframe_parser.parse(data)
    
    def parse_ts_packets(self, bbframe: BBFrame) -> List[TSPacket]:
        """从 BBFrame 提取 TS 包"""
        if not bbframe.header.is_ts_mode:
            raise ValueError("不是 TS 模式")
        return self.ts_parser.parse_all(bbframe.data_field)
    
    def parse_pat(self, ts_packets: List[TSPacket]) -> PAT:
        """解析 PAT 表"""
        pat_packets = [p for p in ts_packets if p.pid == 0x0000]
        return self.pat_parser.parse(pat_packets)
```

## 4. MVP 范围

### 4.1 优先级划分

| 优先级 | 模块 | 功能 | 依赖关系 |
|--------|------|------|----------|
| **P0** | BBFrame Parser | 解析帧头（MATYPE、UPL、DFL、CRC-8），提取数据域 | 无 |
| **P0** | MPEG-TS Parser | 解析 188B 包头（PID、CC、AFC、适应字段） | BBFrame |
| **P0** | PAT Parser | 解析节目关联表 | TS Parser |
| **P0** | PMT Parser | 解析节目映射表 | TS Parser, PAT |
| **P1** | SDT Parser | 解析业务描述表 | TS Parser |
| **P1** | NIT Parser | 解析网络信息表 | TS Parser |
| **P1** | PES Parser | 解析 PES 包头（stream_id、PTS/DTS） | TS Parser |
| **P2** | GSE Parser | 解析 GSE 包 | BBFrame |
| **P2** | MPE Parser | 解析 MPE Section | TS Parser |
| **P2** | ULE Parser | 解析 ULE SNDU | TS Parser |
| **P2** | EIT Parser | 解析事件信息表 | TS Parser |
| **P2** | TDT Parser | 解析时间日期表 | TS Parser |
| **P2** | NIP Parser | 解析 NIP 数据广播 | TS Parser |

### 4.2 MVP 典型使用场景

```python
from dvb_parser import BBFrameParser, TSPacketParser, PATParser, PMTParser

# 解析单个 BBFrame
with open("stream.bb", "rb") as f:
    data = f.read()

bb = BBFrameParser.parse(data)
print(f"流类型: {bb.header.stream_type}")
print(f"数据域长度: {bb.header.dfl} bits")

# 提取 TS 包
ts_packets = TSPacketParser.parse_all(bb.data_field)
print(f"TS 包数量: {len(ts_packets)}")

# 解析 PAT
pat = PATParser.parse(ts_packets)
print(f"节目列表: {pat.programs}")

# 解析 PMT（假设节目号 1 对应 PMT PID 0x100）
pmt = PMTParser.parse(ts_packets, pid=0x100)
for stream in pmt.streams:
    print(f"流类型: {stream.stream_type}, PID: {stream.pid}")
```

### 4.3 依赖策略

| 用途 | 依赖 | 说明 |
|------|------|------|
| 数据类 | `dataclasses` (stdlib, 3.7+) | 结构化对象 |
| 二进制解析 | `struct` (stdlib) | 定长字段解析 |
| CRC 校验 | 自实现 | CRC-8 (BBFrame) 和 CRC-32 (PSI/SI) |
| 测试 | `pytest` | 测试框架 |
| 类型检查 | `typing` (stdlib) | 类型注解 |

## 5. 项目结构

```
dvb-parser/
├── src/
│   └── dvb_parser/
│       ├── __init__.py
│       ├── bbframe/
│       │   ├── __init__.py
│       │   ├── parser.py
│       │   └── models.py
│       ├── ts/
│       │   ├── __init__.py
│       │   ├── parser.py
│       │   └── models.py
│       ├── psi/
│       │   ├── __init__.py
│       │   ├── pat.py
│       │   ├── pmt.py
│       │   └── models.py
│       ├── si/
│       │   ├── __init__.py
│       │   ├── sdt.py
│       │   ├── nit.py
│       │   └── models.py
│       ├── pes/
│       │   ├── __init__.py
│       │   ├── parser.py
│       │   └── models.py
│       ├── gse/
│       │   ├── __init__.py
│       │   ├── parser.py
│       │   └── models.py
│       ├── mpe/
│       │   ├── __init__.py
│       │   ├── parser.py
│       │   └── models.py
│       ├── ule/
│       │   ├── __init__.py
│       │   ├── parser.py
│       │   └── models.py
│       ├── nip/
│       │   ├── __init__.py
│       │   ├── parser.py
│       │   └── models.py
│       └── utils/
│           ├── __init__.py
│           └── crc.py
├── tests/
│   ├── test_bbframe.py
│   ├── test_ts.py
│   ├── test_psi.py
│   └── ...
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-05-02-dvb-parser-design.md
├── pyproject.toml
├── README.md
└── LICENSE
```

## 6. 测试策略

### 6.1 单元测试

每个解析器独立测试：

```python
import pytest
from dvb_parser.bbframe.parser import BBFrameParser

class TestBBFrameParser:
    def test_parse_valid_bbframe(self):
        """测试解析有效的 BBFrame"""
        # 准备测试数据
        data = bytes([
            0b00000000, 0b00000000,  # MATYPE (TS mode)
            0x00, 0xBC,              # UPL (188 bytes)
            0x06, 0x18,              # DFL (1560 bits)
            0x00,                    # SYNC
            0x00, 0x00,              # SYNCD
            0x00                     # CRC-8 (placeholder)
        ])
        
        # 计算正确的 CRC-8
        data = data[:9] + [BBFrameParser._calculate_crc8(data[:9])]
        
        # 解析
        bbframe = BBFrameParser.parse(bytes(data))
        
        # 验证
        assert bbframe.header.is_ts_mode
        assert bbframe.header.upl == 188
        assert bbframe.header.dfl == 1560
    
    def test_parse_invalid_crc(self):
        """测试 CRC-8 校验失败"""
        data = bytes([0x00] * 10)
        with pytest.raises(ValueError, match="CRC-8 校验失败"):
            BBFrameParser.parse(data)
```

### 6.2 集成测试

测试完整的解析链：

```python
class TestDVBS2Parser:
    def test_parse_bbframe_to_pat(self):
        """测试从 BBFrame 到 PAT 的完整解析链"""
        # 准备包含 PAT 的测试数据
        data = self._create_test_bbframe_with_pat()
        
        # 解析
        parser = DVBS2Parser()
        bbframe = parser.parse_bbframe(data)
        ts_packets = parser.parse_ts_packets(bbframe)
        pat = parser.parse_pat(ts_packets)
        
        # 验证
        assert 0x0001 in pat.programs  # 节目号 1
        assert pat.programs[0x0001].pmt_pid == 0x100
```

## 7. 未来扩展

### 7.1 可扩展点

1. **新增协议支持**: 添加 GSE、MPE、ULE 解析器
2. **流式处理**: 基于现有解析器构建流式 Demux
3. **描述符解析**: PSI/SI 描述符的递归解析
4. **错误恢复**: 同步字丢失后的恢复机制
5. **性能优化**: 批量解析、内存映射

### 7.2 向后兼容

- 所有解析器返回 dataclass，便于扩展新字段
- 使用 `__future__` annotations 支持类型注解
- 保持 API 稳定，新增功能通过新方法/类实现

## 8. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| BBFrame 变长帧 | 解析复杂 | 从 MATYPE 或外部参数获取 FEC 率 |
| TS 包误同步 | 数据损坏 | 多字节验证 + 连续性计数器检查 |
| 跨包重组 | 内存消耗 | 限制缓冲区大小，支持流式处理 |
| 协议版本差异 | 兼容性 | 版本检测 + 条件分支 |
| 性能瓶颈 | 解析速度 | 批量解析 + 内存映射 |
