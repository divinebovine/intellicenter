# IntelliCenter Integration Documentation

This directory contains technical documentation for the Pentair IntelliCenter Home Assistant integration.

## Documentation Index

### Project Documentation

#### [CHANGELOG.md](./CHANGELOG.md)
Version history and release notes for the integration.

#### [TESTING.md](./TESTING.md)
Comprehensive testing guide including:
- Test framework setup
- Running tests
- Coverage reports
- CI/CD integration

#### [QUALITY_SCALE_COMPLIANCE.md](./QUALITY_SCALE_COMPLIANCE.md)
Home Assistant Quality Scale compliance tracking (current: Gold ✅).

#### [VALIDATION.md](./VALIDATION.md)
Validation checklist and compliance verification.

#### [info.md](./info.md)
HACS integration metadata and information.

---

### Implementation Guides

#### [Valve Control Implementation](./valve-control-implementation.md)
**Status:** Ready for Implementation
**Date:** 2025-01-15

Complete guide for implementing valve control using Home Assistant Select entities.

**Contents:**
- Live system analysis from IntelliCenter @ 10.100.11.60
- Protocol specification and JSON examples
- Step-by-step implementation guide
- Complete code with unit tests
- Testing strategy
- Future enhancement roadmap

**Quick Start:**
```bash
# Review the valve data
cat docs/valve_objects.json

# Run the exploration script
python3 docs/explore_valves.py 10.100.11.60

# Follow implementation in valve-control-implementation.md
```

#### [Valve Findings Summary](./VALVE_FINDINGS_SUMMARY.md)
**Status:** Executive Summary
**Date:** 2025-01-15

Quick reference guide for valve control implementation findings.

---

## Supporting Files

### Live System Data

#### `valve_objects.json`
Raw JSON dump of all valve objects discovered in the live system.

**Contents:**
- 4 VALVE objects with complete attribute sets
- All 81 objects from the IntelliCenter system
- Metadata about object types and counts

**Usage:**
```python
import json

with open('docs/valve_objects.json') as f:
    data = json.load(f)

print(f"Found {data['valve_count']} valves")
for valve in data['valves']:
    print(f"  {valve['objnam']}: {valve['params']['SNAME']} = {valve['params']['ASSIGN']}")
```

### Exploration Tools

#### `explore_valves.py`
Python script to connect to a live IntelliCenter system and extract valve information.

**Usage:**
```bash
# Connect to IntelliCenter and discover valves
python3 explore_valves.py <ip_address>

# Example
python3 explore_valves.py 10.100.11.60

# Output
# - Console: Formatted valve information
# - File: valve_objects.json (all discovered objects)
```

**Features:**
- Connects via TCP to IntelliCenter (port 6681)
- Sends GetParamList command
- Filters for VALVE object types
- Saves complete JSON for analysis
- Reports all object types found in system

---

## Development Status

### Completed Features

- ✅ **Bronze Quality Scale** - Basic integration, config flow, tests
- ✅ **Silver Quality Scale** - Error handling, documentation
- ✅ **Gold Quality Scale** - Zeroconf, diagnostics, 59 tests
- ✅ **Valve Analysis** - Protocol verified, live system tested

### Planned Features

- ⏳ **Valve Control** - Select entity implementation (ready to code)
- ⏳ **Platinum Quality Scale** - Type annotations, code comments
- ⏳ **Extended Coverage** - Additional equipment types

---

## Contributing

When adding new documentation:

1. **Create markdown files** in this directory
2. **Update this README** with links to new docs
3. **Follow the template** from valve-control-implementation.md:
   - Executive summary
   - Live system analysis
   - Protocol specification
   - Implementation guide
   - Testing strategy
   - Future enhancements
4. **Include code examples** that are copy-paste ready
5. **Document real data** from live systems when possible

### Documentation Standards

- Use clear, descriptive headings
- Include table of contents for long documents
- Provide code examples in fenced code blocks
- Specify file paths relative to repository root
- Include version and date information
- Link to related files and documentation

---

## Research Tools

### IntelliCenter Protocol Explorer

The `explore_valves.py` script can be adapted for exploring other object types:

```python
# Modify line 76 to filter for different object types
if objtyp == "VALVE":  # Change to "PUMP", "CIRCUIT", etc.
```

### Quick Analysis Commands

```bash
# Count object types in live system
jq '.all_objects[].params.OBJTYP' docs/valve_objects.json | sort | uniq -c

# Find all objects with specific attribute
jq '.all_objects[] | select(.params.ASSIGN != null)' docs/valve_objects.json

# List all valve names
jq -r '.valves[].params.SNAME' docs/valve_objects.json
```

---

## References

### External Documentation

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Home Assistant Quality Scale](https://www.home-assistant.io/docs/quality_scale/)
- [IntelliCenter Product Page](https://www.pentair.com/en-us/products/residential/pool-spa-equipment/pool-automation/intellicenter.html)

### Related Projects

- [Original Integration](https://github.com/dwradcliffe/intellicenter)
- [HACS](https://hacs.xyz/)
- [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component)

---

## File Organization

```
docs/
├── README.md                           # This file
├── valve-control-implementation.md     # Valve implementation guide
├── valve_objects.json                  # Live system data
├── explore_valves.py                   # Exploration script
└── VALVE_IMPLEMENTATION_ANALYSIS.md    # Original analysis (deprecated, see valve-control-implementation.md)
```

---

**Last Updated:** 2025-01-15
**Integration Version:** 2.2.0 (Gold Quality Scale)
**Maintained By:** joyfulhouse/intellicenter
