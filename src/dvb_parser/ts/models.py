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