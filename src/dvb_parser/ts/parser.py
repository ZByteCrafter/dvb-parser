"""MPEG-TS parser."""

from typing import List, Optional

from dvb_parser.ts.models import (
    TSPacket,
    AdaptationField,
    AdaptationFieldControl,
    ScramblingControl,
)


class TSPacketParser:
    """MPEG-TS packet parser."""

    PACKET_SIZE_188 = 188
    PACKET_SIZE_204 = 204
    PACKET_SIZE_208 = 208
    SYNC_BYTE = 0x47

    @staticmethod
    def parse(data: bytes, offset: int = 0, packet_size: int = 188) -> TSPacket:
        """Parse a single TS packet.

        Args:
            data: Raw data
            offset: Start offset
            packet_size: Packet size (188/204/208)

        Returns:
            TSPacket object

        Raises:
            ValueError: Sync byte error or insufficient data
        """
        if len(data) - offset < packet_size:
            raise ValueError("数据不足")

        if data[offset] != TSPacketParser.SYNC_BYTE:
            raise ValueError("同步字错误")

        header = data[offset : offset + 4]

        pid = ((header[1] & 0x1F) << 8) | header[2]
        cc = header[3] & 0x0F
        afc = (header[3] >> 4) & 0x03
        scrambling = (header[3] >> 6) & 0x03

        adaptation_field = None
        payload_offset = offset + 4

        if afc in (
            AdaptationFieldControl.ADAPTATION_ONLY,
            AdaptationFieldControl.ADAPTATION_AND_PAYLOAD,
        ):
            adaptation_field, payload_offset = TSPacketParser._parse_adaptation_field(
                data, payload_offset
            )

        payload = b""
        if afc in (
            AdaptationFieldControl.PAYLOAD_ONLY,
            AdaptationFieldControl.ADAPTATION_AND_PAYLOAD,
        ):
            payload = data[payload_offset : offset + TSPacketParser.PACKET_SIZE_188]

        fec = None
        if packet_size > TSPacketParser.PACKET_SIZE_188:
            fec = data[offset + TSPacketParser.PACKET_SIZE_188 : offset + packet_size]

        return TSPacket(
            pid=pid,
            cc=cc,
            afc=afc,
            scrambling=scrambling,
            adaptation_field=adaptation_field,
            payload=payload,
            fec=fec,
        )

    @staticmethod
    def _parse_adaptation_field(data: bytes, offset: int) -> tuple:
        """Parse adaptation field.

        Returns:
            Tuple of (AdaptationField, new_offset)
        """
        if offset >= len(data):
            return None, offset

        length = data[offset]
        if length == 0:
            return None, offset + 1

        end_offset = offset + 1 + length
        if end_offset > len(data):
            return None, end_offset

        if offset + 1 >= len(data):
            return None, offset + 1

        flags = data[offset + 1]
        discontinuity = bool(flags & 0x80)
        random_access = bool(flags & 0x40)
        priority = bool(flags & 0x20)
        pcr_flag = bool(flags & 0x10)
        opcr_flag = bool(flags & 0x08)
        splicing = bool(flags & 0x04)
        private_data = bool(flags & 0x02)
        extension = bool(flags & 0x01)

        current_offset = offset + 2
        remaining = end_offset - current_offset

        pcr = None
        if pcr_flag and remaining >= 6:
            pcr_bytes = data[current_offset : current_offset + 6]
            pcr = int.from_bytes(pcr_bytes, "big")
            current_offset += 6
            remaining = end_offset - current_offset

        opcr = None
        if opcr_flag and remaining >= 6:
            opcr_bytes = data[current_offset : current_offset + 6]
            opcr = int.from_bytes(opcr_bytes, "big")
            current_offset += 6
            remaining = end_offset - current_offset

        splice_countdown = None
        if splicing and remaining >= 1:
            splice_countdown = data[current_offset]
            current_offset += 1
            remaining = end_offset - current_offset

        private = None
        if private_data and remaining >= 1:
            private_length = data[current_offset]
            current_offset += 1
            remaining = end_offset - current_offset
            if remaining >= private_length:
                private = data[current_offset : current_offset + private_length]
                current_offset += private_length

        adaptation_field = AdaptationField(
            length=length,
            discontinuity_indicator=discontinuity,
            random_access_indicator=random_access,
            elementary_stream_priority_indicator=priority,
            pcr_flag=pcr_flag,
            opcr_flag=opcr_flag,
            splicing_point_flag=splicing,
            transport_private_data_flag=private_data,
            adaptation_field_extension_flag=extension,
            pcr=pcr,
            opcr=opcr,
            splice_countdown=splice_countdown,
            private_data=private,
        )

        return adaptation_field, offset + 1 + length

    @staticmethod
    def detect_packet_size(data: bytes, offset: int = 0) -> int:
        """Detect TS packet size.

        Args:
            data: Raw data
            offset: Start offset

        Returns:
            Detected packet size
        """
        if len(data) - offset < 208:
            return TSPacketParser.PACKET_SIZE_188

        if data[offset + 188] == TSPacketParser.SYNC_BYTE:
            return TSPacketParser.PACKET_SIZE_188

        if data[offset + 204] == TSPacketParser.SYNC_BYTE:
            return TSPacketParser.PACKET_SIZE_204

        if data[offset + 208] == TSPacketParser.SYNC_BYTE:
            return TSPacketParser.PACKET_SIZE_208

        return TSPacketParser.PACKET_SIZE_188

    @staticmethod
    def parse_all(data: bytes, packet_size: int = 0) -> List[TSPacket]:
        """Parse multiple TS packets.

        Args:
            data: Raw data
            packet_size: Packet size (0=auto-detect)

        Returns:
            List of TSPacket objects
        """
        if packet_size == 0:
            packet_size = TSPacketParser.detect_packet_size(data)

        packets = []
        offset = 0

        while offset + packet_size <= len(data):
            try:
                packet = TSPacketParser.parse(data, offset, packet_size)
                packets.append(packet)
            except ValueError:
                pass
            offset += packet_size

        return packets
