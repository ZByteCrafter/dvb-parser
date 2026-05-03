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
    label_type: int  # 0=无, 1=6字节, 2=3字节, 3=Label Extension
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
