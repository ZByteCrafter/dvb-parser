# DVB Parser P2 扩展实施计划

> **致自动化代理：** 必须使用子代理驱动开发（推荐）或执行计划子技能来逐任务实施本计划。步骤使用复选框（`- [ ]`）语法进行跟踪。

**目标：** 在 P0 和 P1 基础上扩展实现 GSE、MPE、ULE、NIP、EIT、TDT 六个解析器

**架构：** 遵循现有分层解析器链架构，每个协议层有独立的 Parser 类，返回结构化 dataclass 对象。GSE 解析器处理 BBFrame 中的 GSE 数据，MPE/ULE/NIP 解析器处理 TS 中的数据广播，EIT/TDT 解析器处理 SI 扩展表。

**技术栈：** Python 3.8+, dataclasses, struct, pytest

---

## 文件结构

```
dvb-parser/
├── src/dvb_parser/
│   ├── gse/                   # 新增
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── parser.py
│   ├── mpe/                   # 新增
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── parser.py
│   ├── ule/                   # 新增
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── parser.py
│   ├── nip/                   # 新增
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── parser.py
│   ├── si/                    # 扩展
│   │   ├── models.py          # 追加 EIT, TDT, TOT 模型
│   │   ├── eit.py             # 新增
│   │   └── tdt.py             # 新增
│   └── __init__.py            # 更新导入
├── tests/
│   ├── test_gse.py            # 新增
│   ├── test_mpe.py            # 新增
│   ├── test_ule.py            # 新增
│   ├── test_nip.py            # 新增
│   ├── test_eit.py            # 新增
│   └── test_tdt.py            # 新增
└── ...
```

---

## 任务 1：GSE 数据模型和解析器

**文件：**
- 创建：`src/dvb_parser/gse/__init__.py`
- 创建：`src/dvb_parser/gse/models.py`
- 创建：`src/dvb_parser/gse/parser.py`
- 创建：`tests/test_gse.py`

- [ ] **步骤 1：创建 gse/__init__.py**

```python
"""GSE (Generic Stream Encapsulation) parser module"""
```

- [ ] **步骤 2：实现 GSE 数据模型**

```python
# src/dvb_parser/gse/models.py
"""
GSE data models
"""

from dataclasses import dataclass
from typing import Optional


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

- [ ] **步骤 3：编写 GSE 解析器测试**

```python
# tests/test_gse.py
import pytest
from dvb_parser.gse.parser import GSEParser
from dvb_parser.gse.models import GSEPacket

class TestGSEParser:
    def test_parse_complete_packet(self):
        """测试解析完整 GSE 包（无分片）"""
        # 构造 GSE 包
        # Start=1, End=1, Label Type=0 (无 Label)
        # Protocol Type=0x0800 (IPv4)
        # Total Length=16
        # Payload=16 bytes
        # CRC-32 placeholder
        gse_data = bytes([
            0b11000000,              # Start=1, End=1, Label Type=0
            0x00,                    # Reserved
            0x08, 0x00,              # Protocol Type (IPv4)
            0x00, 0x10,              # Total Length=16
            # Payload
            0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
            0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
            # CRC-32 placeholder
            0x00, 0x00, 0x00, 0x00
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(gse_data[:-4])
        gse_data = gse_data[:-4] + crc_value.to_bytes(4, 'big')
        
        packet = GSEParser.parse(gse_data)
        
        assert packet.start == True
        assert packet.end == True
        assert packet.label_type == 0
        assert packet.protocol_type == 0x0800
        assert packet.total_length == 16
        assert len(packet.payload) == 16
        assert packet.is_ipv4 == True
        assert packet.is_complete == True
    
    def test_parse_fragment_start(self):
        """测试解析分片开始"""
        # Start=1, End=0, Label Type=1 (6 字节 Label)
        gse_data = bytes([
            0b10010000,              # Start=1, End=0, Label Type=1
            0x00,                    # Reserved
            0x08, 0x00,              # Protocol Type (IPv4)
            0x00, 0x20,              # Total Length=32
            # Label (6 bytes)
            0x01, 0x02, 0x03, 0x04, 0x05, 0x06,
            # Payload (16 bytes)
            0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
            0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
            # CRC-32 placeholder
            0x00, 0x00, 0x00, 0x00
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(gse_data[:-4])
        gse_data = gse_data[:-4] + crc_value.to_bytes(4, 'big')
        
        packet = GSEParser.parse(gse_data)
        
        assert packet.start == True
        assert packet.end == False
        assert packet.label_type == 1
        assert packet.label == bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06])
        assert packet.is_fragment_start == True
    
    def test_crc32_validation(self):
        """测试 CRC-32 校验失败"""
        gse_data = bytes([
            0b11000000, 0x00, 0x08, 0x00, 0x00, 0x10,
            0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
            0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
            0xFF, 0xFF, 0xFF, 0xFF  # 错误的 CRC-32
        ])
        
        with pytest.raises(ValueError, match="CRC-32 校验失败"):
            GSEParser.parse(gse_data)
```

- [ ] **步骤 4：运行测试验证失败**

```bash
pytest tests/test_gse.py -v
```

预期：FAIL - 模块不存在

- [ ] **步骤 5：实现 GSE 解析器**

```python
# src/dvb_parser/gse/parser.py
"""
GSE (Generic Stream Encapsulation) parser
"""

import struct
from typing import Optional

from dvb_parser.gse.models import GSEPacket
from dvb_parser.utils.crc import crc32


class GSEParser:
    """GSE 解析器"""
    
    @staticmethod
    def parse(data: bytes, offset: int = 0) -> GSEPacket:
        """
        解析 GSE 包
        
        Args:
            data: 原始数据
            offset: 起始偏移
        
        Returns:
            GSEPacket 对象
        
        Raises:
            ValueError: CRC-32 校验失败或数据无效
        """
        if len(data) - offset < 6:
            raise ValueError("数据不足")
        
        # 解析第一个字节
        first_byte = data[offset]
        start = bool(first_byte & 0x80)
        end = bool(first_byte & 0x40)
        label_type = (first_byte >> 4) & 0x03
        
        # 保留字节
        # data[offset + 1] is reserved
        
        # 解析协议类型
        protocol_type = struct.unpack('>H', data[offset + 2:offset + 4])[0]
        
        # 解析总长度（如果存在）
        total_length = None
        current_offset = offset + 4
        
        if start:
            total_length = struct.unpack('>H', data[current_offset:current_offset + 2])[0]
            current_offset += 2
        
        # 解析 Label（如果存在）
        label = None
        if label_type == 1:  # 6 字节 Label
            label = data[current_offset:current_offset + 6]
            current_offset += 6
        elif label_type == 2:  # 3 字节 Label
            label = data[current_offset:current_offset + 3]
            current_offset += 3
        
        # 计算 payload 长度
        # 总长度 - 头部长度 - CRC-32 长度
        header_length = current_offset - offset
        crc_length = 4
        
        if total_length is not None:
            payload_length = total_length - header_length + crc_length
        else:
            # 对于分片包，payload 延伸到 CRC-32 之前
            payload_length = len(data) - offset - header_length - crc_length
        
        if payload_length < 0:
            raise ValueError("无效的包长度")
        
        # 提取 payload
        payload = data[current_offset:current_offset + payload_length]
        current_offset += payload_length
        
        # 验证 CRC-32
        if current_offset + 4 > len(data):
            raise ValueError("数据不足，无法读取 CRC-32")
        
        crc32_value = struct.unpack('>I', data[current_offset:current_offset + 4])[0]
        calculated_crc = crc32(data[offset:current_offset])
        
        if crc32_value != calculated_crc:
            raise ValueError("CRC-32 校验失败")
        
        return GSEPacket(
            start=start,
            end=end,
            label_type=label_type,
            protocol_type=protocol_type,
            total_length=total_length,
            label=label,
            payload=payload,
            crc32=crc32_value
        )
```

- [ ] **步骤 6：运行测试验证通过**

```bash
pytest tests/test_gse.py -v
```

预期：PASS

- [ ] **步骤 7：提交**

```bash
git add src/dvb_parser/gse/ tests/test_gse.py
git commit -m "feat: add GSE parser with fragmentation support"
```

---

## 任务 2：MPE 数据模型和解析器

**文件：**
- 创建：`src/dvb_parser/mpe/__init__.py`
- 创建：`src/dvb_parser/mpe/models.py`
- 创建：`src/dvb_parser/mpe/parser.py`
- 创建：`tests/test_mpe.py`

- [ ] **步骤 1：创建 mpe/__init__.py**

```python
"""MPE (Multi-Protocol Encapsulation) parser module"""
```

- [ ] **步骤 2：实现 MPE 数据模型**

```python
# src/dvb_parser/mpe/models.py
"""
MPE data models
"""

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
        return (self.mac_address[0] == 0x01 and 
                self.mac_address[1] == 0x00 and 
                self.mac_address[2] == 0x5E)
```

- [ ] **步骤 3：编写 MPE 解析器测试**

```python
# tests/test_mpe.py
import pytest
from dvb_parser.mpe.parser import MPEParser
from dvb_parser.mpe.models import MPEDatagram

class TestMPEParser:
    def test_parse_valid_mpe(self):
        """测试解析有效的 MPE section"""
        # 构造 MPE section
        section_data = bytes([
            0x3E,                    # table_id
            0b10110000, 0x12,        # syntax_indicator=1, length=18
            # MAC address
            0x01, 0x02, 0x03, 0x04, 0x05, 0x06,
            # Payload (IP datagram)
            0x45, 0x00, 0x00, 0x08,  # IPv4 header
            0x00, 0x00, 0x00, 0x00,
            # CRC-32 placeholder
            0x00, 0x00, 0x00, 0x00
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')
        
        mpe = MPEParser.parse(section_data)
        
        assert mpe.table_id == 0x3E
        assert mpe.mac_address == bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06])
        assert mpe.mac_address_str == "01:02:03:04:05:06"
        assert len(mpe.payload) == 8
    
    def test_mac_address_parsing(self):
        """测试 MAC 地址解析"""
        section_data = bytes([
            0x3E, 0b10110000, 0x0E,
            0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,  # 广播地址
            0x45, 0x00, 0x00, 0x04,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')
        
        mpe = MPEParser.parse(section_data)
        
        assert mpe.is_broadcast == True
```

- [ ] **步骤 4：运行测试验证失败**

```bash
pytest tests/test_mpe.py -v
```

预期：FAIL - 模块不存在

- [ ] **步骤 5：实现 MPE 解析器**

```python
# src/dvb_parser/mpe/parser.py
"""
MPE (Multi-Protocol Encapsulation) parser
"""

import struct

from dvb_parser.mpe.models import MPEDatagram
from dvb_parser.utils.crc import crc32


class MPEParser:
    """MPE 解析器"""
    
    @staticmethod
    def parse(data: bytes, offset: int = 0) -> MPEDatagram:
        """
        解析 MPE section
        
        Args:
            data: 原始数据
            offset: 起始偏移
        
        Returns:
            MPEDatagram 对象
        
        Raises:
            ValueError: CRC-32 校验失败或数据无效
        """
        if len(data) - offset < 12:
            raise ValueError("数据不足")
        
        # 解析表头
        table_id = data[offset]
        if table_id != 0x3E:
            raise ValueError("不是 MPE 表")
        
        # Section syntax indicator 和 length
        syntax_length = struct.unpack('>H', data[offset + 1:offset + 3])[0]
        section_length = syntax_length & 0x0FFF
        
        # MAC 地址
        mac_address = data[offset + 3:offset + 9]
        
        # 提取 payload（排除 CRC-32）
        payload = data[offset + 9:offset + 3 + section_length - 4]
        
        # 验证 CRC-32
        section_data = data[offset:offset + 3 + section_length]
        if len(section_data) >= 4:
            expected_crc = struct.unpack('>I', section_data[-4:])[0]
            calculated_crc = crc32(section_data[:-4])
            if expected_crc != calculated_crc:
                raise ValueError("CRC-32 校验失败")
        
        return MPEDatagram(
            table_id=table_id,
            mac_address=mac_address,
            payload=payload,
            crc32=expected_crc
        )
```

- [ ] **步骤 6：运行测试验证通过**

```bash
pytest tests/test_mpe.py -v
```

预期：PASS

- [ ] **步骤 7：提交**

```bash
git add src/dvb_parser/mpe/ tests/test_mpe.py
git commit -m "feat: add MPE parser with MAC address support"
```

---

## 任务 3：ULE 数据模型和解析器

**文件：**
- 创建：`src/dvb_parser/ule/__init__.py`
- 创建：`src/dvb_parser/ule/models.py`
- 创建：`src/dvb_parser/ule/parser.py`
- 创建：`tests/test_ule.py`

- [ ] **步骤 1：创建 ule/__init__.py**

```python
"""ULE (Unidirectional Lightweight Encapsulation) parser module"""
```

- [ ] **步骤 2：实现 ULE 数据模型**

```python
# src/dvb_parser/ule/models.py
"""
ULE data models
"""

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

- [ ] **步骤 3：编写 ULE 解析器测试**

```python
# tests/test_ule.py
import pytest
from dvb_parser.ule.parser import ULEParser
from dvb_parser.ule.models import ULESNDU

class TestULEParser:
    def test_parse_sndu_with_type(self):
        """测试解析包含协议类型的 SNDU"""
        # Length/Type=0x0800 (IPv4)
        # Destination MAC=6 bytes
        # Payload=8 bytes
        # CRC-32 placeholder
        sndu_data = bytes([
            0x08, 0x00,              # Protocol Type (IPv4)
            0x01, 0x02, 0x03, 0x04, 0x05, 0x06,  # Destination MAC
            # Payload
            0x45, 0x00, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00,
            # CRC-32 placeholder
            0x00, 0x00, 0x00, 0x00
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(sndu_data[:-4])
        sndu_data = sndu_data[:-4] + crc_value.to_bytes(4, 'big')
        
        sndu = ULEParser.parse(sndu_data)
        
        assert sndu.length_or_type == 0x0800
        assert sndu.is_type == True
        assert sndu.protocol_type == 0x0800
        assert sndu.is_ipv4 == True
        assert sndu.destination_mac == bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06])
        assert len(sndu.payload) == 8
    
    def test_parse_sndu_with_length(self):
        """测试解析包含长度的 SNDU"""
        # Length/Type=16 (长度)
        # Payload=16 bytes
        # CRC-32 placeholder
        sndu_data = bytes([
            0x00, 0x10,              # Length=16
            # Payload
            0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
            0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
            # CRC-32 placeholder
            0x00, 0x00, 0x00, 0x00
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(sndu_data[:-4])
        sndu_data = sndu_data[:-4] + crc_value.to_bytes(4, 'big')
        
        sndu = ULEParser.parse(sndu_data)
        
        assert sndu.length_or_type == 16
        assert sndu.is_type == False
        assert sndu.length == 16
        assert len(sndu.payload) == 16
```

- [ ] **步骤 4：运行测试验证失败**

```bash
pytest tests/test_ule.py -v
```

预期：FAIL - 模块不存在

- [ ] **步骤 5：实现 ULE 解析器**

```python
# src/dvb_parser/ule/parser.py
"""
ULE (Unidirectional Lightweight Encapsulation) parser
"""

import struct
from typing import List, Optional

from dvb_parser.ule.models import ULESNDU
from dvb_parser.utils.crc import crc32


class ULEParser:
    """ULE 解析器"""
    
    @staticmethod
    def parse(data: bytes, offset: int = 0) -> ULESNDU:
        """
        解析 ULE SNDU
        
        Args:
            data: 原始数据
            offset: 起始偏移
        
        Returns:
            ULESNDU 对象
        
        Raises:
            ValueError: CRC-32 校验失败或数据无效
        """
        if len(data) - offset < 4:
            raise ValueError("数据不足")
        
        # 解析 Length/Type
        length_or_type = struct.unpack('>H', data[offset:offset + 2])[0]
        
        current_offset = offset + 2
        
        # 解析目标 MAC 地址（如果 Length/Type < 1536）
        destination_mac = None
        if length_or_type < 1536:
            if current_offset + 6 > len(data):
                raise ValueError("数据不足")
            destination_mac = data[current_offset:current_offset + 6]
            current_offset += 6
        
        # 解析扩展头（如果有）
        extension_headers: List[bytes] = []
        
        # 提取 payload
        # 对于 Type 模式，payload 延伸到 CRC-32 之前
        # 对于 Length 模式，payload 长度由 Length 决定
        crc_length = 4
        
        if length_or_type >= 1536:
            # Type 模式
            payload_length = len(data) - offset - (current_offset - offset) - crc_length
        else:
            # Length 模式
            payload_length = length_or_type - (current_offset - offset) + 2
        
        if payload_length < 0:
            raise ValueError("无效的包长度")
        
        payload = data[current_offset:current_offset + payload_length]
        current_offset += payload_length
        
        # 验证 CRC-32
        if current_offset + 4 > len(data):
            raise ValueError("数据不足，无法读取 CRC-32")
        
        crc32_value = struct.unpack('>I', data[current_offset:current_offset + 4])[0]
        calculated_crc = crc32(data[offset:current_offset])
        
        if crc32_value != calculated_crc:
            raise ValueError("CRC-32 校验失败")
        
        return ULESNDU(
            length_or_type=length_or_type,
            destination_mac=destination_mac,
            extension_headers=extension_headers,
            payload=payload,
            crc32=crc32_value
        )
```

- [ ] **步骤 6：运行测试验证通过**

```bash
pytest tests/test_ule.py -v
```

预期：PASS

- [ ] **步骤 7：提交**

```bash
git add src/dvb_parser/ule/ tests/test_ule.py
git commit -m "feat: add ULE parser with Type/Length support"
```

---

## 任务 4：NIP 数据模型和解析器

**文件：**
- 创建：`src/dvb_parser/nip/__init__.py`
- 创建：`src/dvb_parser/nip/models.py`
- 创建：`src/dvb_parser/nip/parser.py`
- 创建：`tests/test_nip.py`

- [ ] **步骤 1：创建 nip/__init__.py**

```python
"""NIP (Network Independent Protocol) parser module"""
```

- [ ] **步骤 2：实现 NIP 数据模型**

```python
# src/dvb_parser/nip/models.py
"""
NIP data models
"""

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

- [ ] **步骤 3：编写 NIP 解析器测试**

```python
# tests/test_nip.py
import pytest
from dvb_parser.nip.parser import NIPParser
from dvb_parser.nip.models import NIPDataUnit, NIPStreaming

class TestNIPParser:
    def test_parse_data_piping(self):
        """测试解析数据管道"""
        # Data Piping 直接传输原始数据
        data = bytes([0x01, 0x02, 0x03, 0x04])
        
        nip = NIPParser.parse_piping(data)
        
        assert nip.method == "piping"
        assert nip.payload == data
    
    def test_parse_data_streaming(self):
        """测试解析数据流"""
        # Data Streaming 包含 data_identifier
        streaming_data = bytes([
            0x01,                    # synchronous=1
            0x00, 0x01,              # data_identifier
            0x02, 0x03, 0x04         # payload
        ])
        
        nip = NIPParser.parse_streaming(streaming_data)
        
        assert nip.synchronous == True
        assert nip.data_identifier == 1
        assert len(nip.payload) == 3
```

- [ ] **步骤 4：运行测试验证失败**

```bash
pytest tests/test_nip.py -v
```

预期：FAIL - 模块不存在

- [ ] **步骤 5：实现 NIP 解析器**

```python
# src/dvb_parser/nip/parser.py
"""
NIP (Network Independent Protocol) parser
"""

import struct

from dvb_parser.nip.models import NIPDataUnit, NIPStreaming, NIPCarousel


class NIPParser:
    """NIP 解析器"""
    
    @staticmethod
    def parse_piping(data: bytes, offset: int = 0) -> NIPDataUnit:
        """
        解析数据管道
        
        Args:
            data: 原始数据
            offset: 起始偏移
        
        Returns:
            NIPDataUnit 对象
        """
        payload = data[offset:]
        
        return NIPDataUnit(
            method="piping",
            payload=payload
        )
    
    @staticmethod
    def parse_streaming(data: bytes, offset: int = 0) -> NIPStreaming:
        """
        解析数据流
        
        Args:
            data: 原始数据
            offset: 起始偏移
        
        Returns:
            NIPStreaming 对象
        
        Raises:
            ValueError: 数据无效
        """
        if len(data) - offset < 5:
            raise ValueError("数据不足")
        
        # 解析同步标志
        synchronous = bool(data[offset])
        
        # 解析数据标识
        data_identifier = struct.unpack('>H', data[offset + 1:offset + 3])[0]
        
        # 提取 payload
        payload = data[offset + 3:]
        
        return NIPStreaming(
            synchronous=synchronous,
            data_identifier=data_identifier,
            payload=payload
        )
    
    @staticmethod
    def parse_carousel(data: bytes, offset: int = 0) -> NIPCarousel:
        """
        解析数据循环
        
        Args:
            data: 原始数据
            offset: 起始偏移
        
        Returns:
            NIPCarousel 对象
        
        Raises:
            ValueError: 数据无效
        """
        if len(data) - offset < 8:
            raise ValueError("数据不足")
        
        # 解析 download_id
        download_id = struct.unpack('>I', data[offset:offset + 4])[0]
        
        # 解析 block_size
        block_size = struct.unpack('>H', data[offset + 4:offset + 6])[0]
        
        # 解析 blocks（简化实现）
        blocks = []
        current_offset = offset + 6
        
        while current_offset + block_size <= len(data):
            block = data[current_offset:current_offset + block_size]
            blocks.append(block)
            current_offset += block_size
        
        return NIPCarousel(
            download_id=download_id,
            block_size=block_size,
            blocks=blocks
        )
```

- [ ] **步骤 6：运行测试验证通过**

```bash
pytest tests/test_nip.py -v
```

预期：PASS

- [ ] **步骤 7：提交**

```bash
git add src/dvb_parser/nip/ tests/test_nip.py
git commit -m "feat: add NIP parser with data piping and streaming support"
```

---

## 任务 5：EIT 解析器

**文件：**
- 修改：`src/dvb_parser/si/models.py`（追加 EIT 模型）
- 创建：`src/dvb_parser/si/eit.py`
- 创建：`tests/test_eit.py`

- [ ] **步骤 1：追加 EIT 数据模型**

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

- [ ] **步骤 2：编写 EIT 解析器测试**

```python
# tests/test_eit.py
import pytest
from dvb_parser.si.eit import EITParser
from dvb_parser.si.models import EIT, EITEvent

class TestEITParser:
    def test_parse_present_following(self):
        """测试解析当前/后续事件"""
        # 构造 EIT section
        section_data = bytes([
            0x4E,                    # table_id (present/following, current TS)
            0b10110000, 0x20,        # syntax_indicator=1, length=32
            0x00, 0x01,              # service_id
            0b11000001,              # version=1, current_next=1
            0x00, 0x01,              # transport_stream_id
            0x00, 0x01,              # original_network_id
            0x00,                    # section_number
            0x00,                    # last_section_number
            # Event entry
            0x00, 0x01,              # event_id
            # Start time (MJD + BCD)
            0x58, 0x00,              # MJD
            0x12, 0x00, 0x00,        # BCD time (12:00:00)
            # Duration (BCD)
            0x01, 0x30, 0x00,        # 1h30m
            0b00000101,              # running_status=1, free_ca=0, descriptors_length=5
            # Event name descriptor
            0x4D, 0x03,              # descriptor_tag=0x4D, length=3
            0x45, 0x56, 0x54,        # "EVT"
            # CRC-32 placeholder
            0x00, 0x00, 0x00, 0x00
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')
        
        eit = EITParser.parse(section_data)
        
        assert eit.table_id == 0x4E
        assert eit.service_id == 1
        assert len(eit.events) == 1
        assert eit.events[0].event_id == 1
        assert eit.events[0].event_name == "EVT"
    
    def test_parse_schedule(self):
        """测试解析时间表事件"""
        section_data = bytes([
            0x50,                    # table_id (schedule, current TS)
            0b10110000, 0x1A,        # syntax_indicator=1, length=26
            0x00, 0x01,              # service_id
            0b11000001,              # version=1, current_next=1
            0x00, 0x01,              # transport_stream_id
            0x00, 0x01,              # original_network_id
            0x00,                    # section_number
            0x00,                    # last_section_number
            # Event entry
            0x00, 0x01,              # event_id
            0x58, 0x00,              # MJD
            0x15, 0x30, 0x00,        # 15:30:00
            0x00, 0x45, 0x00,        # 45m
            0b00000001,              # running_status=0, free_ca=0, descriptors_length=1
            0x00, 0x00,              # Empty descriptor
            # CRC-32
            0x00, 0x00, 0x00, 0x00
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')
        
        eit = EITParser.parse(section_data)
        
        assert eit.table_id == 0x50
        assert len(eit.events) == 1
```

- [ ] **步骤 3：运行测试验证失败**

```bash
pytest tests/test_eit.py -v
```

预期：FAIL - 模块不存在

- [ ] **步骤 4：实现 EIT 解析器**

```python
# src/dvb_parser/si/eit.py
"""
EIT (Event Information Table) parser
"""

import struct
from typing import List

from dvb_parser.si.models import EIT, EITEvent
from dvb_parser.utils.crc import crc32


class EITParser:
    """EIT 解析器"""
    
    @staticmethod
    def parse(data: bytes, offset: int = 0) -> EIT:
        """
        解析 EIT section
        
        Args:
            data: 原始数据
            offset: 起始偏移
        
        Returns:
            EIT 对象
        
        Raises:
            ValueError: CRC-32 校验失败或数据无效
        """
        if len(data) - offset < 14:
            raise ValueError("数据不足")
        
        # 解析表头
        table_id = data[offset]
        if table_id < 0x4E or table_id > 0x6F:
            raise ValueError("不是 EIT 表")
        
        # Section syntax indicator 和 length
        syntax_length = struct.unpack('>H', data[offset + 1:offset + 3])[0]
        section_length = syntax_length & 0x0FFF
        
        # Service ID
        service_id = struct.unpack('>H', data[offset + 3:offset + 5])[0]
        
        # Version 和 current/next indicator
        version_current = data[offset + 5]
        version_number = (version_current >> 1) & 0x1F
        current_next_indicator = bool(version_current & 0x01)
        
        # Transport stream ID 和 original network ID
        ts_id = struct.unpack('>H', data[offset + 6:offset + 8])[0]
        original_network_id = struct.unpack('>H', data[offset + 8:offset + 10])[0]
        
        # Section numbers
        section_number = data[offset + 10]
        last_section_number = data[offset + 11]
        
        # 解析事件列表
        events = []
        events_end = offset + 3 + section_length - 4  # 4 bytes for CRC-32
        
        current_offset = offset + 12
        
        while current_offset < events_end:
            if current_offset + 12 > len(data):
                break
            
            # 解析事件信息
            event_id = struct.unpack('>H', data[current_offset:current_offset + 2])[0]
            
            # 解析开始时间 (MJD + BCD)
            mjd = struct.unpack('>H', data[current_offset + 2:current_offset + 4])[0]
            bcd_time = data[current_offset + 4:current_offset + 7]
            start_time = EITParser._mjd_bcd_to_timestamp(mjd, bcd_time)
            
            # 解析持续时间 (BCD)
            duration_bcd = data[current_offset + 7:current_offset + 10]
            duration = EITParser._bcd_to_duration(duration_bcd)
            
            # Running status 和 free CA mode
            running_free_ca = struct.unpack('>H', data[current_offset + 10:current_offset + 12])[0]
            running_status = (running_free_ca >> 13) & 0x07
            free_ca_mode = bool(running_free_ca & 0x1000)
            descriptors_length = running_free_ca & 0x0FFF
            
            # 提取描述符
            descriptors = []
            desc_end = current_offset + 12 + descriptors_length
            desc_offset = current_offset + 12
            
            event_name = ""
            event_description = ""
            
            while desc_offset < desc_end and desc_offset + 2 <= len(data):
                desc_tag = data[desc_offset]
                desc_length = data[desc_offset + 1]
                desc_data = data[desc_offset:desc_offset + 2 + desc_length]
                descriptors.append(desc_data)
                
                # 解析事件名称描述符
                if desc_tag == 0x4D and desc_length >= 4:  # Short event descriptor
                    language = data[desc_offset + 2:desc_offset + 5].decode('ascii', errors='replace')
                    name_length = data[desc_offset + 5]
                    if desc_offset + 6 + name_length <= desc_end:
                        event_name = data[desc_offset + 6:desc_offset + 6 + name_length].decode('utf-8', errors='replace')
                    desc_length_offset = desc_offset + 6 + name_length
                    if desc_length_offset < desc_end:
                        text_length = data[desc_length_offset]
                        if desc_length_offset + 1 + text_length <= desc_end:
                            event_description = data[desc_length_offset + 1:desc_length_offset + 1 + text_length].decode('utf-8', errors='replace')
                
                desc_offset += 2 + desc_length
            
            events.append(EITEvent(
                event_id=event_id,
                start_time=start_time,
                duration=duration,
                running_status=running_status,
                free_ca_mode=free_ca_mode,
                descriptors=descriptors,
                event_name=event_name,
                event_description=event_description
            ))
            
            current_offset = desc_end
        
        # 验证 CRC-32
        section_data = data[offset:offset + 3 + section_length]
        if len(section_data) >= 4:
            expected_crc = struct.unpack('>I', section_data[-4:])[0]
            calculated_crc = crc32(section_data[:-4])
            if expected_crc != calculated_crc:
                raise ValueError("CRC-32 校验失败")
        
        return EIT(
            table_id=table_id,
            service_id=service_id,
            transport_stream_id=ts_id,
            original_network_id=original_network_id,
            version_number=version_number,
            current_next_indicator=current_next_indicator,
            section_number=section_number,
            last_section_number=last_section_number,
            events=events
        )
    
    @staticmethod
    def _mjd_bcd_to_timestamp(mjd: int, bcd_time: bytes) -> int:
        """MJD + BCD 时间转 UTC timestamp"""
        # MJD 转日期
        y = int((mjd - 15078.2) / 365.25)
        m = int((mjd - 14956.1 - int(y * 365.25)) / 30.6001)
        d = mjd - 14956 - int(y * 365.25) - int(m * 30.6001)
        
        if m == 14 or m == 15:
            y += 1
            m -= 12
        
        y += 1900
        
        # BCD 时间
        hour = ((bcd_time[0] >> 4) * 10) + (bcd_time[0] & 0x0F)
        minute = ((bcd_time[1] >> 4) * 10) + (bcd_time[1] & 0x0F)
        second = ((bcd_time[2] >> 4) * 10) + (bcd_time[2] & 0x0F)
        
        # 简化实现：返回秒数
        return hour * 3600 + minute * 60 + second
    
    @staticmethod
    def _bcd_to_duration(bcd_duration: bytes) -> int:
        """BCD 持续时间转秒数"""
        hour = ((bcd_duration[0] >> 4) * 10) + (bcd_duration[0] & 0x0F)
        minute = ((bcd_duration[1] >> 4) * 10) + (bcd_duration[1] & 0x0F)
        second = ((bcd_duration[2] >> 4) * 10) + (bcd_duration[2] & 0x0F)
        
        return hour * 3600 + minute * 60 + second
```

- [ ] **步骤 5：运行测试验证通过**

```bash
pytest tests/test_eit.py -v
```

预期：PASS

- [ ] **步骤 6：提交**

```bash
git add src/dvb_parser/si/eit.py src/dvb_parser/si/models.py tests/test_eit.py
git commit -m "feat: add EIT parser with event information support"
```

---

## 任务 6：TDT 解析器

**文件：**
- 修改：`src/dvb_parser/si/models.py`（追加 TDT/TOT 模型）
- 创建：`src/dvb_parser/si/tdt.py`
- 创建：`tests/test_tdt.py`

- [ ] **步骤 1：追加 TDT/TOT 数据模型**

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

- [ ] **步骤 2：编写 TDT 解析器测试**

```python
# tests/test_tdt.py
import pytest
from dvb_parser.si.tdt import TDTParser
from dvb_parser.si.models import TDT, TOT

class TestTDTParser:
    def test_parse_tdt(self):
        """测试解析 TDT"""
        # 构造 TDT section
        section_data = bytes([
            0x70,                    # table_id (TDT)
            0b10110000, 0x05,        # syntax_indicator=1, length=5
            # UTC time (MJD + BCD)
            0x58, 0x00,              # MJD
            0x12, 0x30, 0x00         # 12:30:00
        ])
        
        tdt = TDTParser.parse(section_data)
        
        assert tdt.table_id == 0x70
        assert tdt.utc_time == 12 * 3600 + 30 * 60  # 45000 seconds
    
    def test_parse_tot(self):
        """测试解析 TOT"""
        # 构造 TOT section
        section_data = bytes([
            0x73,                    # table_id (TOT)
            0b10110000, 0x0D,        # syntax_indicator=1, length=13
            # UTC time (MJD + BCD)
            0x58, 0x00,              # MJD
            0x15, 0x00, 0x00,        # 15:00:00
            # Descriptors
            0b11110000, 0x05,        # descriptors_length=5
            # Time offset descriptor
            0x58, 0x03,              # descriptor_tag=0x58, length=3
            0x43, 0x48, 0x4E,        # "CHN"
            # CRC-32 placeholder
            0x00, 0x00, 0x00, 0x00
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(section_data[:-4])
        section_data = section_data[:-4] + crc_value.to_bytes(4, 'big')
        
        tot = TDTParser.parse(section_data)
        
        assert tot.table_id == 0x73
        assert tot.utc_time == 15 * 3600  # 54000 seconds
        assert len(tot.descriptors) == 1
```

- [ ] **步骤 3：运行测试验证失败**

```bash
pytest tests/test_tdt.py -v
```

预期：FAIL - 模块不存在

- [ ] **步骤 4：实现 TDT 解析器**

```python
# src/dvb_parser/si/tdt.py
"""
TDT (Time and Date Table) and TOT (Time Offset Table) parser
"""

import struct
from typing import List, Union

from dvb_parser.si.models import TDT, TOT
from dvb_parser.utils.crc import crc32


class TDTParser:
    """TDT/TOT 解析器"""
    
    @staticmethod
    def parse(data: bytes, offset: int = 0) -> Union[TDT, TOT]:
        """
        解析 TDT 或 TOT section
        
        Args:
            data: 原始数据
            offset: 起始偏移
        
        Returns:
            TDT 或 TOT 对象
        
        Raises:
            ValueError: 数据无效
        """
        if len(data) - offset < 7:
            raise ValueError("数据不足")
        
        # 解析表头
        table_id = data[offset]
        
        # Section syntax indicator 和 length
        syntax_length = struct.unpack('>H', data[offset + 1:offset + 3])[0]
        section_length = syntax_length & 0x0FFF
        
        # 解析 UTC 时间 (MJD + BCD)
        mjd = struct.unpack('>H', data[offset + 3:offset + 5])[0]
        bcd_time = data[offset + 5:offset + 8]
        utc_time = TDTParser._mjd_bcd_to_timestamp(mjd, bcd_time)
        
        if table_id == 0x70:  # TDT
            return TDT(
                table_id=table_id,
                utc_time=utc_time
            )
        elif table_id == 0x73:  # TOT
            # 解析描述符
            descriptors = []
            descriptors_length = struct.unpack('>H', data[offset + 8:offset + 10])[0] & 0x0FFF
            
            current_offset = offset + 10
            desc_end = current_offset + descriptors_length
            
            while current_offset < desc_end and current_offset + 2 <= len(data):
                desc_tag = data[current_offset]
                desc_length = data[current_offset + 1]
                desc_data = data[current_offset:current_offset + 2 + desc_length]
                descriptors.append(desc_data)
                current_offset += 2 + desc_length
            
            # 验证 CRC-32
            section_data = data[offset:offset + 3 + section_length]
            if len(section_data) >= 4:
                expected_crc = struct.unpack('>I', section_data[-4:])[0]
                calculated_crc = crc32(section_data[:-4])
                if expected_crc != calculated_crc:
                    raise ValueError("CRC-32 校验失败")
            
            return TOT(
                table_id=table_id,
                utc_time=utc_time,
                descriptors=descriptors
            )
        else:
            raise ValueError("不是 TDT 或 TOT 表")
    
    @staticmethod
    def _mjd_bcd_to_timestamp(mjd: int, bcd_time: bytes) -> int:
        """MJD + BCD 时间转 UTC timestamp（秒数）"""
        # BCD 时间
        hour = ((bcd_time[0] >> 4) * 10) + (bcd_time[0] & 0x0F)
        minute = ((bcd_time[1] >> 4) * 10) + (bcd_time[1] & 0x0F)
        second = ((bcd_time[2] >> 4) * 10) + (bcd_time[2] & 0x0F)
        
        # 简化实现：返回秒数
        return hour * 3600 + minute * 60 + second
```

- [ ] **步骤 5：运行测试验证通过**

```bash
pytest tests/test_tdt.py -v
```

预期：PASS

- [ ] **步骤 6：提交**

```bash
git add src/dvb_parser/si/tdt.py src/dvb_parser/si/models.py tests/test_tdt.py
git commit -m "feat: add TDT/TOT parser with UTC time support"
```

---

## 任务 7：完善包导入

**文件：**
- 修改：`src/dvb_parser/__init__.py`
- 修改：`src/dvb_parser/gse/__init__.py`
- 修改：`src/dvb_parser/mpe/__init__.py`
- 修改：`src/dvb_parser/ule/__init__.py`
- 修改：`src/dvb_parser/nip/__init__.py`
- 修改：`src/dvb_parser/si/__init__.py`

- [ ] **步骤 1：更新 gse/__init__.py**

```python
"""GSE (Generic Stream Encapsulation) parser module"""

from dvb_parser.gse.parser import GSEParser
from dvb_parser.gse.models import GSEPacket

__all__ = [
    "GSEParser",
    "GSEPacket",
]
```

- [ ] **步骤 2：更新 mpe/__init__.py**

```python
"""MPE (Multi-Protocol Encapsulation) parser module"""

from dvb_parser.mpe.parser import MPEParser
from dvb_parser.mpe.models import MPEDatagram

__all__ = [
    "MPEParser",
    "MPEDatagram",
]
```

- [ ] **步骤 3：更新 ule/__init__.py**

```python
"""ULE (Unidirectional Lightweight Encapsulation) parser module"""

from dvb_parser.ule.parser import ULEParser
from dvb_parser.ule.models import ULESNDU

__all__ = [
    "ULEParser",
    "ULESNDU",
]
```

- [ ] **步骤 4：更新 nip/__init__.py**

```python
"""NIP (Network Independent Protocol) parser module"""

from dvb_parser.nip.parser import NIPParser
from dvb_parser.nip.models import NIPDataUnit, NIPStreaming, NIPCarousel

__all__ = [
    "NIPParser",
    "NIPDataUnit",
    "NIPStreaming",
    "NIPCarousel",
]
```

- [ ] **步骤 5：更新 si/__init__.py**

```python
"""SI (Service Information) parser module"""

from dvb_parser.si.sdt import SDTParser
from dvb_parser.si.nit import NITParser
from dvb_parser.si.eit import EITParser
from dvb_parser.si.tdt import TDTParser
from dvb_parser.si.models import (
    SDT, SDTService, NIT, NITTransportStream,
    EIT, EITEvent, TDT, TOT
)

__all__ = [
    "SDTParser",
    "NITParser",
    "EITParser",
    "TDTParser",
    "SDT",
    "SDTService",
    "NIT",
    "NITTransportStream",
    "EIT",
    "EITEvent",
    "TDT",
    "TOT",
]
```

- [ ] **步骤 6：更新 dvb_parser/__init__.py**

```python
"""
DVB Parser - DVB protocol parser for satellite signal analysis
"""

__version__ = "0.3.0"

from dvb_parser.bbframe.parser import BBFrameParser
from dvb_parser.bbframe.models import BBFrame, BBFrameHeader, StreamType
from dvb_parser.ts.parser import TSPacketParser
from dvb_parser.ts.models import TSPacket, AdaptationField
from dvb_parser.psi.pat import PATParser
from dvb_parser.psi.pmt import PMTParser
from dvb_parser.psi.models import PAT, PMT, PATEntry, PMTStream
from dvb_parser.si.sdt import SDTParser
from dvb_parser.si.nit import NITParser
from dvb_parser.si.eit import EITParser
from dvb_parser.si.tdt import TDTParser
from dvb_parser.si.models import (
    SDT, SDTService, NIT, NITTransportStream,
    EIT, EITEvent, TDT, TOT
)
from dvb_parser.pes.parser import PESParser
from dvb_parser.pes.models import (
    PESPacket, PESHeader, ESFrameHeader,
    H264NALUHeader, H265NALUHeader,
    AACADTSHeader, MP3FrameHeader, AC3SyncHeader
)
from dvb_parser.gse.parser import GSEParser
from dvb_parser.gse.models import GSEPacket
from dvb_parser.mpe.parser import MPEParser
from dvb_parser.mpe.models import MPEDatagram
from dvb_parser.ule.parser import ULEParser
from dvb_parser.ule.models import ULESNDU
from dvb_parser.nip.parser import NIPParser
from dvb_parser.nip.models import NIPDataUnit, NIPStreaming, NIPCarousel

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
    "EITParser",
    "TDTParser",
    "SDT",
    "SDTService",
    "NIT",
    "NITTransportStream",
    "EIT",
    "EITEvent",
    "TDT",
    "TOT",
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
    # GSE
    "GSEParser",
    "GSEPacket",
    # MPE
    "MPEParser",
    "MPEDatagram",
    # ULE
    "ULEParser",
    "ULESNDU",
    # NIP
    "NIPParser",
    "NIPDataUnit",
    "NIPStreaming",
    "NIPCarousel",
]
```

- [ ] **步骤 7：运行所有测试**

```bash
pytest -v
```

预期：所有测试通过

- [ ] **步骤 8：提交**

```bash
git add src/dvb_parser/__init__.py src/dvb_parser/gse/__init__.py src/dvb_parser/mpe/__init__.py src/dvb_parser/ule/__init__.py src/dvb_parser/nip/__init__.py src/dvb_parser/si/__init__.py
git commit -m "feat: complete P2 package imports"
```

---

## 任务 8：集成测试

**文件：**
- 修改：`tests/test_integration.py`

- [ ] **步骤 1：添加 P2 集成测试**

```python
# tests/test_integration.py (追加)
from dvb_parser.gse.parser import GSEParser
from dvb_parser.mpe.parser import MPEParser
from dvb_parser.ule.parser import ULEParser
from dvb_parser.nip.parser import NIPParser
from dvb_parser.si.eit import EITParser
from dvb_parser.si.tdt import TDTParser

class TestIntegrationP2:
    def test_gse_with_bbframe(self):
        """测试 GSE 与 BBFrame 关联"""
        # 构造 GSE 数据
        gse_data = bytes([
            0b11000000, 0x00, 0x08, 0x00, 0x00, 0x10,
            0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
            0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
            0x00, 0x00, 0x00, 0x00  # CRC-32 placeholder
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(gse_data[:-4])
        gse_data = gse_data[:-4] + crc_value.to_bytes(4, 'big')
        
        gse = GSEParser.parse(gse_data)
        
        assert gse.is_ipv4 == True
        assert gse.is_complete == True
    
    def test_eit_with_sdt(self):
        """测试 EIT 与 SDT 关联（事件对应节目）"""
        # 构造 EIT 数据
        eit_data = bytes([
            0x4E, 0b10110000, 0x1A,
            0x00, 0x01,  # service_id=1
            0b11000001,  # version=1
            0x00, 0x01, 0x00, 0x01,  # ts_id, original_network_id
            0x00, 0x00,  # section numbers
            0x00, 0x01,  # event_id
            0x58, 0x00,  # MJD
            0x12, 0x00, 0x00,  # 12:00:00
            0x01, 0x30, 0x00,  # 1h30m
            0b00000001, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00  # CRC-32
        ])
        
        from dvb_parser.utils.crc import crc32
        crc_value = crc32(eit_data[:-4])
        eit_data = eit_data[:-4] + crc_value.to_bytes(4, 'big')
        
        eit = EITParser.parse(eit_data)
        
        assert eit.service_id == 1  # 对应 SDT.service_id
        assert len(eit.events) == 1
```

- [ ] **步骤 2：运行集成测试**

```bash
pytest tests/test_integration.py -v
```

预期：PASS

- [ ] **步骤 3：提交**

```bash
git add tests/test_integration.py
git commit -m "test: add P2 integration tests"
```

---

## 任务 9：最终验证

- [ ] **步骤 1：运行完整测试套件**

```bash
pytest -v --cov=src/dvb_parser
```

预期：所有测试通过，覆盖率 > 80%

- [ ] **步骤 2：验证包安装**

```bash
pip install -e .
python -c "from dvb_parser import GSEParser, MPEParser, ULEParser, NIPParser, EITParser, TDTParser; print('Import successful')"
```

预期：Import successful

- [ ] **步骤 3：最终提交**

```bash
git add .
git commit -m "feat: complete P2 expansion - GSE, MPE, ULE, NIP, EIT, TDT parsers"
```

---

## 完成后

P2 扩展完成后，DVB Parser 将支持：

- **P0**: BBFrame, MPEG-TS, PAT, PMT
- **P1**: SDT, NIT, PES
- **P2**: GSE, MPE, ULE, NIP, EIT, TDT

总共 12 个解析器，覆盖 DVB-S2/S2X 卫星信号分析的主要需求。
