import pytest
from dvb_parser.psi.models import (
    PAT,
    PATEntry,
    PMT,
    PMTStream,
)


class TestPATEntry:
    def test_basic_entry(self):
        entry = PATEntry(program_number=1, pid=0x100)
        assert entry.program_number == 1
        assert entry.pid == 0x100

    def test_network_pid(self):
        entry = PATEntry(program_number=0, pid=0x10)
        assert entry.program_number == 0
        assert entry.pid == 0x10


class TestPAT:
    def _make_pat(self, entries=None):
        if entries is None:
            entries = [
                PATEntry(program_number=0, pid=0x10),
                PATEntry(program_number=1, pid=0x100),
            ]
        return PAT(
            table_id=0x00,
            transport_stream_id=0x0001,
            version_number=1,
            current_next_indicator=True,
            section_number=0,
            last_section_number=0,
            entries=entries,
        )

    def test_table_id(self):
        pat = self._make_pat()
        assert pat.table_id == 0x00

    def test_version_number(self):
        pat = self._make_pat()
        assert pat.version_number == 1

    def test_current_next_indicator(self):
        pat = self._make_pat()
        assert pat.current_next_indicator is True

    def test_section_number(self):
        pat = self._make_pat()
        assert pat.section_number == 0
        assert pat.last_section_number == 0

    def test_programs_property(self):
        pat = self._make_pat()
        programs = pat.programs
        assert programs == {0: 0x10, 1: 0x100}

    def test_programs_empty(self):
        pat = self._make_pat(entries=[])
        assert pat.programs == {}

    def test_programs_single(self):
        pat = self._make_pat(entries=[PATEntry(program_number=5, pid=0x200)])
        assert pat.programs == {5: 0x200}


class TestPMTStream:
    def test_basic_stream(self):
        stream = PMTStream(stream_type=0x1B, pid=0x101, descriptors=[])
        assert stream.stream_type == 0x1B
        assert stream.pid == 0x101
        assert stream.descriptors == []

    def test_with_descriptors(self):
        desc = bytes([0x0A, 0x04, 0x65, 0x6E, 0x67, 0x00])
        stream = PMTStream(stream_type=0x0F, pid=0x102, descriptors=[desc])
        assert len(stream.descriptors) == 1
        assert stream.descriptors[0] == desc


class TestPMT:
    def _make_pmt(self, streams=None):
        if streams is None:
            streams = [
                PMTStream(stream_type=0x1B, pid=0x101, descriptors=[]),
                PMTStream(stream_type=0x0F, pid=0x102, descriptors=[]),
            ]
        return PMT(
            table_id=0x02,
            version_number=1,
            current_next_indicator=True,
            section_number=0,
            last_section_number=0,
            program_number=1,
            pcr_pid=0x101,
            descriptors=[],
            streams=streams,
        )

    def test_table_id(self):
        pmt = self._make_pmt()
        assert pmt.table_id == 0x02

    def test_version_number(self):
        pmt = self._make_pmt()
        assert pmt.version_number == 1

    def test_current_next_indicator(self):
        pmt = self._make_pmt()
        assert pmt.current_next_indicator is True

    def test_section_numbers(self):
        pmt = self._make_pmt()
        assert pmt.section_number == 0
        assert pmt.last_section_number == 0

    def test_program_number(self):
        pmt = self._make_pmt()
        assert pmt.program_number == 1

    def test_pcr_pid(self):
        pmt = self._make_pmt()
        assert pmt.pcr_pid == 0x101

    def test_descriptors_empty(self):
        pmt = self._make_pmt()
        assert pmt.descriptors == []

    def test_descriptors_with_data(self):
        desc = bytes([0x0E, 0x03, 0x01, 0x02, 0x03])
        pmt = PMT(
            table_id=0x02,
            version_number=1,
            current_next_indicator=True,
            section_number=0,
            last_section_number=0,
            program_number=1,
            pcr_pid=0x101,
            descriptors=[desc],
            streams=[],
        )
        assert len(pmt.descriptors) == 1
        assert pmt.descriptors[0] == desc

    def test_streams(self):
        pmt = self._make_pmt()
        assert len(pmt.streams) == 2
        assert pmt.streams[0].stream_type == 0x1B
        assert pmt.streams[0].pid == 0x101
        assert pmt.streams[1].stream_type == 0x0F
        assert pmt.streams[1].pid == 0x102

    def test_streams_empty(self):
        pmt = self._make_pmt(streams=[])
        assert pmt.streams == []
