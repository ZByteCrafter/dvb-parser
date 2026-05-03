# DVBParser 高层 API 实施计划

> **致自动化代理：** 必须使用子代理驱动开发（推荐）或执行计划子技能来逐任务实施本计划。步骤使用复选框（`- [ ]`）语法进行跟踪。

**目标：** 实现 DVBParser 高层 API，支持自动逐层解析 DVB 协议嵌套结构

**架构：** 新增 `DVBParser` 类作为入口，内部调用现有解析器链，返回 `ParseResult` 结构化结果。支持自动检测输入格式和容错处理。

**技术栈：** Python 3.8+, dataclasses, struct, pytest

---

## 文件结构

```
dvb-parser/
├── src/dvb_parser/
│   ├── __init__.py          # 更新导出
│   ├── parser.py            # 新增 DVBParser 类
│   ├── models.py            # 新增 ParseResult 数据模型
│   └── ... (现有模块)
├── tests/
│   ├── test_parser.py       # 新增 DVBParser 测试
│   └── ... (现有测试)
└── ...
```

---

## 任务 1：ParseResult 数据模型

**文件：**
- 创建：`src/dvb_parser/models.py`

- [ ] **步骤 1：实现 ParseResult 数据模型**

```python
# src/dvb_parser/models.py
"""
DVBParser 数据模型
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from dvb_parser.bbframe.models import BBFrame
from dvb_parser.ts.models import TSPacket
from dvb_parser.psi.models import PAT, PMT
from dvb_parser.si.models import SDT, SDTService, NIT, NITTransportStream, EIT, EITEvent, TDT, TOT
from dvb_parser.pes.models import PESPacket
from dvb_parser.gse.models import GSEPacket
from dvb_parser.mpe.models import MPEDatagram
from dvb_parser.ule.models import ULESNDU


@dataclass
class ParseResult:
    """DVB 解析结果"""
    format: str = ""                         # 检测到的输入格式
    bbframes: List[BBFrame] = field(default_factory=list)
    ts_packets: List[TSPacket] = field(default_factory=list)
    pat: Optional[PAT] = None
    pmts: Dict[int, PMT] = field(default_factory=dict)
    sdt: Optional[SDT] = None
    nit: Optional[NIT] = None
    eit: List[EIT] = field(default_factory=list)
    tdt: Optional[TDT] = None
    pes_packets: List[PESPacket] = field(default_factory=list)
    gse_packets: List[GSEPacket] = field(default_factory=list)
    mpe_datagrams: List[MPEDatagram] = field(default_factory=list)
    ule_sndus: List[ULESNDU] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0
    
    def summary(self) -> str:
        """解析摘要"""
        lines = [
            f"输入格式: {self.format}",
            f"BBFrame: {len(self.bbframes)}",
            f"TS 包: {len(self.ts_packets)}",
            f"PAT: {'是' if self.pat else '否'}",
            f"PMT: {len(self.pmts)}",
            f"SDT: {'是' if self.sdt else '否'}",
            f"NIT: {'是' if self.nit else '否'}",
            f"EIT: {len(self.eit)}",
            f"TDT: {'是' if self.tdt else '否'}",
            f"PES: {len(self.pes_packets)}",
            f"GSE: {len(self.gse_packets)}",
            f"MPE: {len(self.mpe_datagrams)}",
            f"ULE: {len(self.ule_sndus)}",
            f"错误: {len(self.errors)}",
        ]
        return "\n".join(lines)
```

- [ ] **步骤 2：提交**

```bash
git add src/dvb_parser/models.py
git commit -m "feat: add ParseResult data model for DVBParser"
```

---

## 任务 2：DVBParser 核心实现

**文件：**
- 创建：`src/dvb_parser/parser.py`
- 创建：`tests/test_parser.py`

- [ ] **步骤 1：编写 DVBParser 测试**

```python
# tests/test_parser.py
import pytest
from dvb_parser.parser import DVBParser
from dvb_parser.models import ParseResult


class TestDVBParser:
    def test_parse_bbframe_auto_detect(self):
        """测试 BBFrame 格式自动检测"""
        from dvb_parser.bbframe.parser import BBFrameParser
        from dvb_parser.utils.crc import crc8
        
        # 构造 BBFrame 数据
        bb_header = bytes([
            0b00000000, 0b00000000,  # MATYPE (TS mode)
            0x00, 0xBC,              # UPL (188 bytes)
            0x06, 0x18,              # DFL (1560 bits = 195 bytes)
            0x00,                    # SYNC
            0x00, 0x00,              # SYNCD
            0x00                     # CRC-8 placeholder
        ])
        crc_value = crc8(bb_header[:9])
        bb_header = bb_header[:9] + bytes([crc_value])
        
        # TS packet with PAT
        ts_header = bytes([0x47, 0b00000000, 0x00, 0b00010000])
        ts_payload = bytes([0xFF] * 184)
        ts_packet = ts_header + ts_payload
        
        # Fill BBFrame data field
        ts_data = ts_packet * (195 // 188 + 1)
        ts_data = ts_data[:195]
        
        bbframe_data = bb_header + ts_data
        
        parser = DVBParser()
        result = parser.parse(bbframe_data)
        
        assert result.format == "bbframe"
        assert len(result.bbframes) == 1
        assert len(result.ts_packets) > 0
    
    def test_parse_ts_auto_detect(self):
        """测试 TS 格式自动检测"""
        # 构造 TS 数据
        ts_header = bytes([0x47, 0b00000000, 0x00, 0b00010000])
        ts_payload = bytes([0xFF] * 184)
        ts_data = ts_header + ts_payload
        
        parser = DVBParser()
        result = parser.parse(ts_data)
        
        assert result.format == "ts"
        assert len(result.ts_packets) == 1
    
    def test_parse_with_manual_format(self):
        """测试手动指定格式"""
        ts_header = bytes([0x47, 0b00000000, 0x00, 0b00010000])
        ts_payload = bytes([0xFF] * 184)
        ts_data = ts_header + ts_payload
        
        parser = DVBParser()
        result = parser.parse(ts_data, format="ts")
        
        assert result.format == "ts"
        assert len(result.ts_packets) == 1
    
    def test_parse_with_errors(self):
        """测试容错处理"""
        # 构造损坏的 TS 数据
        ts_header = bytes([0x00, 0b00000000, 0x00, 0b00010000])  # 错误的同步字
        ts_payload = bytes([0xFF] * 184)
        ts_data = ts_header + ts_payload
        
        parser = DVBParser()
        result = parser.parse(ts_data, format="ts")
        
        assert result.format == "ts"
        assert len(result.errors) > 0
    
    def test_parse_result_summary(self):
        """测试解析摘要"""
        result = ParseResult(format="ts")
        summary = result.summary()
        
        assert "输入格式: ts" in summary
        assert "BBFrame: 0" in summary
        assert "TS 包: 0" in summary
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/test_parser.py -v
```

预期：FAIL - 模块不存在

- [ ] **步骤 3：实现 DVBParser**

```python
# src/dvb_parser/parser.py
"""
DVBParser 高层 API
"""

from typing import Optional

from dvb_parser.models import ParseResult
from dvb_parser.bbframe.parser import BBFrameParser
from dvb_parser.ts.parser import TSPacketParser
from dvb_parser.psi.pat import PATParser
from dvb_parser.psi.pmt import PMTParser
from dvb_parser.si.sdt import SDTParser
from dvb_parser.si.nit import NITParser
from dvb_parser.si.eit import EITParser
from dvb_parser.si.tdt import TDTParser
from dvb_parser.pes.parser import PESParser
from dvb_parser.gse.parser import GSEParser
from dvb_parser.mpe.parser import MPEParser
from dvb_parser.ule.parser import ULEParser
from dvb_parser.utils.crc import crc8


class DVBParser:
    """DVB 协议自动解析器"""
    
    def parse(self, data: bytes, format: str = "auto") -> ParseResult:
        """
        自动解析 DVB 数据
        
        Args:
            data: 原始二进制数据
            format: 输入格式 ("auto", "bbframe", "ts", "gse", "mpe", "ule")
        
        Returns:
            ParseResult 对象，包含所有解析结果
        
        Raises:
            ValueError: 无法检测输入格式或数据严重损坏
        """
        result = ParseResult()
        
        # 检测或验证输入格式
        if format == "auto":
            format = self._detect_format(data)
        
        result.format = format
        
        # 根据格式调用对应的解析器
        if format == "bbframe":
            self._parse_bbframe(data, result)
        elif format == "ts":
            self._parse_ts(data, result)
        elif format == "gse":
            self._parse_gse(data, result)
        elif format == "mpe":
            self._parse_mpe(data, result)
        elif format == "ule":
            self._parse_ule(data, result)
        else:
            raise ValueError(f"不支持的格式: {format}")
        
        return result
    
    def _detect_format(self, data: bytes) -> str:
        """检测输入格式"""
        if len(data) < 6:
            raise ValueError("数据太短")
        
        # 检测 TS 格式（第一个字节是 0x47）
        if data[0] == 0x47:
            return "ts"
        
        # 检测 BBFrame 格式（前 10 字节 CRC-8 通过）
        if len(data) >= 10:
            if crc8(data[:9]) == data[9]:
                return "bbframe"
        
        # 检测 GSE 格式（前 6 字节符合 GSE 头）
        if len(data) >= 6:
            first_byte = data[0]
            label_type = (first_byte >> 4) & 0x03
            if label_type <= 2:  # 有效的 label_type
                return "gse"
        
        # 检测 MPE 格式（第一个字节是 0x3E）
        if data[0] == 0x3E:
            return "mpe"
        
        # 默认尝试 TS 格式
        return "ts"
    
    def _parse_bbframe(self, data: bytes, result: ParseResult):
        """解析 BBFrame 格式"""
        try:
            bbframes = BBFrameParser.parse_multiple(data)
            result.bbframes = bbframes
            
            for bbframe in bbframes:
                if bbframe.header.is_ts_mode:
                    self._parse_ts(bbframe.data_field, result)
                elif bbframe.header.is_gse_mode:
                    self._parse_gse(bbframe.data_field, result)
        except Exception as e:
            result.errors.append(f"BBFrame 解析错误: {e}")
    
    def _parse_ts(self, data: bytes, result: ParseResult):
        """解析 TS 格式"""
        try:
            ts_packets = TSPacketParser.parse_all(data)
            result.ts_packets.extend(ts_packets)
            
            # 收集 PMT PID 和 PES PID
            pmt_pids = set()
            pes_pids = set()
            
            for ts in ts_packets:
                try:
                    if ts.pid == 0x0000:  # PAT
                        result.pat = PATParser.parse(ts.payload)
                        # 注册 PMT PID
                        for entry in result.pat.entries:
                            if entry.program_number != 0:
                                pmt_pids.add(entry.pid)
                    elif ts.pid == 0x0011:  # SDT
                        result.sdt = SDTParser.parse(ts.payload)
                    elif ts.pid == 0x0010:  # NIT
                        result.nit = NITParser.parse(ts.payload)
                    elif ts.pid in pmt_pids:  # PMT
                        pmt = PMTParser.parse(ts.payload)
                        result.pmts[pmt.program_number] = pmt
                        # 注册 PES PID
                        for stream in pmt.streams:
                            pes_pids.add(stream.pid)
                    elif ts.pid in pes_pids:  # PES
                        # 需要知道 stream_type，这里简化处理
                        pass
                except Exception as e:
                    result.errors.append(f"TS 包 {ts.pid} 解析错误: {e}")
        except Exception as e:
            result.errors.append(f"TS 解析错误: {e}")
    
    def _parse_gse(self, data: bytes, result: ParseResult):
        """解析 GSE 格式"""
        try:
            gse = GSEParser.parse(data)
            result.gse_packets.append(gse)
        except Exception as e:
            result.errors.append(f"GSE 解析错误: {e}")
    
    def _parse_mpe(self, data: bytes, result: ParseResult):
        """解析 MPE 格式"""
        try:
            mpe = MPEParser.parse(data)
            result.mpe_datagrams.append(mpe)
        except Exception as e:
            result.errors.append(f"MPE 解析错误: {e}")
    
    def _parse_ule(self, data: bytes, result: ParseResult):
        """解析 ULE 格式"""
        try:
            ule = ULEParser.parse(data)
            result.ule_sndus.append(ule)
        except Exception as e:
            result.errors.append(f"ULE 解析错误: {e}")
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/test_parser.py -v
```

预期：PASS

- [ ] **步骤 5：提交**

```bash
git add src/dvb_parser/parser.py tests/test_parser.py
git commit -m "feat: add DVBParser high-level API with auto-detection"
```

---

## 任务 3：完善包导入

**文件：**
- 修改：`src/dvb_parser/__init__.py`

- [ ] **步骤 1：更新 dvb_parser/__init__.py**

```python
"""
DVB Parser - DVB protocol parser for satellite signal analysis
"""

__version__ = "0.4.0"

from dvb_parser.parser import DVBParser
from dvb_parser.models import ParseResult

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
    # High-level API
    "DVBParser",
    "ParseResult",
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

- [ ] **步骤 2：运行所有测试**

```bash
pytest -v
```

预期：所有测试通过

- [ ] **步骤 3：提交**

```bash
git add src/dvb_parser/__init__.py
git commit -m "feat: complete DVBParser package imports, version 0.4.0"
```

---

## 任务 4：集成测试

**文件：**
- 修改：`tests/test_integration.py`

- [ ] **步骤 1：添加 DVBParser 集成测试**

```python
# tests/test_integration.py (追加)
from dvb_parser.parser import DVBParser


class TestDVBParserIntegration:
    def test_full_bbframe_to_si(self):
        """测试完整的 BBFrame → TS → SI 解析链"""
        from dvb_parser.bbframe.parser import BBFrameParser
        from dvb_parser.utils.crc import crc8, crc32
        
        # 构造包含 PAT 的 BBFrame
        bb_header = bytes([
            0b00000000, 0b00000000,  # MATYPE (TS mode)
            0x00, 0xBC,              # UPL (188 bytes)
            0x06, 0x18,              # DFL (1560 bits = 195 bytes)
            0x00,                    # SYNC
            0x00, 0x00,              # SYNCD
            0x00                     # CRC-8 placeholder
        ])
        crc_value = crc8(bb_header[:9])
        bb_header = bb_header[:9] + bytes([crc_value])
        
        # TS packet with PAT
        ts_header = bytes([0x47, 0b00000000, 0x00, 0b00010000])
        
        # PAT payload
        pat_data = bytes([
            0x00,                    # table_id
            0b10110000, 0x0D,        # syntax_indicator=1, length=13
            0x00, 0x01,              # transport_stream_id
            0b11000001,              # version=1, current_next=1
            0x00,                    # section_number
            0x00,                    # last_section_number
            0x00, 0x01,              # program_number=1
            0b11100001, 0x00,        # PID=0x100
        ])
        crc_value = crc32(pat_data)
        pat_data = pat_data + crc_value.to_bytes(4, 'big')
        
        # Pad TS payload
        ts_payload = pat_data + bytes([0xFF] * (184 - len(pat_data)))
        ts_packet = ts_header + ts_payload
        
        # Fill BBFrame data field
        ts_data = ts_packet * (195 // 188 + 1)
        ts_data = ts_data[:195]
        
        bbframe_data = bb_header + ts_data
        
        # 使用 DVBParser 自动解析
        parser = DVBParser()
        result = parser.parse(bbframe_data)
        
        assert result.format == "bbframe"
        assert len(result.bbframes) == 1
        assert len(result.ts_packets) > 0
        assert result.pat is not None
        assert 1 in result.pat.programs
        assert result.pat.programs[1] == 0x100
    
    def test_ts_with_pat(self):
        """测试 TS 格式自动解析 PAT"""
        from dvb_parser.utils.crc import crc32
        
        # 构造包含 PAT 的 TS 数据
        ts_header = bytes([0x47, 0b00000000, 0x00, 0b00010000])
        
        pat_data = bytes([
            0x00,                    # table_id
            0b10110000, 0x0D,        # syntax_indicator=1, length=13
            0x00, 0x01,              # transport_stream_id
            0b11000001,              # version=1, current_next=1
            0x00,                    # section_number
            0x00,                    # last_section_number
            0x00, 0x01,              # program_number=1
            0b11100001, 0x00,        # PID=0x100
        ])
        crc_value = crc32(pat_data)
        pat_data = pat_data + crc_value.to_bytes(4, 'big')
        
        ts_payload = pat_data + bytes([0xFF] * (184 - len(pat_data)))
        ts_data = ts_header + ts_payload
        
        # 使用 DVBParser 自动解析
        parser = DVBParser()
        result = parser.parse(ts_data)
        
        assert result.format == "ts"
        assert len(result.ts_packets) == 1
        assert result.pat is not None
        assert 1 in result.pat.programs
```

- [ ] **步骤 2：运行集成测试**

```bash
pytest tests/test_integration.py -v
```

预期：PASS

- [ ] **步骤 3：提交**

```bash
git add tests/test_integration.py
git commit -m "test: add DVBParser integration tests"
```

---

## 任务 5：最终验证

- [ ] **步骤 1：运行完整测试套件**

```bash
pytest -v --cov=src/dvb_parser
```

预期：所有测试通过，覆盖率 > 80%

- [ ] **步骤 2：验证包安装**

```bash
pip install -e .
python -c "from dvb_parser import DVBParser; print('Import successful')"
```

预期：Import successful

- [ ] **步骤 3：最终提交**

```bash
git add .
git commit -m "feat: complete DVBParser high-level API"
```

---

## 完成后

DVBParser 高层 API 完成后，用户可以：

```python
from dvb_parser import DVBParser

parser = DVBParser()
result = parser.parse(raw_data)

# 自动解析所有层
print(result.summary())
```
