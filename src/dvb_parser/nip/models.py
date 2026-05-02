"""NIP data models"""

from dataclasses import dataclass
from typing import List


@dataclass
class NIPDataUnit:
    """NIP 数据单元"""
    method: str  # "piping", "streaming", "carousel", "object_carousel"
    payload: bytes


@dataclass
class NIPStreaming:
    """NIP 数据流"""
    synchronous: bool
    data_identifier: int
    payload: bytes


@dataclass
class NIPCarousel:
    """NIP 数据循环"""
    download_id: int
    block_size: int
    blocks: List[bytes]
