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
        return self.mac_address == b'\xff\xff\xff\xff\xff\xff'
    
    @property
    def is_multicast(self) -> bool:
        """是否为组播地址"""
        return (self.mac_address[0] == 0x01 and 
                self.mac_address[1] == 0x00 and 
                self.mac_address[2] == 0x5E)
