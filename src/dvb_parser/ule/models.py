"""ULE data models"""

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
