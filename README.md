# cim100-sdk

Python SDK covering all CIM100 classes (1,426 classes, 405 enums, datatypes and compounds), generated
from the CIM UG Enterprise Architect model. Objects live in memory; CIMXML serialization is in `cim100.serialization`.

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

## Serialization (CIMXML and JSON-LD)

`cim100.serialization` writes and reads IEC 61970-552 RDF/XML (CIMXML) and CIM JSON-LD (stdlib
only), generically for every class, driven by `_cim_meta`.

```python
from cim100 import ACLineSegment, Terminal, Substation, PhaseCode
from cim100.serialization import read_cimxml, to_cimxml_string, write_cimxml

sub = Substation(name="Zone Sub", mrid="sub-1")
line = ACLineSegment(name="L1", length=12.5, mrid="line-1", equipment_container=sub)
Terminal(mrid="t-1", sequence_number=1, phases=PhaseCode.ABC, conducting_equipment=line)

print(to_cimxml_string([sub]))             # the roots plus everything reachable (include_reachable=True)
write_cimxml([sub], "network.xml", header={"description": "demo", "version": "1"})

doc = read_cimxml("network.xml")           # CimDocument: .objects .by_id .header .warnings .dangling
line2 = doc.by_id["line-1"]                # keyed by mRID
assert line2.length == 12.5 and line2.terminals[0].phases is PhaseCode.ABC
assert line2.equipment_container is doc.by_id["sub-1"]
```

- Elements are `<cim:ACLineSegment rdf:ID="_<mrid>">`, properties `<cim:Declaring.cimName>` (the CIM
  name of the class that declares them), references `rdf:resource="#_<mrid>"`, enums
  `rdf:resource="<ns>EnumName.literal"`, compounds nested with `rdf:parseType="Resource"`.
- Each association is written once, from its single-valued end (`Terminal.ConductingEquipment`); for
  1:1 and N:M from the end whose `<Owner>.<Role>` sorts first. `write_both_ends=True` writes both.
- Objects without an mRID (for example `PositionPoint`) get `rdf:ID="_gen<N>"`; they are read back
  without an mRID.
- The reader accepts `rdf:ID`, `rdf:about="#_x"` and `urn:uuid:x`, associations on either or both
  ends, and collects unknown classes/properties, bad literals and dangling references in
  `doc.warnings` / `doc.dangling` (`strict=True` raises `CimXmlError` instead).
- Output is deterministic (sorted by CIM class name, then id) and pretty-printed UTF-8.
- The full rules (ids, naming, value encoding, duplicate CIM class names) are in the docstring of
  `cim100/serialization/_common.py`.

### CIM JSON-LD

`write_jsonld`, `to_jsonld_string`, `to_jsonld_dict` and `read_jsonld` take the same arguments
(plus `indent=`) and return the same `CimDocument`; the format follows the DIGIN10 "CIMJSON-LD"
convention. Reading CIMXML and JSON-LD of the same objects gives equal graphs.

```python
from cim100.serialization import read_jsonld, to_jsonld_string, write_jsonld

print(to_jsonld_string([sub]))
# {
#   "@context": {"cim": "http://iec.ch/TC57/CIM100#", "rdf": "...", "md": "...", "xsd": "..."},
#   "@graph": [
#     {"@id": "#_line-1", "@type": "cim:ACLineSegment",
#      "cim:Conductor.length": 12.5,
#      "cim:IdentifiedObject.mRID": "line-1", "cim:IdentifiedObject.name": "L1",
#      "cim:Equipment.EquipmentContainer": {"@id": "#_sub-1"}},
#     {"@id": "#_t-1", "@type": "cim:Terminal", "cim:Terminal.phases": {"@id": "cim:PhaseCode.ABC"},
#      "cim:Terminal.ConductingEquipment": {"@id": "#_line-1"}, ...},
#     ...
#   ]
# }
write_jsonld([sub], "network.jsonld", header={"description": "demo", "version": "1"})
doc = read_jsonld("network.jsonld")
assert doc.by_id["line-1"].terminals[0].phases is PhaseCode.ABC
```

- `@id` is `urn:uuid:<mrid>` for UUID mRIDs, `#_<percent-encoded mrid>` for any other mRID and the
  blank node `_:gen<N>` for objects without one. Enums are `{"@id": "cim:Enum.literal"}`,
  compounds nested objects without `@id`, many-ends arrays of `{"@id": ...}`, `Decimal` a string,
  datetimes typed `xsd` literals, and NaN/INF `{"@value": "NaN", "@type": "xsd:double"}`.
- A header becomes the DIGIN dataset description (`dcat:Dataset`, `prov:generatedAtTime`,
  `dcterms:description`, ...) next to `@graph`.
- The reader takes `@graph` or a top-level array, `urn:uuid:x`, `_x`, `#_x` and compact IRIs as ids,
  and properties without `cim:` when the context has an `@vocab`.
- The module docstring of `cim100/serialization/jsonld.py` lists which conventions are from the
  spec and which are inferred.
- In CIMXML, strings with XML-invalid control characters raise `ValueError` when written (JSON-LD
  can carry them); an mRID that is not a valid XML name (for example `a#b`) is written
  `rdf:about="#_a%23b"`.
- A writer emits one `warnings.warn` per association end that has no CIM role in the model (it is
  then written under its generated Python name, which is not standard CIM).

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
