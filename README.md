# DVB Parser

A Python library for parsing DVB (Digital Video Broadcasting) protocol formats, focusing on DVB-S2/S2X satellite signal analysis.

## Features

- BBFrame parsing (Baseband Frame)
- MPEG-TS parsing (188/204/208 byte packets)
- PSI/SI table parsing (PAT, PMT, SDT, NIT, etc.)
- PES packet parsing
- GSE, MPE, ULE, NIP parsing (planned)

## Installation

```bash
pip install -e .
```

## Usage

```python
from dvb_parser import BBFrameParser, TSPacketParser

# Parse BBFrame
bbframe = BBFrameParser.parse(data)

# Extract TS packets
ts_packets = TSPacketParser.parse_all(bbframe.data_field)
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
