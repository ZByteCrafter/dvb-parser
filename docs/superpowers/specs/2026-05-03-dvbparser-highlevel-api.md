# DVBParser 高层 API 设计规范

**日期**: 2026-05-03
**状态**: 草稿
**作者**: AI Assistant

## 1. 概述

### 1.1 目标

新增一个高层 API `DVBParser`，支持自动逐层解析 DVB 协议嵌套结构。用户只需传入原始二进制数据，即可自动获得所有层的解析结果。

### 1.2 核心需求

- **自动检测输入格式**：支持 BBFrame、TS、GSE、MPE、ULE 等多种输入格式
- **自动逐层解析**：根据输入格式自动调用对应的解析器链
- **容错模式**：遇到损坏的包时跳过并记录警告，继续解析后续数据
- **结构化输出**：返回 `ParseResult` 对象，包含所有解析结果

### 1.3 使用场景

- 离线数据分析：解析卫星接收机输出的二进制文件
- 协议分析：查看 DVB 流中的节目信息、传输参数等
- 调试工具：快速验证 DVB 数据的正确性

## 2. API 设计

### 2.1 DVBParser 类

```python
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
```

### 2.2 ParseResult 数据模型

```python
@dataclass
class ParseResult:
    """解析结果"""
    format: str                    # 检测到的输入格式
    bbframes: List[BBFrame]        # BBFrame 列表（如果有）
    ts_packets: List[TSPacket]     # TS 包列表（如果有）
    pat: Optional[PAT]             # PAT 表
    pmts: Dict[int, PMT]           # program_number → PMT
    sdt: Optional[SDT]             # SDT 表
    nit: Optional[NIT]             # NIT 表
    eit: List[EIT]                 # EIT 列表
    tdt: Optional[TDT]             # TDT 表
    pes_packets: List[PESPacket]   # PES 包列表
    gse_packets: List[GSEPacket]   # GSE 包列表（如果有）
    mpe_datagrams: List[MPEDatagram]  # MPE 数据报（如果有）
    ule_sndus: List[ULESNDU]       # ULE SNDU（如果有）
    errors: List[str]              # 错误/警告信息
```

### 2.3 使用示例

```python
from dvb_parser import DVBParser

parser = DVBParser()

# 自动检测格式
result = parser.parse(raw_data)

# 手动指定格式
result = parser.parse(ts_data, format="ts")

# 访问解析结果
print(f"输入格式: {result.format}")
print(f"BBFrame 数量: {len(result.bbframes)}")
print(f"TS 包数量: {len(result.ts_packets)}")

if result.pat:
    print(f"节目列表: {result.pat.programs}")

if result.sdt:
    for service in result.sdt.services:
        print(f"节目 {service.service_id}: {service.service_name}")

if result.nit:
    print(f"网络名称: {result.nit.network_name}")
    for ts in result.nit.transport_streams:
        print(f"  频率: {ts.frequency} Hz")

if result.errors:
    print(f"警告: {len(result.errors)} 个")
```

## 3. 输入格式自动检测

### 3.1 检测逻辑

```
输入数据
    │
    ├─ 第一个字节是 0x47？ ──→ TS 格式
    │
    ├─ 前 10 字节 CRC-8 通过？ ──→ BBFrame 格式
    │
    ├─ 前 6 字节符合 GSE 头？ ──→ GSE 格式
    │
    ├─ 第一个字节是 0x3E？ ──→ MPE 格式
    │
    └─ 默认 ──→ 尝试 TS 格式
```

### 3.2 检测实现

```python
def _detect_format(self, data: bytes) -> str:
    """检测输入格式"""
    if len(data) < 6:
        raise ValueError("数据太短")
    
    # 检测 TS 格式（第一个字节是 0x47）
    if data[0] == 0x47:
        return "ts"
    
    # 检测 BBFrame 格式（前 10 字节 CRC-8 通过）
    if len(data) >= 10:
        from dvb_parser.utils.crc import crc8
        if crc8(data[:9]) == data[9]:
            return "bbframe"
    
    # 检测 GSE 格式（前 6 字节符合 GSE 头）
    if len(data) >= 6:
        first_byte = data[0]
        start = bool(first_byte & 0x80)
        end = bool(first_byte & 0x40)
        label_type = (first_byte >> 4) & 0x03
        if label_type <= 2:  # 有效的 label_type
            return "gse"
    
    # 检测 MPE 格式（第一个字节是 0x3E）
    if data[0] == 0x3E:
        return "mpe"
    
    # 默认尝试 TS 格式
    return "ts"
```

## 4. 解析流程

### 4.1 BBFrame 输入

```
BBFrame 数据
    │
    ├─ BBFrameParser.parse_multiple(data) → List[BBFrame]
    │
    └─ 对每个 BBFrame:
        ├─ 如果是 TS 模式:
        │   └─ TSPacketParser.parse_all(bbframe.data_field) → List[TSPacket]
        │       └─ 对每个 TSPacket:
        │           ├─ PID=0x0000 → PATParser.parse(payload)
        │           ├─ PID=0x0011 → SDTParser.parse(payload)
        │           ├─ PID=0x0010 → NITParser.parse(payload)
        │           ├─ PID 在 PMT PID 列表中 → PMTParser.parse(payload)
        │           ├─ PID 在 PES PID 列表中 → PESParser.parse(payload)
        │           └─ 其他 PID → 记录但不解析
        │
        └─ 如果是 GSE 模式:
            └─ GSEParser.parse(bbframe.data_field) → GSEPacket
```

### 4.2 TS 输入

```
TS 数据
    │
    ├─ TSPacketParser.parse_all(data) → List[TSPacket]
    │
    └─ 对每个 TSPacket:
        ├─ PID=0x0000 → PATParser.parse(payload)
        ├─ PID=0x0011 → SDTParser.parse(payload)
        ├─ PID=0x0010 → NITParser.parse(payload)
        ├─ PID 在 PMT PID 列表中 → PMTParser.parse(payload)
        ├─ PID 在 PES PID 列表中 → PESParser.parse(payload)
        └─ 其他 PID → 记录但不解析
```

### 4.3 GSE 输入

```
GSE 数据
    │
    └─ GSEParser.parse(data) → GSEPacket
```

### 4.4 MPE 输入

```
MPE 数据
    │
    └─ MPEParser.parse(data) → MPEDatagram
```

### 4.5 ULE 输入

```
ULE 数据
    │
    └─ ULEParser.parse(data) → ULESNDU
```

## 5. 容错处理

### 5.1 错误类型

| 错误类型 | 处理方式 |
|----------|----------|
| CRC-8 校验失败 | 跳过该 BBFrame，记录警告 |
| CRC-32 校验失败 | 跳过该 Section，记录警告 |
| 同步字错误 | 跳过该 TS 包，记录警告 |
| 数据不足 | 跳过剩余数据，记录警告 |
| 未知表类型 | 跳过该 Section，记录警告 |

### 5.2 错误收集

```python
@dataclass
class ParseResult:
    # ... 其他字段 ...
    errors: List[str]  # 错误/警告信息

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

## 6. 项目结构更新

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

## 7. 测试策略

### 7.1 单元测试

```python
class TestDVBParser:
    def test_parse_bbframe_auto_detect(self):
        """测试 BBFrame 格式自动检测"""
    
    def test_parse_ts_auto_detect(self):
        """测试 TS 格式自动检测"""
    
    def test_parse_gse_auto_detect(self):
        """测试 GSE 格式自动检测"""
    
    def test_parse_with_manual_format(self):
        """测试手动指定格式"""
    
    def test_parse_with_errors(self):
        """测试容错处理"""
    
    def test_parse_result_summary(self):
        """测试解析摘要"""
```

### 7.2 集成测试

```python
class TestDVBParserIntegration:
    def test_full_bbframe_to_si(self):
        """测试完整的 BBFrame → TS → SI 解析链"""
    
    def test_real_world_data(self):
        """测试真实世界数据（如果有测试数据）"""
```

## 8. 未来扩展

- **流式处理**：支持连续数据流输入
- **事件驱动**：解析时触发回调
- **过滤器**：只解析指定的表类型
- **性能优化**：批量解析、并行处理
