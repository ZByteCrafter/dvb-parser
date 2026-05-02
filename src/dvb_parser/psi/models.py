"""
PSI data models
"""

from dataclasses import dataclass
from typing import List


@dataclass
class PATEntry:
    """PAT entry"""
    program_number: int
    pid: int  # PMT PID or network PID


@dataclass
class PAT:
    """Program Association Table"""
    table_id: int
    version_number: int
    current_next_indicator: bool
    section_number: int
    last_section_number: int
    entries: List[PATEntry]

    @property
    def programs(self) -> dict:
        """Get program number to PMT PID mapping"""
        return {entry.program_number: entry.pid for entry in self.entries}


@dataclass
class PMTStream:
    """PMT stream entry"""
    stream_type: int
    pid: int
    descriptors: List[bytes]


@dataclass
class PMT:
    """Program Map Table"""
    table_id: int
    version_number: int
    current_next_indicator: bool
    section_number: int
    last_section_number: int
    program_number: int
    pcr_pid: int
    descriptors: List[bytes]
    streams: List[PMTStream]
