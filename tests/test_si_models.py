import pytest
from dvb_parser.si.models import (
    SDT,
    SDTService,
    NIT,
    NITTransportStream,
)


class TestSDTService:
    def test_basic_service(self):
        service = SDTService(
            service_id=1,
            eit_schedule_flag=True,
            eit_present_following_flag=False,
            running_status=4,
            free_ca_mode=False,
            descriptors=[],
        )
        assert service.service_id == 1
        assert service.eit_schedule_flag is True
        assert service.eit_present_following_flag is False
        assert service.running_status == 4
        assert service.free_ca_mode is False
        assert service.descriptors == []

    def test_default_fields(self):
        service = SDTService(
            service_id=1,
            eit_schedule_flag=True,
            eit_present_following_flag=False,
            running_status=4,
            free_ca_mode=False,
            descriptors=[],
        )
        assert service.service_type == 0
        assert service.service_name == ""
        assert service.provider_name == ""

    def test_with_descriptor_fields(self):
        service = SDTService(
            service_id=1,
            eit_schedule_flag=True,
            eit_present_following_flag=False,
            running_status=4,
            free_ca_mode=False,
            descriptors=[],
            service_type=0x01,
            service_name="BBC One",
            provider_name="BBC",
        )
        assert service.service_type == 0x01
        assert service.service_name == "BBC One"
        assert service.provider_name == "BBC"

    def test_with_descriptors(self):
        desc = bytes([0x48, 0x12, 0x01, 0x05, 0x65, 0x6E, 0x67])
        service = SDTService(
            service_id=1,
            eit_schedule_flag=True,
            eit_present_following_flag=False,
            running_status=4,
            free_ca_mode=False,
            descriptors=[desc],
        )
        assert len(service.descriptors) == 1
        assert service.descriptors[0] == desc


class TestSDT:
    def _make_sdt(self, services=None):
        if services is None:
            services = [
                SDTService(
                    service_id=1,
                    eit_schedule_flag=True,
                    eit_present_following_flag=False,
                    running_status=4,
                    free_ca_mode=False,
                    descriptors=[],
                ),
            ]
        return SDT(
            table_id=0x42,
            transport_stream_id=0x0001,
            original_network_id=0x0001,
            version_number=1,
            current_next_indicator=True,
            section_number=0,
            last_section_number=0,
            services=services,
        )

    def test_table_id(self):
        sdt = self._make_sdt()
        assert sdt.table_id == 0x42

    def test_transport_stream_id(self):
        sdt = self._make_sdt()
        assert sdt.transport_stream_id == 0x0001

    def test_original_network_id(self):
        sdt = self._make_sdt()
        assert sdt.original_network_id == 0x0001

    def test_version_number(self):
        sdt = self._make_sdt()
        assert sdt.version_number == 1

    def test_current_next_indicator(self):
        sdt = self._make_sdt()
        assert sdt.current_next_indicator is True

    def test_section_numbers(self):
        sdt = self._make_sdt()
        assert sdt.section_number == 0
        assert sdt.last_section_number == 0

    def test_services(self):
        sdt = self._make_sdt()
        assert len(sdt.services) == 1
        assert sdt.services[0].service_id == 1

    def test_services_empty(self):
        sdt = self._make_sdt(services=[])
        assert sdt.services == []

    def test_multiple_services(self):
        services = [
            SDTService(
                service_id=1,
                eit_schedule_flag=True,
                eit_present_following_flag=False,
                running_status=4,
                free_ca_mode=False,
                descriptors=[],
            ),
            SDTService(
                service_id=2,
                eit_schedule_flag=False,
                eit_present_following_flag=True,
                running_status=4,
                free_ca_mode=False,
                descriptors=[],
            ),
        ]
        sdt = self._make_sdt(services=services)
        assert len(sdt.services) == 2
        assert sdt.services[0].service_id == 1
        assert sdt.services[1].service_id == 2


class TestNITTransportStream:
    def test_basic_stream(self):
        stream = NITTransportStream(
            transport_stream_id=0x0001,
            original_network_id=0x0001,
            descriptors=[],
        )
        assert stream.transport_stream_id == 0x0001
        assert stream.original_network_id == 0x0001
        assert stream.descriptors == []

    def test_default_fields(self):
        stream = NITTransportStream(
            transport_stream_id=0x0001,
            original_network_id=0x0001,
            descriptors=[],
        )
        assert stream.frequency == 0
        assert stream.modulation == 0
        assert stream.symbol_rate == 0
        assert stream.polarization == 0

    def test_with_descriptor_fields(self):
        stream = NITTransportStream(
            transport_stream_id=0x0001,
            original_network_id=0x0001,
            descriptors=[],
            frequency=11700000000,
            modulation=0x05,
            symbol_rate=27500000,
            polarization=0x01,
        )
        assert stream.frequency == 11700000000
        assert stream.modulation == 0x05
        assert stream.symbol_rate == 27500000
        assert stream.polarization == 0x01

    def test_with_descriptors(self):
        desc = bytes([0x43, 0x08, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])
        stream = NITTransportStream(
            transport_stream_id=0x0001,
            original_network_id=0x0001,
            descriptors=[desc],
        )
        assert len(stream.descriptors) == 1
        assert stream.descriptors[0] == desc


class TestNIT:
    def _make_nit(self, transport_streams=None):
        if transport_streams is None:
            transport_streams = [
                NITTransportStream(
                    transport_stream_id=0x0001,
                    original_network_id=0x0001,
                    descriptors=[],
                ),
            ]
        return NIT(
            table_id=0x40,
            network_id=0x0001,
            version_number=1,
            current_next_indicator=True,
            section_number=0,
            last_section_number=0,
            network_name="Test Network",
            transport_streams=transport_streams,
        )

    def test_table_id(self):
        nit = self._make_nit()
        assert nit.table_id == 0x40

    def test_network_id(self):
        nit = self._make_nit()
        assert nit.network_id == 0x0001

    def test_version_number(self):
        nit = self._make_nit()
        assert nit.version_number == 1

    def test_current_next_indicator(self):
        nit = self._make_nit()
        assert nit.current_next_indicator is True

    def test_section_numbers(self):
        nit = self._make_nit()
        assert nit.section_number == 0
        assert nit.last_section_number == 0

    def test_network_name(self):
        nit = self._make_nit()
        assert nit.network_name == "Test Network"

    def test_transport_streams(self):
        nit = self._make_nit()
        assert len(nit.transport_streams) == 1
        assert nit.transport_streams[0].transport_stream_id == 0x0001

    def test_transport_streams_empty(self):
        nit = self._make_nit(transport_streams=[])
        assert nit.transport_streams == []

    def test_multiple_transport_streams(self):
        streams = [
            NITTransportStream(
                transport_stream_id=0x0001,
                original_network_id=0x0001,
                descriptors=[],
            ),
            NITTransportStream(
                transport_stream_id=0x0002,
                original_network_id=0x0001,
                descriptors=[],
            ),
        ]
        nit = self._make_nit(transport_streams=streams)
        assert len(nit.transport_streams) == 2
        assert nit.transport_streams[0].transport_stream_id == 0x0001
        assert nit.transport_streams[1].transport_stream_id == 0x0002
