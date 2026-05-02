"""
CRC checksum implementations for DVB protocols
"""


def crc8(data: bytes, polynomial: int = 0xD5) -> int:
    """
    Calculate CRC-8 checksum

    Args:
        data: Input data
        polynomial: CRC polynomial (default: 0xD5 for BBFrame)

    Returns:
        CRC-8 value
    """
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ polynomial
            else:
                crc <<= 1
            crc &= 0xFF
    return crc


def crc32(data: bytes) -> int:
    """
    Calculate CRC-32 checksum (CRC-32/ISO-HDLC, reflected)

    Args:
        data: Input data

    Returns:
        CRC-32 value
    """
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1
    return crc ^ 0xFFFFFFFF
