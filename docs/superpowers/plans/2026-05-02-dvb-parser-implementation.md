# DVB Parser 实施计划

> **致自动化代理：** 必须使用子代理驱动开发（推荐）或执行计划子技能来逐任务实施本计划。步骤使用复选框（`- [ ]`）语法进行跟踪。

**目标：** 构建一个 Python 库，用于解析 DVB-S2/S2X 卫星信号中的信源封装格式

**架构：** 采用分层解析器链架构，每个协议层有独立的 Parser 类，返回结构化 dataclass 对象。Parser 之间通过组合模式协作，但每个 Parser 也可独立使用。

**技术栈：** Python 3.8+, dataclasses, struct, pytest

---

## 文件结构

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
│   ├── __init__.py
│   ├── test_bbframe.py
│   ├── test_ts.py
│   ├── test_psi.py
│   ├── test_si.py
│   ├── test_pes.py
│   ├── test_gse.py
│   ├── test_mpe.py
│   ├── test_ule.py
│   └── test_nip.py
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## 任务 1：项目初始化

**文件：**
- 创建：`pyproject.toml`
- 创建：`src/dvb_parser/__init__.py`
- 创建：`tests/__init__.py`
- 创建：`README.md`
- 创建：`LICENSE`

- [ ] **步骤 1：创建 pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "dvb-parser"
version = "0.1.0"
description = "DVB protocol parser for satellite signal analysis"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.8"
authors = [
    {name = "Your Name", email = "your.email@example.com"},
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Communications",
    "Topic :: Multimedia :: Video",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

- [ ] **步骤 2：创建 src/dvb_parser/__init__.py**

```python
"""
DVB Parser - DVB protocol parser for satellite signal analysis
"""

__version__ = "0.1.0"

from dvb_parser.bbframe.parser import BBFrameParser
from dvb_parser.bbframe.models import BBFrame, BBFrameHeader
from dvb_parser.ts.parser import TSPacketParser
from dvb_parser.ts.models import TSPacket

__all__ = [
    "BBFrameParser",
    "BBFrame",
    "BBFrameHeader",
    "TSPacketParser",
    "TSPacket",
]
```

- [ ] **步骤 3：创建 tests/__init__.py**

```python
"""Test package for dvb_parser"""
```

- [ ] **步骤 4：创建 README.md**

```markdown
# DVB Parser

A Python library for parsing DVB (Digital Video Broadcasting) protocol formats, focusing on DVB-S2/S2X satellite signal analysis.

## Features

- BBFrame parsing (Baseband Frame)
- MPEG-TS parsing (188/204/208 byte packets)
- PSI/SI table parsing (PAT, PMT, SDT, NIT, etc.)
- PES packet parsing
- GSE, MPE, ULE, NIP parsing (planned)

## Installation

```bash
pip install -e .
```

## Usage

```python
from dvb_parser import BBFrameParser, TSPacketParser

# Parse BBFrame
bbframe = BBFrameParser.parse(data)

# Extract TS packets
ts_packets = TSPacketParser.parse_all(bbframe.data_field)
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
```

- [ ] **步骤 5：创建 LICENSE**

```text
MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **步骤 6：初始化 git 并提交**

```bash
git add .
git commit -m "feat: initialize project structure"
```

---

## 任务 2：工具模块 - CRC 校验

**文件：**
- 创建：`src/dvb_parser/utils/__init__.py`
- 创建：`src/dvb_parser/utils/crc.py`
- 创建：`tests/test_utils.py`

- [ ] **步骤 1：创建 utils/__init__.py**

```python
"""Utility modules for DVB parser"""
```

- [ ] **步骤 2：编写 CRC 测试**

```python
# tests/test_utils.py
import pytest
from dvb_parser.utils.crc import crc8, crc32

class TestCRC8:
    def test_crc8_basic(self):
        """测试 CRC-8 基本计算"""
        data = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        result = crc8(data)
        assert isinstance(result, int)
        assert 0 <= result <= 255
    
    def test_crc8_known_value(self):
        """测试 CRC-8 已知值"""
        # BBFrame header with known CRC
        data = bytes([0x00, 0x00, 0x00, 0xBC, 0x06, 0x18, 0x00, 0x00, 0x00])
        result = crc8(data)
        assert result == 0xD5  # Expected CRC for this data

class TestCRC32:
    def test_crc32_basic(self):
        """测试 CRC-32 基本计算"""
        data = b"123456789"
        result = crc32(data)
        assert isinstance(result, int)
        assert 0 <= result <= 0xFFFFFFFF
    
    def test_crc32_known_value(self):
        """测试 CRC-32 已知值"""
        # CRC-32 for "123456789" should be 0xCBF43926
        data = b"123456789"
        result = crc32(data)
        assert result == 0xCBF43926
```

- [ ] **步骤 3：运行测试验证失败**

```bash
pytest tests/test_utils.py -v
```

预期：FAIL - 模块不存在

- [ ] **步骤 4：实现 CRC 模块**

```python
# src/dvb_parser/utils/crc.py
"""
CRC checksum implementations for DVB protocols
"""

def crc8(data: bytes, polynomial: int = 0xD5) -> int:
    """
    Calculate CRC-8 checksum
    
    Args:
        data: Input data
        polynomial: CRC polynomial (default: 0xD5 for BBFrame)
    
    Returns:
        CRC-8 value
    """
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ polynomial
            else:
                crc <<= 1
            crc &= 0xFF
    return crc

def crc32(data: bytes) -> int:
    """
    Calculate CRC-32 checksum (CRC-32/MPEG-2)
    
    Args:
        data: Input data
    
    Returns:
        CRC-32 value
    """
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte << 24
        for _ in range(8):
            if crc & 0x80000000:
                crc = (crc << 1) ^ 0x04C11DB7
            else:
                crc <<= 1
            crc &= 0xFFFFFFFF
    return crc ^ 0xFFFFFFFF
```

- [ ] **步骤 5：运行测试验证通过**

```bash
pytest tests/test_utils.py -v
```

预期：PASS

- [ ] **步骤 6：提交**

```bash
git add src/dvb_parser/utils/ tests/test_utils.py
git commit -m "feat: add CRC-8 and CRC-32 utility functions"
```

---

## 任务 3：BBFrame 数据模型

**文件：**
- 创建：`src/dvb_parser/bbframe/__init__.py`
- 创建：`src/dvb_parser/bbframe/models.py`

- [ ] **步骤 1：创建 bbframe/__init__.py**

```python
"""BBFrame parser module"""
```

- [ ] **步骤 2：实现 BBFrame 数据模型**

```python
# src/dvb_parser/bbframe/models.py
"""
BBFrame data models
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class StreamType(IntEnum):
    """BBFrame input stream type"""
    TS = 0b00      # Transport Stream
    GSE = 0b01     # Generic Stream Encapsulation
    GCS = 0b10     # Generic Continuous Stream
    RESERVED = 0b11


class ScramblingMode(IntEnum):
    """BBFrame scrambling mode"""
    NO_SCRAMBLING = 0b00
    ENERGY_DISPERAL = 0b01
    RESERVED_1 = 0b10
    RESERVED_2 = 0b11


@dataclass
class BBFrameHeader:
    """BBFrame header (10 bytes)"""
    matype: bytes        # 2 bytes: stream type, scrambling mode, etc.
    upl: int             # 2 bytes: User Packet Length
    dfl: int             # 2 bytes: Data Field Length (in bits)
    sync: int            # 1 byte: Sync byte
    syncd: int           # 2 bytes: Distance to next packet header
    crc8: int            # 1 byte: CRC-8 checksum
    
    @property
    def stream_type(self) -> StreamType:
        """Get stream type from MATYPE"""
        return StreamType((self.matype[0] >> 6) & 0x03)
    
    @property
    def is_ts_mode(self) -> bool:
        """Check if stream is TS mode"""
        return self.stream_type == StreamType.TS
    
    @property
    def is_gse_mode(self) -> bool:
        """Check if stream is GSE mode"""
        return self.stream_type == StreamType.GSE
    
    @property
    def is_gcs_mode(self) -> bool:
        """Check if stream is GCS mode"""
        return self.stream_type == StreamType.GCS
    
    @property
    def scrambling_mode(self) -> ScramblingMode:
        """Get scrambling mode from MATYPE"""
        return ScramblingMode((self.matype[0] >> 4) & 0x03)
    
    @property
    def isi(self) -> int:
        """Get Input Stream Identifier"""
        return self.matype[1] if len(self.matype) > 1 else 0
    
    @property
    def npd(self) -> bool:
        """Check if Null Packet Deletion is enabled"""
        return bool(self.matype[0] & 0x01)
    
    @property
    def roll_off(self) -> int:
        """Get roll-off factor"""
        return (self.matype[0] >> 2) & 0x03


@dataclass
class BBFrame:
    """Complete BBFrame"""
    header: BBFrameHeader
    data_field: bytes    # Data field content
    padding: bytes       # Padding bytes (if any)
    
    @property
    def data_field_length_bytes(self) -> int:
        """Get data field length in bytes"""
        return self.header.dfl // 8
```

- [ ] **步骤 3：提交**

```bash
git add src/dvb_parser/bbframe/
git commit -m "feat: add BBFrame data models"
```

---

## 任务 4：BBFrame 解析器

**文件：**
- 创建：`src/dvb_parser/bbframe/parser.py`
- 创建：`tests/test_bbframe.py`

- [ ] **步骤 1：编写 BBFrame 解析器测试**

```python
# tests/test_bbframe.py
import pytest
from dvb_parser.bbframe.parser import BBFrameParser
from dvb_parser.bbframe.models import StreamType

class TestBBFrameParser:
    def test_parse_valid_bbframe(self):
        """测试解析有效的 BBFrame"""
        # 构造测试数据
        # MATYPE: TS mode (00), no scrambling (00)
        # UPL: 188 bytes (0x00BC)
        # DFL: 1560 bits (0x0618)
        # SYNC: 0x00
        # SYNCD: 0x0000
        # CRC-8: placeholder
        header_data = bytes([
            0b00000000, 0b00000000,  # MATYPE (TS mode)
            0x00, 0xBC,              # UPL (188 bytes)
            0x06, 0x18,              # DFL (1560 bits)
            0x00,                    # SYNC
            0x00, 0x00,              # SYNCD
            0x00                     # CRC-8 (placeholder)
        ])
        
        # 计算正确的 CRC-8
        from dvb_parser.utils.crc import crc8
        crc_value = crc8(header_data[:9])
        header_data = header_data[:9] + bytes([crc_value])
        
        # 添加数据域（1560 bits = 195 bytes）
        data_field = bytes([0x00] * 195)
        
        # 完整 BBFrame
        bbframe_data = header_data + data_field
        
        # 解析
        bbframe = BBFrameParser.parse(bbframe_data)
        
        # 验证
        assert bbframe.header.is_ts_mode
        assert bbframe.header.upl == 188
        assert bbframe.header.dfl == 1560
        assert len(bbframe.data_field) == 195
    
    def test_parse_invalid_crc(self):
        """测试 CRC-8 校验失败"""
        # 错误的 CRC-8
        header_data = bytes([
            0b00000000, 0b00000000,  # MATYPE
            0x00, 0xBC,              # UPL
            0x06, 0x18,              # DFL
            0x00,                    # SYNC
            0x00, 0x00,              # SYNCD
            0xFF                     # 错误的 CRC-8
        ])
        data_field = bytes([0x00] * 195)
        bbframe_data = header_data + data_field
        
        with pytest.raises(ValueError, match="CRC-8 校验失败"):
            BBFrameParser.parse(bbframe_data)
    
    def test_parse_insufficient_data(self):
        """测试数据不足"""
        data = bytes([0x00] * 5)  # 不足 10 字节
        
        with pytest.raises(ValueError, match="数据不足"):
            BBFrameParser.parse(data)
    
    def test_parse_gse_mode(self):
        """测试 GSE 模式"""
        # MATYPE: GSE mode (01)
        header_data = bytes([
            0b01000000, 0b00000000,  # MATYPE (GSE mode)
            0x00, 0xBC,              # UPL
            0x06, 0x18,              # DFL
            0x00,                    # SYNC
            0x00, 0x00,              # SYNCD
            0x00                     # CRC-8 (placeholder)
        ])
        
        from dvb_parser.utils.crc import crc8
        crc_value = crc8(header_data[:9])
        header_data = header_data[:9] + bytes([crc_value])
        
        data_field = bytes([0x00] * 195)
        bbframe_data = header_data + data_field
        
        bbframe = BBFrameParser.parse(bbframe_data)
        
        assert bbframe.header.is_gse_mode
        assert not bbframe.header.is_ts_mode
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/test_bbframe.py -v
```

预期：FAIL - 模块不存在

- [ ] **步骤 3：实现 BBFrame 解析器**

```python
# src/dvb_parser/bbframe/parser.py
"""
BBFrame parser
"""

import struct
from typing import Optional

from dvb_parser.bbframe.models import BBFrame, BBFrameHeader
from dvb_parser.utils.crc import crc8


class BBFrameParser:
    """BBFrame parser"""
    
    HEADER_SIZE = 10  # BBFrame header is fixed 10 bytes
    
    @staticmethod
    def parse(data: bytes, offset: int = 0) -> BBFrame:
        """
        Parse BBFrame
        
        Args:
            data: Raw data
            offset: Start offset
        
        Returns:
            BBFrame object
        
        Raises:
            ValueError: CRC-8 checksum failure or insufficient data
        """
        if len(data) - offset < BBFrameParser.HEADER_SIZE:
            raise ValueError("数据不足")
        
        # Parse header
        header_data = data[offset:offset + BBFrameParser.HEADER_SIZE]
        matype = header_data[0:2]
        upl = struct.unpack('>H', header_data[2:4])[0]
        dfl = struct.unpack('>H', header_data[4:6])[0]
        sync = header_data[6]
        syncd = struct.unpack('>H', header_data[7:9])[0]
        crc8_value = header_data[9]
        
        # Verify CRC-8
        if crc8(header_data[:9]) != crc8_value:
            raise ValueError("CRC-8 校验失败")
        
        header = BBFrameHeader(
            matype=matype,
            upl=upl,
            dfl=dfl,
            sync=sync,
            syncd=syncd,
            crc8=crc8_value
        )
        
        # Extract data field
        data_start = offset + BBFrameParser.HEADER_SIZE
        data_end = data_start + (dfl // 8)  # dfl is in bits
        data_field = data[data_start:data_end]
        
        # Extract padding (if any)
        padding = data[data_end:]
        
        return BBFrame(
            header=header,
            data_field=data_field,
            padding=padding
        )
    
    @staticmethod
    def parse_multiple(data: bytes) -> list:
        """
        Parse multiple BBFrames from data
        
        Args:
            data: Raw data containing multiple BBFrames
        
        Returns:
            List of BBFrame objects
        """
        frames = []
        offset = 0
        
        while offset < len(data):
            try:
                frame = BBFrameParser.parse(data, offset)
                frames.append(frame)
                offset += BBFrameParser.HEADER_SIZE + (frame.header.dfl // 8)
            except ValueError:
                # Skip invalid frames
                offset += 1
        
        return frames
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/test_bbframe.py -v
```

预期：PASS

- [ ] **步骤 5：提交**

```bash
git add src/dvb_parser/bbframe/parser.py tests/test_bbframe.py
git commit -m "feat: add BBFrame parser with CRC-8 validation"
```

---

## 任务 5：MPEG-TS 数据模型

**文件：**
- 创建：`src/dvb_parser/ts/__init__.py`
- 创建：`src/dvb_parser/ts/models.py`

- [ ] **步骤 1：创建 ts/__init__.py**

```python
"""MPEG-TS parser module"""
```

- [ ] **步骤 2：实现 TS 数据模型**

```python
# src/dvb_parser/ts/models.py
"""
MPEG-TS data models
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class AdaptationFieldControl(IntEnum):
    """Adaptation Field Control values"""
    RESERVED = 0b00
    PAYLOAD_ONLY = 0b01
    ADAPTATION_ONLY = 0b10
    ADAPTATION_AND_PAYLOAD = 0b11


class ScramblingControl(IntEnum):
    """Transport Scrambling Control values"""
    NOT_SCRAMBLED = 0b00
    RESERVED = 0b01
    EVEN_KEY = 0b10
    ODD_KEY = 0b11


@dataclass
class AdaptationField:
    """TS adaptation field"""
    length: int
    discontinuity_indicator: bool
    random_access_indicator: bool
    elementary_stream_priority_indicator: bool
    pcr_flag: bool
    opcr_flag: bool
    splicing_point_flag: bool
    transport_private_data_flag: bool
    adaptation_field_extension_flag: bool
    pcr: Optional[int] = None  # 42-bit PCR
    opcr: Optional[int] = None  # 42-bit OPCR
    splice_countdown: Optional[int] = None
    private_data: Optional[bytes] = None


@dataclass
class TSPacket:
    """TS packet (188/204/208 bytes)"""
    pid: int
    cc: int
    afc: int
    scrambling: int
    adaptation_field: Optional[AdaptationField]
    payload: bytes
    fec: Optional[bytes] = None  # Outer coding (16/20 bytes)
    
    @property
    def is_payload_only(self) -> bool:
        """Check if AFC is payload only"""
        return self.afc == AdaptationFieldControl.PAYLOAD_ONLY
    
    @property
    def is_adaptation_only(self) -> bool:
        """Check if AFC is adaptation only"""
        return self.afc == AdaptationFieldControl.ADAPTATION_ONLY
    
    @property
    def has_adaptation_field(self) -> bool:
        """Check if adaptation field exists"""
        return self.afc in (
            AdaptationFieldControl.ADAPTATION_ONLY,
            AdaptationFieldControl.ADAPTATION_AND_PAYLOAD
        )
    
    @property
    def has_payload(self) -> bool:
        """Check if payload exists"""
        return self.afc in (
            AdaptationFieldControl.PAYLOAD_ONLY,
            AdaptationFieldControl.ADAPTATION_AND_PAYLOAD
        )
    
    @property
    def is_scrambled(self) -> bool:
        """Check if packet is scrambled"""
        return self.scrambling != ScramblingControl.NOT_SCRAMBLED
    
    @property
    def is_null_packet(self) -> bool:
        """Check if this is a null packet (PID 0x1FFF)"""
        return self.pid == 0x1FFF
```

- [ ] **步骤 3：提交**

```bash
git add src/dvb_parser/ts/
git commit -m "feat: add MPEG-TS data models"
```

---

## 任务 6：MPEG-TS 解析器

**文件：**
- 创建：`src/dvb_parser/ts/parser.py`
- 创建：`tests/test_ts.py`

- [ ] **步骤 1：编写 TS 解析器测试**

```python
# tests/test_ts.py
import pytest
from dvb_parser.ts.parser import TSPacketParser
from dvb_parser.ts.models import AdaptationFieldControl, ScramblingControl

class TestTSPacketParser:
    def test_parse_valid_ts_packet(self):
        """测试解析有效的 TS 包"""
        # 构造 188 字节 TS 包
        # Header: sync=0x47, PID=0x100, CC=0, AFC=01 (payload only)
        header = bytes([
            0x47,                    # Sync byte
            0b00000001, 0x00,        # PID=0x100
            0b00010000               # AFC=01, CC=0
        ])
        payload = bytes([0x00] * 184)  # 184 bytes payload
        ts_data = header + payload
        
        packet = TSPacketParser.parse(ts_data)
        
        assert packet.pid == 0x100
        assert packet.cc == 0
        assert packet.afc == AdaptationFieldControl.PAYLOAD_ONLY
        assert packet.scrambling == ScramblingControl.NOT_SCRAMBLED
        assert len(packet.payload) == 184
        assert packet.fec is None
    
    def test_parse_204_byte_packet(self):
        """测试解析 204 字节 TS 包（带 FEC）"""
        header = bytes([
            0x47,                    # Sync byte
            0b00000001, 0x00,        # PID=0x100
            0b00010000               # AFC=01, CC=0
        ])
        payload = bytes([0x00] * 184)
        fec = bytes([0x00] * 16)  # 16 bytes FEC
        ts_data = header + payload + fec
        
        packet = TSPacketParser.parse(ts_data, packet_size=204)
        
        assert packet.pid == 0x100
        assert len(packet.payload) == 184
        assert packet.fec is not None
        assert len(packet.fec) == 16
    
    def test_parse_invalid_sync(self):
        """测试同步字错误"""
        header = bytes([
            0x00,                    # 错误的同步字
            0b00000001, 0x00,
            0b00010000
        ])
        payload = bytes([0x00] * 184)
        ts_data = header + payload
        
        with pytest.raises(ValueError, match="同步字错误"):
            TSPacketParser.parse(ts_data)
    
    def test_detect_packet_size(self):
        """测试自动检测包大小"""
        # 构造两个连续的 188 字节包
        header = bytes([
            0x47,                    # Sync byte
            0b00000001, 0x00,        # PID=0x100
            0b00010000               # AFC=01, CC=0
        ])
        payload = bytes([0x00] * 184)
        ts_data = header + payload + header + payload
        
        detected_size = TSPacketParser.detect_packet_size(ts_data)
        assert detected_size == 188
    
    def test_parse_multiple_packets(self):
        """测试解析多个 TS 包"""
        # 构造两个 TS 包
        header = bytes([
            0x47,                    # Sync byte
            0b00000001, 0x00,        # PID=0x100
            0b00010000               # AFC=01, CC=0
        ])
        payload = bytes([0x00] * 184)
        ts_data = header + payload + header + payload
        
        packets = TSPacketParser.parse_all(ts_data)
        
        assert len(packets) == 2
        assert packets[0].pid == 0x100
        assert packets[1].pid == 0x100
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/test_ts.py -v
```

预期：FAIL - 模块不存在

- [ ] **步骤 3：实现 TS 解析器**

```python
# src/dvb_parser/ts/parser.py
"""
MPEG-TS parser
"""

import struct
from typing import List, Optional

from dvb_parser.ts.models import (
    TSPacket,
    AdaptationField,
    AdaptationFieldControl,
    ScramblingControl,
)


class TSPacketParser:
    """MPEG-TS packet parser"""
    
    PACKET_SIZE_188 = 188
    PACKET_SIZE_204 = 204
    PACKET_SIZE_208 = 208
    SYNC_BYTE = 0x47
    
    @staticmethod
    def parse(data: bytes, offset: int = 0, packet_size: int = 188) -> TSPacket:
        """
        Parse a single TS packet
        
        Args:
            data: Raw data
            offset: Start offset
            packet_size: Packet size (188/204/208)
        
        Returns:
            TSPacket object
        
        Raises:
            ValueError: Sync byte error or insufficient data
        """
        if len(data) - offset < packet_size:
            raise ValueError("数据不足")
        
        # Verify sync byte
        if data[offset] != TSPacketParser.SYNC_BYTE:
            raise ValueError("同步字错误")
        
        # Parse header
        header = data[offset:offset + 4]
        
        # Extract fields
        pid = ((header[1] & 0x1F) << 8) | header[2]
        cc = header[3] & 0x0F
        afc = (header[3] >> 4) & 0x03
        scrambling = (header[3] >> 6) & 0x03
        
        # Parse adaptation field
        adaptation_field = None
        payload_offset = offset + 4
        
        if afc in (AdaptationFieldControl.ADAPTATION_ONLY, 
                   AdaptationFieldControl.ADAPTATION_AND_PAYLOAD):
            adaptation_field, payload_offset = TSPacketParser._parse_adaptation_field(
                data, payload_offset
            )
        
        # Extract payload
        payload = b''
        if afc in (AdaptationFieldControl.PAYLOAD_ONLY,
                   AdaptationFieldControl.ADAPTATION_AND_PAYLOAD):
            payload = data[payload_offset:offset + TSPacketParser.PACKET_SIZE_188]
        
        # Extract FEC (if present)
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
    def _parse_adaptation_field(data: bytes, offset: int) -> tuple:
        """
        Parse adaptation field
        
        Returns:
            Tuple of (AdaptationField, new_offset)
        """
        length = data[offset]
        if length == 0:
            return None, offset + 1
        
        # Parse flags
        flags = data[offset + 1]
        discontinuity = bool(flags & 0x80)
        random_access = bool(flags & 0x40)
        priority = bool(flags & 0x20)
        pcr_flag = bool(flags & 0x10)
        opcr_flag = bool(flags & 0x08)
        splicing = bool(flags & 0x04)
        private_data = bool(flags & 0x02)
        extension = bool(flags & 0x01)
        
        current_offset = offset + 2
        
        # Parse PCR
        pcr = None
        if pcr_flag and length >= 6:
            pcr_bytes = data[current_offset:current_offset + 6]
            pcr = int.from_bytes(pcr_bytes, 'big')
            current_offset += 6
        
        # Parse OPCR
        opcr = None
        if opcr_flag and length >= 6:
            opcr_bytes = data[current_offset:current_offset + 6]
            opcr = int.from_bytes(opcr_bytes, 'big')
            current_offset += 6
        
        # Parse splice countdown
        splice_countdown = None
        if splicing:
            splice_countdown = data[current_offset]
            current_offset += 1
        
        # Parse private data
        private = None
        if private_data:
            private_length = data[current_offset]
            current_offset += 1
            private = data[current_offset:current_offset + private_length]
            current_offset += private_length
        
        adaptation_field = AdaptationField(
            length=length,
            discontinuity_indicator=discontinuity,
            random_access_indicator=random_access,
            elementary_stream_priority_indicator=priority,
            pcr_flag=pcr_flag,
            opcr_flag=opcr_flag,
            splicing_point_flag=splicing,
            transport_private_data_flag=private_data,
            adaptation_field_extension_flag=extension,
            pcr=pcr,
            opcr=opcr,
            splice_countdown=splice_countdown,
            private_data=private
        )
        
        return adaptation_field, offset + 1 + length
    
    @staticmethod
    def detect_packet_size(data: bytes, offset: int = 0) -> int:
        """
        Detect TS packet size
        
        Args:
            data: Raw data
            offset: Start offset
        
        Returns:
            Detected packet size
        """
        if len(data) - offset < 208:
            return TSPacketParser.PACKET_SIZE_188
        
        # Check sync byte at different positions
        if data[offset + 188] == TSPacketParser.SYNC_BYTE:
            return TSPacketParser.PACKET_SIZE_188
        
        if data[offset + 204] == TSPacketParser.SYNC_BYTE:
            return TSPacketParser.PACKET_SIZE_204
        
        if data[offset + 208] == TSPacketParser.SYNC_BYTE:
            return TSPacketParser.PACKET_SIZE_208
        
        return TSPacketParser.PACKET_SIZE_188
    
    @staticmethod
    def parse_all(data: bytes, packet_size: int = 0) -> List[TSPacket]:
        """
        Parse multiple TS packets
        
        Args:
            data: Raw data
            packet_size: Packet size (0=auto-detect)
        
        Returns:
            List of TSPacket objects
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
                # Skip invalid packets
                pass
            offset += packet_size
        
        return packets
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/test_ts.py -v
```

预期：PASS

- [ ] **步骤 5：提交**

```bash
git add src/dvb_parser/ts/parser.py tests/test_ts.py
git commit -m "feat: add MPEG-TS parser with multi-size support"
```

---

## 任务 7：PSI 数据模型

**文件：**
- 创建：`src/dvb_parser/psi/__init__.py`
- 创建：`src/dvb_parser/psi/models.py`

- [ ] **步骤 1：创建 psi/__init__.py**

```python
"""PSI (Program Specific Information) parser module"""
```

- [ ] **步骤 2：实现 PSI 数据模型**

```python
# src/dvb_parser/psi/models.py
"""
PSI data models
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PATEntry:
    """PAT entry"""
    program_number: int
    pid: int  # PMT PID or network PID


@dataclass
class PAT:
    """Program Association Table"""
    table_id: int
    version_number: int
    current_next_indicator: bool
    section_number: int
    last_section_number: int
    entries: List[PATEntry]
    
    @property
    def programs(self) -> dict:
        """Get program number to PMT PID mapping"""
        return {entry.program_number: entry.pid for entry in self.entries}


@dataclass
class PMTStream:
    """PMT stream entry"""
    stream_type: int
    pid: int
    descriptors: List[bytes]


@dataclass
class PMT:
    """Program Map Table"""
    table_id: int
    version_number: int
    current_next_indicator: bool
    section_number: int
    last_section_number: int
    program_number: int
    pcr_pid: int
    descriptors: List[bytes]
    streams: List[PMTStream]
```

- [ ] **步骤 3：提交**

```bash
git add src/dvb_parser/psi/
git commit -m "feat: add PSI data models (PAT, PMT)"
```

---

## 任务 8：PAT 解析器

**文件：**
- 创建：`src/dvb_parser/psi/pat.py`
- 创建：`tests/test_psi.py`

- [ ] **步骤 1：编写 PAT 解析器测试**

```python
# tests/test_psi.py
import pytest
from dvb_parser.psi.pat import PATParser

class TestPATParser:
    def test_parse_valid_pat(self):
        """测试解析有效的 PAT"""
        # 构造 PAT section
        # table_id=0x00, section_syntax_indicator=1, section_length=17
        # transport_stream_id=0x0001, version_number=1, current_next_indicator=1
        # section_number=0, last_section_number=0
        # program_number=1, PID=0x100
        # CRC-32 placeholder
        section_data = bytes([
            0x00,                    # table_id
            0b10110000, 0x11,        # syntax_indicator=1, length=17
            0x00, 0x01,              # transport_stream_id
            0b11000001,              # version=1, current_next=1
            0x00,                    # section_number
            0x00,                    # last_section_number
            0x00, 0x01,              # program_number=1
            0b11100001, 0x00,        # PID=0x100
            0x00, 0x00, 0x00, 0x00   # CRC-32 placeholder
        ])
        
        # Calculate correct CRC-32
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')
        
        pat = PATParser.parse(section_data)
        
        assert pat.table_id == 0x00
        assert pat.version_number == 1
        assert pat.current_next_indicator == True
        assert 1 in pat.programs
        assert pat.programs[1] == 0x100
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/test_psi.py -v
```

预期：FAIL - 模块不存在

- [ ] **步骤 3：实现 PAT 解析器**

```python
# src/dvb_parser/psi/pat.py
"""
PAT (Program Association Table) parser
"""

import struct
from typing import List

from dvb_parser.psi.models import PAT, PATEntry
from dvb_parser.utils.crc import crc32


class PATParser:
    """PAT parser"""
    
    @staticmethod
    def parse(data: bytes, offset: int = 0) -> PAT:
        """
        Parse PAT section
        
        Args:
            data: Raw section data
            offset: Start offset
        
        Returns:
            PAT object
        
        Raises:
            ValueError: CRC-32 checksum failure or invalid data
        """
        if len(data) - offset < 12:
            raise ValueError("数据不足")
        
        # Parse header
        table_id = data[offset]
        if table_id != 0x00:
            raise ValueError("不是 PAT 表")
        
        # Section syntax indicator and length
        syntax_length = struct.unpack('>H', data[offset + 1:offset + 3])[0]
        syntax_indicator = (syntax_length >> 15) & 0x01
        section_length = syntax_length & 0x0FFF
        
        # Transport stream ID
        ts_id = struct.unpack('>H', data[offset + 3:offset + 5])[0]
        
        # Version and current/next indicator
        version_current = data[offset + 5]
        version_number = (version_current >> 1) & 0x1F
        current_next_indicator = bool(version_current & 0x01)
        
        # Section numbers
        section_number = data[offset + 6]
        last_section_number = data[offset + 7]
        
        # Parse entries (excluding CRC-32)
        entries = []
        entries_end = offset + 3 + section_length - 4  # 4 bytes for CRC-32
        
        current_offset = offset + 8
        while current_offset < entries_end:
            if current_offset + 4 > len(data):
                break
            
            program_number = struct.unpack('>H', data[current_offset:current_offset + 2])[0]
            pid = struct.unpack('>H', data[current_offset + 2:current_offset + 4])[0] & 0x1FFF
            
            entries.append(PATEntry(
                program_number=program_number,
                pid=pid
            ))
            current_offset += 4
        
        # Verify CRC-32
        section_data = data[offset:offset + 3 + section_length]
        if len(section_data) >= 4:
            expected_crc = struct.unpack('>I', section_data[-4:])[0]
            calculated_crc = crc32(section_data[:-4])
            if expected_crc != calculated_crc:
                raise ValueError("CRC-32 校验失败")
        
        return PAT(
            table_id=table_id,
            version_number=version_number,
            current_next_indicator=current_next_indicator,
            section_number=section_number,
            last_section_number=last_section_number,
            entries=entries
        )
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/test_psi.py -v
```

预期：PASS

- [ ] **步骤 5：提交**

```bash
git add src/dvb_parser/psi/pat.py tests/test_psi.py
git commit -m "feat: add PAT parser with CRC-32 validation"
```

---

## 任务 9：PMT 解析器

**文件：**
- 修改：`src/dvb_parser/psi/pmt.py`（新建）
- 修改：`tests/test_psi.py`

- [ ] **步骤 1：添加 PMT 解析器测试**

```python
# tests/test_psi.py (追加)
from dvb_parser.psi.pmt import PMTParser

class TestPMTParser:
    def test_parse_valid_pmt(self):
        """测试解析有效的 PMT"""
        # 构造 PMT section
        # table_id=0x02, section_syntax_indicator=1, section_length=22
        # program_number=1, version_number=1, current_next_indicator=1
        # section_number=0, last_section_number=0
        # PCR_PID=0x100, program_info_length=0
        # stream_type=0x1B (H.264), PID=0x101
        # CRC-32 placeholder
        section_data = bytes([
            0x02,                    # table_id
            0b10110000, 0x16,        # syntax_indicator=1, length=22
            0x00, 0x01,              # program_number=1
            0b11000001,              # version=1, current_next=1
            0x00,                    # section_number
            0x00,                    # last_section_number
            0b11100001, 0x00,        # PCR_PID=0x100
            0b11110000, 0x00,        # program_info_length=0
            0x1B,                    # stream_type=H.264
            0b11100001, 0x01,        # PID=0x101
            0b11110000, 0x00,        # ES_info_length=0
            0x00, 0x00, 0x00, 0x00   # CRC-32 placeholder
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')
        
        pmt = PMTParser.parse(section_data)
        
        assert pmt.table_id == 0x02
        assert pmt.program_number == 1
        assert pmt.pcr_pid == 0x100
        assert len(pmt.streams) == 1
        assert pmt.streams[0].stream_type == 0x1B
        assert pmt.streams[0].pid == 0x101
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/test_psi.py::TestPMTParser -v
```

预期：FAIL - 模块不存在

- [ ] **步骤 3：实现 PMT 解析器**

```python
# src/dvb_parser/psi/pmt.py
"""
PMT (Program Map Table) parser
"""

import struct
from typing import List

from dvb_parser.psi.models import PMT, PMTStream
from dvb_parser.utils.crc import crc32


class PMTParser:
    """PMT parser"""
    
    @staticmethod
    def parse(data: bytes, offset: int = 0) -> PMT:
        """
        Parse PMT section
        
        Args:
            data: Raw section data
            offset: Start offset
        
        Returns:
            PMT object
        
        Raises:
            ValueError: CRC-32 checksum failure or invalid data
        """
        if len(data) - offset < 16:
            raise ValueError("数据不足")
        
        # Parse header
        table_id = data[offset]
        if table_id != 0x02:
            raise ValueError("不是 PMT 表")
        
        # Section syntax indicator and length
        syntax_length = struct.unpack('>H', data[offset + 1:offset + 3])[0]
        section_length = syntax_length & 0x0FFF
        
        # Program number
        program_number = struct.unpack('>H', data[offset + 3:offset + 5])[0]
        
        # Version and current/next indicator
        version_current = data[offset + 5]
        version_number = (version_current >> 1) & 0x1F
        current_next_indicator = bool(version_current & 0x01)
        
        # Section numbers
        section_number = data[offset + 6]
        last_section_number = data[offset + 7]
        
        # PCR PID
        pcr_pid = struct.unpack('>H', data[offset + 8:offset + 10])[0] & 0x1FFF
        
        # Program info length
        info_length = struct.unpack('>H', data[offset + 10:offset + 12])[0] & 0x03FF
        
        # Skip program descriptors
        current_offset = offset + 12 + info_length
        
        # Parse streams
        streams = []
        streams_end = offset + 3 + section_length - 4  # 4 bytes for CRC-32
        
        while current_offset < streams_end:
            if current_offset + 5 > len(data):
                break
            
            stream_type = data[current_offset]
            pid = struct.unpack('>H', data[current_offset + 1:current_offset + 3])[0] & 0x1FFF
            es_info_length = struct.unpack('>H', data[current_offset + 3:current_offset + 5])[0] & 0x03FF
            
            # Parse ES descriptors
            descriptors = []
            desc_end = current_offset + 5 + es_info_length
            desc_offset = current_offset + 5
            
            while desc_offset < desc_end and desc_offset + 2 <= len(data):
                desc_tag = data[desc_offset]
                desc_length = data[desc_offset + 1]
                desc_data = data[desc_offset:desc_offset + 2 + desc_length]
                descriptors.append(desc_data)
                desc_offset += 2 + desc_length
            
            streams.append(PMTStream(
                stream_type=stream_type,
                pid=pid,
                descriptors=descriptors
            ))
            
            current_offset = desc_end
        
        # Verify CRC-32
        section_data = data[offset:offset + 3 + section_length]
        if len(section_data) >= 4:
            expected_crc = struct.unpack('>I', section_data[-4:])[0]
            calculated_crc = crc32(section_data[:-4])
            if expected_crc != calculated_crc:
                raise ValueError("CRC-32 校验失败")
        
        return PMT(
            table_id=table_id,
            version_number=version_number,
            current_next_indicator=current_next_indicator,
            section_number=section_number,
            last_section_number=last_section_number,
            program_number=program_number,
            pcr_pid=pcr_pid,
            descriptors=[],  # Program-level descriptors
            streams=streams
        )
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/test_psi.py -v
```

预期：PASS

- [ ] **步骤 5：提交**

```bash
git add src/dvb_parser/psi/pmt.py tests/test_psi.py
git commit -m "feat: add PMT parser with stream type detection"
```

---

## 任务 10：集成测试

**文件：**
- 创建：`tests/test_integration.py`

- [ ] **步骤 1：编写集成测试**

```python
# tests/test_integration.py
import pytest
from dvb_parser.bbframe.parser import BBFrameParser
from dvb_parser.ts.parser import TSPacketParser
from dvb_parser.psi.pat import PATParser
from dvb_parser.psi.pmt import PMTParser

class TestIntegration:
    def test_bbframe_to_ts_to_pat(self):
        """测试从 BBFrame 到 PAT 的完整解析链"""
        # 构造包含 PAT 的 BBFrame
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
            0b10110000, 0x11,        # syntax_indicator=1, length=17
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
```

- [ ] **步骤 2：运行集成测试**

```bash
pytest tests/test_integration.py -v
```

预期：PASS

- [ ] **步骤 3：提交**

```bash
git add tests/test_integration.py
git commit -m "test: add integration test for BBFrame -> TS -> PAT chain"
```

---

## 任务 11：完善包导入

**文件：**
- 修改：`src/dvb_parser/__init__.py`
- 修改：`src/dvb_parser/psi/__init__.py`

- [ ] **步骤 1：更新 dvb_parser/__init__.py**

```python
"""
DVB Parser - DVB protocol parser for satellite signal analysis
"""

__version__ = "0.1.0"

from dvb_parser.bbframe.parser import BBFrameParser
from dvb_parser.bbframe.models import BBFrame, BBFrameHeader, StreamType
from dvb_parser.ts.parser import TSPacketParser
from dvb_parser.ts.models import TSPacket, AdaptationField
from dvb_parser.psi.pat import PATParser
from dvb_parser.psi.pmt import PMTParser
from dvb_parser.psi.models import PAT, PMT, PATEntry, PMTStream

__all__ = [
    "BBFrameParser",
    "BBFrame",
    "BBFrameHeader",
    "StreamType",
    "TSPacketParser",
    "TSPacket",
    "AdaptationField",
    "PATParser",
    "PMTParser",
    "PAT",
    "PMT",
    "PATEntry",
    "PMTStream",
]
```

- [ ] **步骤 2：更新 psi/__init__.py**

```python
"""PSI (Program Specific Information) parser module"""

from dvb_parser.psi.pat import PATParser
from dvb_parser.psi.pmt import PMTParser
from dvb_parser.psi.models import PAT, PMT, PATEntry, PMTStream

__all__ = [
    "PATParser",
    "PMTParser",
    "PAT",
    "PMT",
    "PATEntry",
    "PMTStream",
]
```

- [ ] **步骤 3：运行所有测试**

```bash
pytest -v
```

预期：所有测试通过

- [ ] **步骤 4：提交**

```bash
git add src/dvb_parser/__init__.py src/dvb_parser/psi/__init__.py
git commit -m "feat: complete package imports for MVP"
```

---

## 任务 12：最终验证

- [ ] **步骤 1：运行完整测试套件**

```bash
pytest -v --cov=src/dvb_parser
```

预期：所有测试通过，覆盖率 > 80%

- [ ] **步骤 2：验证包安装**

```bash
pip install -e .
python -c "from dvb_parser import BBFrameParser, TSPacketParser; print('Import successful')"
```

预期：Import successful

- [ ] **步骤 3：最终提交**

```bash
git add .
git commit -m "feat: complete MVP - BBFrame, MPEG-TS, PAT, PMT parsers"
```

---

## 后续任务（P1/P2 优先级）

以下任务在 MVP 完成后实施：

### P1 任务：
- SDT 解析器
- NIT 解析器
- PES 解析器

### P2 任务：
- GSE 解析器
- MPE 解析器
- ULE 解析器
- NIP 解析器
- EIT 解析器
- TDT 解析器
