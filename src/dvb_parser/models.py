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
