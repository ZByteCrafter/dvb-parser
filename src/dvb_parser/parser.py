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

        if format == "auto":
            format = self._detect_format(data)

        result.format = format

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

        if data[0] == 0x47:
            return "ts"

        if len(data) >= 10:
            if crc8(data[:9]) == data[9]:
                return "bbframe"

        if len(data) >= 6:
            first_byte = data[0]
            label_type = (first_byte >> 4) & 0x03
            if label_type <= 2:
                return "gse"

        if data[0] == 0x3E:
            return "mpe"

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

            if len(ts_packets) == 0 and len(data) > 0:
                result.errors.append("未找到有效的 TS 包")

            pmt_pids = set()
            pes_pids = set()

            for ts in ts_packets:
                try:
                    if ts.pid == 0x0000:  # PAT
                        result.pat = PATParser.parse(ts.payload)
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
                        for stream in pmt.streams:
                            pes_pids.add(stream.pid)
                    elif ts.pid in pes_pids:
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
