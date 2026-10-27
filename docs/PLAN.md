# CIM100 Python SDK: plan

Written 2026-10-27 from the planning agent's research. Scope: every CIM100 class can be instantiated in memory. Serialization is out of scope.

## Source model
- **Primary:** `https://raw.githubusercontent.com/cimug-org/CIMTool/2a47a3778963da9389c9d50b91e92439470021e4/CSharpEFTestProject/CSharpEFTestProject/Schema/iec61970cim17v40_iec61968cim13v13b_iec62325cim03v17b_CIM100.1.1.1.qea`
  - 42,663,936 bytes, sha256 `677355eaad0c7a1321788c0301e0e24c66c8567c5560dab8d7788974c98cf710`
  - The repo is LGPL-2.1, but the UML file states public domain / Apache-2.0.
- **Mirror** (Apache-2.0 repo; content identical, bytes differ): `https://raw.githubusercontent.com/netbeheernederland/tc57cim/91d32217c396bbaa379bc29a5e8bc3cda6f17f07/src/data/iec61970cim17v40_iec61968cim13v13b_iec62325cim03v17b_CIM100.1.1.1.qea`
  - sha256 `feb5c3c51b8efc2e66bc917b3f5be43bf1d0e6434cb235da5b486869a5944454`
- **Format:** EA 16 `.qea`, which is SQLite, read with stdlib `sqlite3`.
- **Versions:** IEC61970CIM17v40, IEC61968CIM13v13b, IEC62325CIM03v17b.
- **Caching:** the file goes in `build/model/` (gitignored) and is never committed.

## Expected model contents (scope `Model/TC57CIM`)
| Item | Count |
|---|---|
| Classifiers | 1,947 |
| Plain classes | 1,426 |
| «enumeration» | 405 (3,211 literals) |
| «CIMDatatype» | 56 |
| «Compound» | 50 |
| «Primitive» | 10 |
| Attribute rows | 9,545 (~6,330 non-literal) |
| Associations | 1,356 + 18 aggregations |
| Generalizations | 1,238 |

Packages: 174.

## Parser facts the code must handle
- **Inheritance:** single only.
- **Association ends:** cardinality is always filled in. 33 associations have no role name on one end. Navigability is mostly unspecified, so generate both ends.
- **EA role convention:** `SourceRole`/`SourceCard` describe the property on the *End* class that points back to the Start class. Example: Contingency.ContingencyElement is 0..\* and ContingencyElement.Contingency is 1.
- **Odd cardinalities:** `1..*`, `2..*`, `0..2`, `0..n`, `1..`.
- **Duplicate class names:** Profile and ResourceCertification each appear in two packages. TroubleReportingKind and IEC61968CIMVersion are duplicated within one package.
- **Duplicate member names:** 21 classes, mostly a subclass re-declaring `kind` with a narrower enum, or a repeated role name.
- **Python keywords used as attribute names:** `and`, `or`, `not`, `class`. These are escaped with a trailing `_`.
- **Filtering:** take only connectors where both ends are `Object_Type='Class'` inside TC57CIM. This drops object links from the instance diagrams.

## Design
- **Classes:** plain generated classes with `__slots__` and keyword-only `__init__`. No dataclasses and no pydantic.
- **Runtime:** a hand-written `cim100/_runtime/` provides the `CimObject` base and the helpers that update both ends of 1:1, 1:N and N:M associations.
- **Layout:** `src/cim100/model/<std>/<pkg...>/<snake_class>.py`, plus a generated `_registry.py` and a lazy (PEP 562) top-level `__init__`.
- **Imports:** inheritance uses real imports; association types are string annotations under TYPE_CHECKING.
- **Associations:**
  - Upper bound 1 is a property whose setter keeps both ends in sync.
  - Upper bound >1 is a private list with Zepben-style `x` (generator), `num_x`, `get_x_by_mrid`, `add_x`, `remove_x` and `clear_x`.
  - Lower bounds are reported by `validate()` and not enforced at construction.
- **Types:**
  - Primitives map to Python types: Float→float, Integer→int, Boolean→bool, String→str, Decimal→Decimal, DateTime→datetime, Date→date, Time→time. Duration and MonthDay stay str.
  - CIMDatatype attributes hold their value type, with unit and multiplier as metadata.
  - Compounds become slotted value classes.
  - Enumerations become `enum.Enum` with the CIM literal spellings.
- **Naming:** members are snake_case. Duplicate class names: the canonical one is exported at the top level, the other is reachable only by its module path. The generator fails on any collision it does not recognise.
- **Metadata:** every generated class has `_cim_meta` (package, EA GUID, multiplicities), which the completeness tests use.
- **What is committed:** generated code, checked with `tools/regen.py --check`, and the IR JSON snapshot.

## Decisions (decided by recommendation; Michael gave blanket autonomy on 2026-10-27)
1. Scope is TC57CIM, including the Inf\* and PackageDependencies packages. European extensions are left out.
2. mRID is optional and defaults to `str(uuid4())`.
3. The IR JSON snapshot is committed, so tests run offline.
4. The generated code is committed, with `--check` in the tests.
5. Classes marked «deprecated» and the Inf\* packages are generated and flagged in metadata.
6. Lower bounds are reported by `validate()` only.
7. Build models are chosen to save cost. Opus builds only M2 (EA reader) and M4 (association runtime). The others use sonnet. Reviews use sonnet.

## Milestones (one agent and one commit each, run in order)
| # | Work | Acceptance | Model |
|---|---|---|---|
| M0 | uv project `cim100-sdk` (py3.12), pyproject (jinja2; dev: pytest, ruff), .gitignore, README, `src/cim100/`, `codegen/`, `tools/`, `tests/` | `uv run pytest` passes; ruff is clean | sonnet |
| M1 | `model-source.toml` and `tools/fetch_model.py` (download, sha256, SQLite header, cache in `build/model/`, mirror fallback) | A wrong hash fails; a test checks the IEC61970CIMVersion version is IEC61970CIM17v40 (skipped if the model is absent) | sonnet |
| M2 | `codegen/ir.py` and `codegen/ea_reader.py` write `codegen/snapshot/cim100_ir.json` (sorted, deterministic) | Counts match the table above; output is identical on every run; role/cardinality mapping is tested | opus |
| M3 | `codegen/normalize.py` handles snake_case, keyword escaping, duplicate classes/members, overrides, generated role names and type resolution; writes `codegen/snapshot/naming_report.md` | No unresolved names; known collisions are unit-tested | sonnet |
| M4 | `src/cim100/_runtime/`: CimObject, two-way link helpers, enum/datatype bases; tested on a hand-written mini model | Both ends stay consistent through set/replace/remove/clear; no recursion | opus |
| M5 | `codegen/generate.py` and Jinja2 templates generate the package, `_registry.py`, lazy `__init__` and `py.typed`; `tools/regen.py [--check]` | Generation runs cleanly; ruff is clean; a second run gives no diff | sonnet |
| M6 | Commit the generated package and `tests/sdk/`: completeness against the IR, two-way checks on every association, every concrete class instantiates, importing everything takes <3 s | All tests pass offline; the regen check is clean | sonnet |

Later: CIMXML/RDF I/O; network container/services; API docs; `.eap`/CSV reader backend.
