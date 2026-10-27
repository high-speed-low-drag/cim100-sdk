# cim100-sdk

Python SDK covering all CIM100 classes (1,426 classes, 405 enums, datatypes and compounds), generated
from the CIM UG Enterprise Architect model. In-memory objects only for now (no serialization).

## Install

```
uv sync
uv run pytest -q
uv run ruff check .
```

## Usage

```python
from cim100 import ACLineSegment, Terminal, Substation, VoltageLevel, UnitSymbol, PhaseCode

# Attributes and enums (keyword-only constructors; everything is optional)
line = ACLineSegment(name="L1", length=12.5)
term = Terminal(phases=PhaseCode.ABC, sequence_number=1)
line.name = "Line 1"
assert UnitSymbol.m.value == "m"

# Automatic mRIDs: a random UUID4 string unless you pass mrid=...
assert len(line.mrid) == 36

# Links update both ends
term.conducting_equipment = line
assert line.terminals == (term,)          # many-ends read as a tuple snapshot
term.conducting_equipment = None
assert line.terminals == ()

# Many-end methods: add_, remove_, clear_, num_, get_*_by_mrid
line.add_terminal(term)
assert term.conducting_equipment is line
assert line.num_terminal() == 1
assert line.get_terminal_by_mrid(term.mrid) is term
line.remove_terminal(term)                 # ValueError if absent
line.add_terminal(term).clear_terminals()  # add/remove/clear return self

sub = Substation(name="S1")
vl = VoltageLevel(name="132kV", substation=sub)
assert sub.voltage_levels == (vl,)
```

### validate()

`obj.validate()` returns a list of messages (empty when fine). Only lower bounds are reported;
upper bounds are not checked, and association targets are type-checked on assignment (`TypeError`). Attribute values are not type-checked.

```python
from cim100 import Substation

print(Substation(name="S").validate())
# ["Substation(mrid='...'): required association 'instance_set' is not set"]
```

### Copying

`copy.deepcopy` and `pickle` give a separate, consistent graph (cycles are fine).
`copy.copy` raises `TypeError`, because a shallow copy would share half-links with the original.

## Naming

- Members, methods and modules are snake_case (`sequence_number`, `voltage_levels`).
- The original CIM names are kept in `Class._cim_meta` (`cim_name`, `package`, `guid`, and per
  attribute/end `cim_name` / `cim_role`); use `cim100._runtime.cim_attributes(cls)` for the merged view.
- Renames (keyword escapes, collisions, generated role names) are listed in
  `codegen/snapshot/naming_report.md`.

## Regenerating from the model

The generated package (`src/cim100/model/`) is committed; regenerate only when the generator changes.

```
uv run python tools/fetch_model.py        # download + sha256-check the pinned .qea into build/model/
uv run python tools/dump_ir.py            # read the .qea, write codegen/snapshot/cim100_ir.json
uv run python tools/regen.py              # regenerate src/cim100/model/ and _registry.py
uv run python tools/regen.py --check      # exit 1 if the committed code is out of date
```

Tests run offline from the committed IR snapshot. Never edit generated files; fix `codegen/` instead.

## Known model quirks

- **IdentifiedObject.InstanceSet:** the model has an association `IdentifiedObject.InstanceSet`
  (multiplicity `1`) to `InstanceSet`, where the other end `InstanceSetMember` is `0..*` and neither end
  is navigable in the source. The SDK generates both ends, and since the lower bound is 1, `validate()`
  reports `instance_set` as missing on every IdentifiedObject that is not linked to an `InstanceSet`.
  Filter it out if you do not use `InstanceSet`.
- **`Mass.unit`:** the model gives `Mass.unit` the default `'g'`, but `UnitSymbol` has no `g` literal.
  The default is therefore left as `None`.
- **Duplicate class names:** `Profile` and `ResourceCertification` exist in two packages, and
  `TroubleReportingKind` and `IEC61968CIMVersion` are duplicated within a package. The most referenced
  class is exported at top level (`from cim100 import Profile`); the others are reachable only by module
  path (see the table in `naming_report.md`).

## Source model and license

The model is the CIM100 `.qea` (SQLite) file from `cimug-org/CIMTool`
(`iec61970cim17v40_iec61968cim13v13b_iec62325cim03v17b_CIM100.1.1.1.qea`), pinned by commit SHA and
sha256 in `model-source.toml` (with a mirror in `netbeheernederland/tc57cim`). The file is not committed; it
is fetched at build time. CIMTool is licensed LGPL-2.1; check the upstream license before redistributing
the model or code derived from it.
