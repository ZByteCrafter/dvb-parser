"""
SI data models (SDT, NIT, EIT)
"""

from dataclasses import dataclass
from typing import List


@dataclass
class SDTService:
    """SDT service entry"""
    service_id: int
    eit_schedule_flag: bool
    eit_present_following_flag: bool
    running_status: int
    free_ca_mode: bool
    descriptors: List[bytes]
    # Fields parsed from descriptors
    service_type: int = 0
    service_name: str = ""
    provider_name: str = ""


@dataclass
class SDT:
    """Service Description Table"""
    table_id: int
    transport_stream_id: int
    original_network_id: int
    version_number: int
    current_next_indicator: bool
    section_number: int
    last_section_number: int
    services: List[SDTService]


@dataclass
class NITTransportStream:
    """NIT transport stream entry"""
    transport_stream_id: int
    original_network_id: int
    descriptors: List[bytes]
    # Fields parsed from descriptors
    frequency: int = 0  # Hz
    modulation: int = 0  # QPSK, 8PSK, 16APSK, etc.
    symbol_rate: int = 0
    polarization: int = 0  # horizontal/vertical


@dataclass
class NIT:
    """Network Information Table"""
    table_id: int
    network_id: int
    version_number: int
    current_next_indicator: bool
    section_number: int
    last_section_number: int
    network_name: str
    transport_streams: List[NITTransportStream]


@dataclass
class EITEvent:
    """EIT event entry"""
    event_id: int
    start_time: int  # UTC timestamp (seconds since midnight)
    duration: int  # seconds
    running_status: int
    free_ca_mode: bool
    descriptors: List[bytes]
    # Fields parsed from descriptors
    event_name: str = ""
    event_description: str = ""


@dataclass
class EIT:
    """Event Information Table"""
    table_id: int
    service_id: int
    transport_stream_id: int
    original_network_id: int
    version_number: int
    current_next_indicator: bool
    section_number: int
    last_section_number: int
    events: List[EITEvent]
