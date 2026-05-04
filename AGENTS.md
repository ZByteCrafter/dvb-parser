# AGENTS.md

## Project

DVB (Digital Video Broadcasting) protocol parser library. Parses satellite signal data: BBFrame → MPEG-TS → PSI/SI tables, plus GSE/MPE/ULE protocol encapsulations.

## Commands

```bash
# Install (editable)
pip install -e ".[dev]"

# Run all tests
pytest

# Run single test file
pytest tests/test_psi.py -v

# Run single test
pytest tests/test_psi.py::TestPATParser::test_parse_valid_pat -v

# Coverage
pytest --cov=src/dvb_parser

# Lint (CI uses flake8)
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

## Architecture

- **Source layout**: `src/dvb_parser/` (src-layout, setuptools)
- **High-level API**: `DVBParser` in `parser.py` — auto-detects input format, chains parsers
- **Per-protocol subpackages**: `bbframe/`, `ts/`, `psi/`, `si/`, `pes/`, `gse/`, `mpe/`, `ule/`, `nip/`
  - Each has `parser.py` (parse logic) + `models.py` (dataclasses)
- **`utils/crc.py`**: `crc8()` and `crc32()` — used by all parsers for validation
- **`models.py`** (root): `ParseResult` — aggregated result from `DVBParser.parse()`
- **`__init__.py`**: Re-exports everything. Version string lives here AND in `pyproject.toml` — keep both in sync.

## Key conventions

- **Error messages are in Chinese** (e.g., `"数据不足"`, `"CRC-32 校验失败"`). Match existing style when adding new errors.
- **All parsers are static methods** on classes (e.g., `BBFrameParser.parse(data)`). No instance state.
- **Fault-tolerant mode**: `DVBParser` collects errors in `ParseResult.errors` rather than raising. Individual parsers raise `ValueError` on invalid data.
- **Python 3.8+**: No walrus operator, no `match/case`, use `from __future__ import annotations` if needed for typing.
- **No external dependencies** beyond stdlib (`struct`, `dataclasses`, `typing`). CRC is implemented in-house.

## Testing

- **Framework**: pytest, config in `pyproject.toml`
- **Test files**: `tests/test_<module>.py` for parsers, `tests/test_<module>_models.py` for dataclasses
- **Integration tests**: `tests/test_integration.py` — test multi-layer parsing chains
- **Test data**: Constructed inline as bytes literals (no fixture files)
- **CI matrix**: Python 3.8, 3.9, 3.10, 3.11 on ubuntu-latest

## Gotchas

- **TS pointer_field**: PSI sections in TS packets have a `pointer_field` byte before section data. `_parse_ts()` in `parser.py` handles this with `psi_offset = 1 + pointer_field`. Don't skip it.
- **BBFrame `parse()` vs `parse_multiple()`**: `parse()` returns one frame; `padding` field will contain trailing data (including next frames). Use `parse_multiple()` for multi-frame data.
- **PMT program-level vs ES descriptors**: Variable names are `program_descriptors` and `es_descriptors` — don't reuse `descriptors` for both (was a past bug).
- **TS packet sizes**: 188 (standard), 204 (16B FEC), 208 (20B FEC). Payload always ends at byte 188; FEC is separate. `detect_packet_size()` auto-detects by checking sync byte at offsets 188/204/208.
- **PES PID ordering**: PES PIDs are discovered from PMT, so PES packets appearing before their PMT are silently skipped. This is inherent to MPEG-TS.
- **Version sync**: Update version in BOTH `pyproject.toml` and `src/dvb_parser/__init__.py`.
