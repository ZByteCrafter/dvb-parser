# DVB Parser

A Python library for parsing DVB (Digital Video Broadcasting) protocol formats, focusing on DVB-S2/S2X satellite signal analysis.

## Features

### High-Level API (v0.4.0)

- **DVBParser** - Automatic DVB protocol parser with format auto-detection
  - Auto-detect input format (BBFrame, TS, GSE, MPE, ULE)
  - Automatic multi-layer parsing (BBFrame → TS → PSI/SI)
  - Fault-tolerant mode (skip corrupted packets, collect errors)
  - Structured output with `ParseResult` object

### Core Parsers (P0)

- **BBFrame Parser** - Parse DVB-S2/S2X Baseband Frame headers (MATYPE, UPL, DFL, CRC-8)
- **MPEG-TS Parser** - Parse 188/204/208 byte Transport Stream packets with adaptation field support
- **PAT Parser** - Parse Program Association Table (program_number → PMT PID mapping)
- **PMT Parser** - Parse Program Map Table (stream_type → ES PID mapping)

### Service Information Parsers (P1)

- **SDT Parser** - Parse Service Description Table (service names, providers, service types)
- **NIT Parser** - Parse Network Information Table (frequency, modulation, symbol rate)
- **PES Parser** - Parse Packetized Elementary Stream headers (PTS/DTS) with ES frame header support:
  - H.264 (NALU Header)
  - H.265 (NALU Header)
  - AAC (ADTS Header)
  - MP3 (Frame Header)
  - AC3/E-AC3 (Sync Header)

### Protocol Parsers (P2)

- **GSE Parser** - Parse Generic Stream Encapsulation (IP datagrams, fragmentation)
- **MPE Parser** - Parse Multi-Protocol Encapsulation (MAC addresses, IP datagrams)
- **ULE Parser** - Parse Unidirectional Lightweight Encapsulation (RFC 4326, Type/Length modes)
- **NIP Parser** - Parse Network Independent Protocol (data piping, streaming, carousel)
- **EIT Parser** - Parse Event Information Table (EPG data, event schedules)
- **TDT/TOT Parser** - Parse Time and Date Table / Time Offset Table (UTC time)

## Installation

```bash
pip install -e .
```

## Quick Start

### Automatic Parsing (Recommended)

```python
from dvb_parser import DVBParser

# Create parser
parser = DVBParser()

# Auto-detect format and parse all layers
result = parser.parse(raw_data)

# Access results
print(result.summary())
print(f"Format: {result.format}")
print(f"BBFrames: {len(result.bbframes)}")
print(f"TS packets: {len(result.ts_packets)}")

# Access PSI/SI tables
if result.pat:
    print(f"Programs: {result.pat.programs}")

if result.sdt:
    for service in result.sdt.services:
        print(f"Service {service.service_id}: {service.service_name}")

if result.nit:
    print(f"Network: {result.nit.network_name}")
    for ts in result.nit.transport_streams:
        print(f"  Frequency: {ts.frequency} Hz")
```

### Manual Parsing (Advanced)

#### Parse BBFrame and Extract TS Packets

```python
from dvb_parser import BBFrameParser, TSPacketParser

# Parse BBFrame
bbframe = BBFrameParser.parse(data)
print(f"Stream type: {bbframe.header.stream_type}")
print(f"Data field length: {bbframe.header.dfl} bits")

# Extract TS packets
ts_packets = TSPacketParser.parse_all(bbframe.data_field)
print(f"TS packets: {len(ts_packets)}")
```

#### Parse PSI/SI Tables

```python
from dvb_parser import PATParser, PMTParser, SDTParser, NITParser

# Parse PAT
pat = PATParser.parse(ts_packets[0].payload)
print(f"Programs: {pat.programs}")

# Parse PMT
pmt = PMTParser.parse(ts_packets, pid=pat.programs[1].pmt_pid)
for stream in pmt.streams:
    print(f"Stream type: {stream.stream_type}, PID: {stream.pid}")

# Parse SDT
sdt = SDTParser.parse(sdt_data)
for service in sdt.services:
    print(f"Service {service.service_id}: {service.service_name}")

# Parse NIT
nit = NITParser.parse(nit_data)
for ts in nit.transport_streams:
    print(f"Frequency: {ts.frequency} Hz, Symbol rate: {ts.symbol_rate} sym/s")
```

#### Parse PES with ES Frame Headers

```python
from dvb_parser import PESParser

# Parse PES packet
pes = PESParser.parse(pes_data, stream_type=0x1B)  # H.264
print(f"PTS: {pes.header.pts}")
print(f"Codec: {pes.es_frame_header.codec}")
```

#### Parse Protocol Encapsulations

```python
from dvb_parser import GSEParser, MPEParser, ULEParser

# Parse GSE
gse = GSEParser.parse(gse_data)
if gse.is_ipv4:
    print(f"IPv4 datagram: {len(gse.payload)} bytes")

# Parse MPE
mpe = MPEParser.parse(mpe_data)
print(f"MAC: {mpe.mac_address_str}")

# Parse ULE
sndu = ULEParser.parse(sndu_data)
if sndu.is_ipv4:
    print(f"IPv4 datagram: {len(sndu.payload)} bytes")
```

#### Parse EPG Data

```python
from dvb_parser import EITParser, TDTParser

# Parse EIT
eit = EITParser.parse(eit_data)
for event in eit.events:
    print(f"Event: {event.event_name}, Duration: {event.duration}s")

# Parse TDT
tdt = TDTParser.parse(tdt_data)
print(f"UTC time: {tdt.utc_time}")
```

## Architecture

The library uses a layered parser chain architecture:

```
DVBParser (High-Level API)
├── Format Auto-Detection
└── Parser Chain
    ├── BBFrame Parser
    │   └── TS Packet Parser
    │       ├── PAT Parser
    │       ├── PMT Parser
    │       ├── SDT Parser
    │       ├── NIT Parser
    │       ├── EIT Parser
    │       ├── TDT Parser
    │       ├── PES Parser
    │       │   └── ES Frame Header Parser
    │       ├── MPE Parser
    │       └── ULE Parser
    └── GSE Parser
```

Each parser:
- Returns structured Python objects (dataclasses)
- Can be used independently
- Includes CRC validation
- Supports error handling

## Protocol Support

| Protocol | Standard | Description |
|----------|----------|-------------|
| BBFrame | ETSI EN 302 307-1/2 | DVB-S2/S2X Baseband Frame |
| MPEG-TS | ISO/IEC 13818-1 | Transport Stream (188/204/208 bytes) |
| PAT/PMT | ISO/IEC 13818-1 | Program Specific Information |
| SDT/NIT | ETSI EN 300 468 | Service Information |
| EIT | ETSI EN 300 468 | Event Information Table |
| TDT/TOT | ETSI EN 300 468 | Time and Date Table |
| PES | ISO/IEC 13818-1 | Packetized Elementary Stream |
| GSE | ETSI EN 102 772 | Generic Stream Encapsulation |
| MPE | ETSI EN 301 192 | Multi-Protocol Encapsulation |
| ULE | RFC 4326 | Unidirectional Lightweight Encapsulation |
| NIP | ETSI EN 301 192 | Network Independent Protocol |

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=src/dvb_parser

# Run specific test file
pytest tests/test_bbframe.py -v
```

## Test Coverage

- **Total tests**: 148
- **Coverage**: 88%
- **All tests passing**: ✅

## Project Structure

```
dvb-parser/
├── src/dvb_parser/
│   ├── __init__.py          # Package exports
│   ├── parser.py            # DVBParser high-level API
│   ├── models.py            # ParseResult data model
│   ├── bbframe/             # BBFrame parser
│   ├── ts/                  # MPEG-TS parser
│   ├── psi/                 # PSI parsers (PAT, PMT)
│   ├── si/                  # SI parsers (SDT, NIT, EIT, TDT)
│   ├── pes/                 # PES parser
│   ├── gse/                 # GSE parser
│   ├── mpe/                 # MPE parser
│   ├── ule/                 # ULE parser
│   ├── nip/                 # NIP parser
│   └── utils/               # Utility functions (CRC)
├── tests/                   # Test files
├── docs/                    # Documentation
├── pyproject.toml           # Project configuration
└── README.md                # This file
```

## License

MIT
