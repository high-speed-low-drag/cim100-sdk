# CIM100 SDK: progress and resume log

This file is the source of truth for resuming work after an interruption (usage limit, crash, new session).
Update it and commit it at the end of every milestone, and whenever a milestone is paused partway through.

## Status
- The SDK is complete for in-memory use: all 1,947 CIM100 classifiers are generated with navigable two-way associations.
- 200 tests pass (`uv run pytest -q`); ruff is clean; `tools/regen.py --check` is clean.
- mypy (`uv run --with mypy mypy src/cim100`, 2,062 files, ~14 s, 320 MB): 0 errors before and after M6b; nothing needed fixing. mypy is not a project dependency.
- Later: CIMXML/RDF I/O; network container/services; API docs; `.eap`/CSV reader backend.

## Resume procedure
1. `cd ~/claude_code/cim100-sdk && git status && git log --oneline -15`
2. Read this file and `docs/PLAN.md`.
3. Find the first milestone that is not `done`. If it is `in-progress`, check its branch or WIP commits and continue from there. Don't restart it.
4. Run the tests: `uv run pytest -q` (once the project exists).

## Scope
- Generate every CIM100 class (with attributes, enums, datatypes, inheritance and associations navigable from both ends) as an in-memory Python SDK.
- No serialization yet.
- API style follows Zepben evolve-sdk-python.

## Source model
- cimug-org/CIMTool `CSharpEFTestProject/CSharpEFTestProject/Schema/iec61970cim17v40_iec61968cim13v13b_iec62325cim03v17b_CIM100.1.1.1.qea`
- The file is SQLite and the repo is LGPL-2.1.
- Download it at build time, pinned to a commit SHA and a sha256 checksum. Don't commit the file.

## Decisions
- 2026-10-27: Code is generated from the EA model, not written by hand. (Decided by recommendation; Michael gave blanket autonomy on 2026-10-27.)
- 2026-10-27: Use the .qea (SQLite) instead of the .eap (Access). It is the same model, needs no Access reader, and is the newer cim17v40 revision.
- 2026-10-27: Keep the repo local only. No GitHub repo or push without Michael's approval.
- 2026-10-27: Work happens on branch `feat/cim100-sdk`; `main` holds only plan + scaffold. M0 was self-reviewed (trivial scaffold), no review agent.

## Milestones
| # | Title | Status | Commit |
|---|-------|--------|--------|
| P | Plan (docs/PLAN.md) | done | (this commit) |
| M0 | Scaffold | done | f761be9 |
| M1 | Model fetch | done | e7853ca |
| M2 | EA reader + IR | done (reviewed: PASS WITH NITS) | 45e644b |
| M3 | Normalize | done (reviewed, fixes applied) | 27fcbe3, e5c7a21 |
| M4 | Runtime | done (reviewed PASS WITH NITS, fixes applied) | 95bdfad, befc4e8 |
| M5 | Generator + generated package (committed) | done | f350458, f85278b, bfad248 |
| M6 | Generated package + tests, mypy, README usage | done | 411e3bc, de7bbcb, 2a563d0, M6b (this commit; see git log) |

## Review notes
- M2 review (sonnet, independent; PASS WITH NITS):
  - Six asymmetric associations from IEC61968, IEC62325 and IEC61970 were checked against the raw t_connector rows; all match.
  - The reader drops nothing in scope.
  - Notes for M3:
    - Key classes by GUID, not name: TroubleReportingKind appears twice in the same package.
    - There are 14 self-associations.
    - Don't rely on `navigable`.
    - `0..0` would be rejected; the model has none.
- M3 orchestrator smoke test: 2 of the 405 enums fail on `enum.Enum` because their literal names are reserved `_sunder_` names: ASTMStandardEditionKind `_00_2005_` and UKMinistryofDefenceStandardKind `_05_50__Part_65_`. A fix is needed before M5; it is pending a review agent.
- M3 review (sonnet): FAIL (narrow).
  - Blocker: 26 `_sunder_` enum literals in 2 enums. Normalization rules are all clean.
  - Medium: `get_*_by_mrid` is generated for targets that have no mrid; bad singular names (`time_sery`, `sv_statu`).
  - Low: `network_boundarys`; Facility.kind overrides AssetKind with str.
  - Fix agent launched with decided rules: literals get no leading `_` and a `v` prefix for leading digits; an exceptions list for singular names; `pluralize()`; by_mrid only for mrid targets.
  - Note for M5: attributes named `date`, `time`, `open`, `max` and `sum` shadow imports/builtins, so emit qualified `datetime.date` annotations under `from __future__ import annotations`.
- M3 fix applied: literal names (no leading `_`, `v` prefix), singularize exceptions, `pluralize()`, mrid methods only for mrid targets, `RAttribute.override_compatible` (Facility.kind is the only incompatible override).
- M4 (opus): `src/cim100/_runtime/` + `docs/RUNTIME.md` (the M5 contract) + `tests/runtime/` (mini model written exactly as M5 must emit; a test keeps the doc blocks byte-identical to it).
  - Design: `One`/`Many` data descriptors over private `_<end>` slots (unset slot = None/empty; Many = lazy `{id(obj): obj}` dict). Reading a Many returns a tuple snapshot. Generated Many methods are one-liners calling `Many.add/remove/clear/count/get_by_mrid`; `__init__` uses `Many.extend` and `if x is not None` guards.
  - Inverse maintenance uses one-sided `_raw_add`/`_raw_remove`; One's `_raw_add` returns the displaced target for cleanup. Targets/inverses resolve lazily from `"module:ClassName"` and are checked once.
  - Deviation: the runtime avoids importing `typing` (~15 ms); modules use `TYPE_CHECKING = False`. Import ~10 ms. Metas are frozen slotted classes, not NamedTuple/dataclass.
  - Deviation from Decision 2: default mRID is `new_mrid()` (UUID4 string from a private PRNG seeded by os.urandom, ~1 us) instead of `str(uuid4())` (~6 us + 7 ms `import uuid`).
  - mypy is clean on the runtime and mini model (`uv run --with mypy`, not a project dependency).
  - Notes for M5: `__slots__` must be naturally sorted (ruff RUF023); `_cim_meta` on enums needs `enum.nonmember`; all 405 enums build on `CimEnum`; alias imports when two referenced classes share a py_name; overrides get `# type: ignore[assignment]` when the annotation differs.
- M4 (95bdfad), orchestrator decision: accept `new_mrid()` (a fast UUID4 string from a private PRNG seeded from os.urandom and reseeded after fork) instead of `str(uuid4())`. mRIDs are identifiers, not secrets. The format is still a valid UUID4. Review agent launched (sonnet).

- M5 (opus): `codegen/generate.py` + `codegen/templates/*.j2` + `tools/regen.py [--check]` generate `src/cim100/model/**` (1,937 modules: 1,532 classes/datatypes/compounds, 405 enums; 115 docstring-only `__init__.py`) and `_registry.py` (`BY_GUID`, `BY_NAME` canonical only, `MODEL_VERSIONS`). Regen formats with `ruff format --config pyproject.toml`; `--check` is deterministic. Model package is ~13 MB, `_registry.py` ~0.5 MB. `cim100/__init__.py` has PEP 562 `__getattr__`/`__dir__` over `BY_NAME`; `import cim100` ~1-4 ms; importing all 1,937 modules ~0.63 s (warm pyc).
  - Contract choices: static attr with no default is `ClassVar[T | None] = None`, with a default `ClassVar[T] = ...`; a class with no `__init__` parameters (only static attributes) omits `__init__`; an import whose py_name clashes with another reference or the runtime/annotation names gets the alias `<name>_dup<k>` (none occur in the real model); attribute docstrings are not emitted (class docstrings only); `AttrMeta`/`EndMeta` `deprecated` only for attributes (the resolved model has no end deprecation). Ruff: E501 and E741 are ignored for `src/cim100/model/**` (E501 also `_registry.py`); everything else is clean.
  - Notes for M6: `tests/generated/test_generated.py` is the light suite (imports all, instantiates all, spot checks, regen check, import timing). 2 enums have no literals (e.g. TransformerRepairItemKind). Exhaustive checks still to write: every `EndMeta.inverse` exists on the target with matching `many/lower/upper` and points back; `cim_attributes` vs IR for every class; all 405 enums vs IR literals; each non-canonical duplicate importable by module path; deprecated flags vs IR (1 class-level enum, 16 attributes); every `Many` class has the five/four methods named by `RAssocEnd.methods`.
- M6 attempt 1 was cut off by a usage limit with nothing committed. Its partial `tests/sdk/test_completeness.py` was saved as a WIP commit by the orchestrator. It gives 6 passed and 1 failed, with 8 real findings:
  - The `date` defaults on the 6 *CIMVersion classes are dropped. They need generating as `datetime.date(...)`.
  - The attribute meta for `TroubleSymptoms.troubleSymptomsTree` holds the sanitized type name `TroubleSymptomsTree_Kind` instead of the CIM name `TroubleSymptomsTree Kind`.
  - `Mass.unit` 'g' is a known model quirk (UnitSymbol has no `g`). The test should allow it as a documented exception.
- M6a done (opus): fixed at the source the 8 findings of attempt 1. `normalize._parse_default` now emits `_dt.date(y, m, d)` for Date defaults (generator imports `datetime as _dt` at runtime for those modules); `AttrMeta.py_type` holds the CIM type name for non-primitive types (e.g. `TroubleSymptomsTree Kind`); `Mass.unit` 'g' stays None and is allowed through `KNOWN_MODEL_QUIRKS` in the tests. New `tests/sdk/test_integrity.py` (end integrity, exact Many methods, deprecated flags 16/1/0, API surface) and `tests/sdk/test_behaviour.py` (link/unlink of all 1,374 associations from both sides, self-associations, by_mrid). mypy and README still to do for M6.

## Phase 2 (2026-10-27): serialization and MV-LV networks. Decisions approved; see PLAN.md Phase 2
- Source data: ~/claude_code/MV-LV-Networks, a clone of Team-Nando/MV-LV-Networks (BSD-3-Clause). 4 AusNet 22 kV feeders; the rural ones include SWER at 12.7 kV.
- Michael wants the LV network left out. Everything after the distribution transformer secondary becomes an EquivalentInjection.
- Proposed milestones:
  - S1: generic CIMXML (IEC 61970-552) writer and reader.
  - S2: Excel→CIM network builder.
  - S3: write the 4 networks to XML and round-trip them.
- Open questions for Michael:
  - format: CIMXML only?
  - EquivalentInjection p/q: empty?
  - explicit phases for SWER?
  - repo: new cim100-networks repo vs SDK examples/?

| S1 | CIMXML | done (reviewed PASS WITH NITS) | 2f3e057 |
| S2 | JSON-LD | done (verified by orchestrator: CIMXML↔JSON-LD equivalence + pyld expand; no separate review) | 65c77aa |
| S3 | Network builder (~/claude_code/cim100-networks) | in-progress | |
| S4 | Export + round-trip | todo | |
- S1 (2f3e057) review by sonnet: PASS WITH NITS.
  - Conformance matches CGMES conventions; round-trip fidelity is good; performance is linear.
  - The "200 roleless ends" figure was double-counting inherited ends. The real numbers are 66 declared ends, of which 33 are written under snake_case names (none of them in distribution classes).
  - Nits, to be folded into S2:
    - control characters produce invalid XML
    - `\r` is lost
    - `_normalize_id` splits mrids that contain `#`
    - the docstring count is wrong
    - the warning text duplicates the class name

- S2 (sonnet): `cim100.serialization.jsonld` (`write_jsonld`, `to_jsonld_string`, `to_jsonld_dict`, `read_jsonld`, `CimJsonLdError`), following the DIGIN10 CIMJSON-LD convention (3lbits/CIM4NoUtility `Telemark-120/docs/CIMJSON-LD.adoc`; the Grunnprofil path in the brief has moved). `CimDocument` and the reader scaffolding moved to `_common`; test network moved to `tests/serialization/network.py`. S1 nits fixed: XML-invalid control characters raise ValueError, `\r` is written `&#13;`, `normalize_id` strips only a leading `#`/`urn:uuid:`/IRI base and non-NCName mrids use `rdf:about="#_<pct>"`, docstring counts, one roleless-end warning per end per call, warning text `Terminal: ACDCTerminal.sequenceNumber`.
- S3 done: Excel to CIM builder for the four MV networks in ~/claude_code/cim100-networks (branch feat/builder, commit adc1934); 42 tests pass, validate() clean apart from instance_set.
- S4 done: CIMXML and JSON-LD export of the four networks with round-trip verification in ~/claude_code/cim100-networks (branch feat/builder, commit e8e5319); all round trips equal, SDK unchanged.

## Phase 3 (2026-10-31): CGMES 3.0 profiles. Plan in PLAN.md Phase 3
Resume rule: the first milestone not marked done is next. "running" means an agent was started;
if no agent is running any more, check `git log` and the working tree for its WIP, then retry once.

| # | Work | Status | Commit |
|---|---|---|---|
| C1 | OWL reader + profile snapshot | done | 5c866cf |
| C2 | European extensions | done | d5cbb30 |
| R1 | Review C1+C2 | done | 87f58c4 |
| C3 | Profile API + validate_profile | done | 03b8f4e |
| C4 | CGMES writer | todo | |
| C5 | CGMES reader + samples | todo | |
| R2 | Review C3–C5 | todo | |
| C6 | MV example + README | todo | |
| F | Final checks + report | todo | |

- C1 (5c866cf): `profile-source.toml`, `codegen/profile_source.py`, `tools/fetch_profiles.py`, `codegen/owl_reader.py` (OWL conventions in its docstring), `tools/dump_profiles.py [--check]`, snapshot `src/cim100/profiles/data/cgmes_3_0.json` (~290 KB, ships in the wheel). 30 new tests in `tests/profiles/` (292 passed in all).
  - Snapshot schema (documented in `tools/dump_profiles.py`): `profiles[keyword]` = keyword, name, file, uri, version, base, comment, orphan_properties, classes. Class = ns, super (profile superclass), concrete, enumeration, stereotypes, literals (null = all CIM literals), min_instances, properties. Property (keyed `Class.prop`, under the class that owns it, i.e. the side written in CIMXML) = ns, kind (attribute/association/null), min, max (null = CIM multiplicity), range (`cim:`/`eu:`/`xsd:`/`cim15:` prefixed), range_kind (datatype/enumeration/compound/class), targets (in-profile classes), stereotypes.
  - Profile URIs, keywords and versions come from `owl:versionIRI`/`dcat:keyword`/`owl:versionInfo` of the ENTSO-E RDFS2020 vocabularies (entsoe/CGMES-AP e96dd4e, `CGMES/RDFS/61970-600-2_*-AP-Voc-RDFS2020.rdf`), matching powsybl `CgmesNamespace` for EQ/OP/TP/SV/SSH/EQBD. All `http://iec.ch/TC57/ns/CIM/<Name>-EU/3.0`, version 3.0.0, except DY `Dynamics-EU/1.0` (1.0.0). Keywords EQ, SSH, TP, SV, DL, GL, OP, SC, EQBD, DY.
  - Counts (classes / properties): EQ 180/292 (14 eu), TP 14/13 (2 eu), SSH 72/65, SV 23/31, DL 12/26, GL 11/39, OP 37/57, SC 35/106, EQBD 22/27 (11 eu), DY 0/0. The brief's higher SSH/SV/SC numbers counted unattached restrictions, which are now `orphan_properties` (SSH 25, SV 16, SC 15).
  - Class stereotype `description` = instances are written with `rdf:about` in that profile (defined in another one): e.g. TP Terminal/ConnectivityNode, most SSH classes, SV CsConverter/VsConverter. C4 should use it for `rdf:ID` vs `rdf:about`.
  - Profile properties of a class are the union along its profile superclasses (EQ restates `OperationalLimit.*` on ActivePowerLimit/ApparentPowerLimit).
  - Enum literals: only 11 enumerations list literals (`owl:oneOf`, SSH/OP/DL); the rest (all EQ, incl. `eu:LimitKind`) mean "all literals". The EU literals for C2 are in the CGMES-CIM17 clone `Schema/*.qea` (LimitKind: patl, patlt, tatl, tc, tct, highVoltage, lowVoltage, operationalVoltageLimit, alarmVoltage, warningVoltage, stability; BoundaryPoint attributes) and in the ENTSO-E RDFS files.
  - Pinned SDK gaps (`tests/profiles/test_gaps.py`): eu classes BoundaryPoint, LimitKind, SolarPowerPlant, WindPowerPlant; 14 eu properties; `cim:VsConverter.uf` (SV, min 1 only, no range); range `cim:Simple_Float` (SSH, SV) and orphan `Simple_Float.value`; SC stale: attached `cim15:SynchronousMachine.GeneratingUnit`, ranges `cim15:Conductance/Reactance/Resistance/Susceptance`, and 14 orphan restrictions (6 cim15, 8 cim such as `PhaseTapChanger.TransformerWinding`).
- C2 (d5cbb30): eu: extensions are generated model members. 315 passed, 13 skipped; ruff and `regen.py --check` clean; examples 2 passed, 51 skipped (no source data).
  - Source: the European package `EuropeanCIMExtensions/ExtIEC61970/ExtEuBase` (`ExtIEC61970Version` 3.0) of the CGMES-CIM17 EA model, pinned in `profile-source.toml` `[schema]` (sha256, 50,151,424 bytes, fetched by `tools/fetch_profiles.py --schema` into `build/profiles/`). `codegen/eu_reader.py` reads it (CIMTool pattern: `IdentifiedObject` generalizes `ExtEuIdentifiedObject` -> IR classifier with `extends`; CIM GUIDs are the same as CIM100's and are checked by GUID+name; the NC `ExtOperationalLimitType` generalization is skipped). `tools/dump_eu_ir.py [--check]` writes `codegen/snapshot/eu_ir.json` (IR shape of cim100_ir.json); the check test skips without the .qea. LimitKind literals confirmed as in C1 notes; all types/multiplicities agree with the OWL snapshot (UML 0..1 where profiles say min 1).
  - IR: `namespace` on Classifier/Attribute/Association (default `cim`, omitted in JSON so cim100_ir.json is unchanged), `Classifier.extends`, `codegen.ir.merge(base, ext)`. `normalize.load_model()` = CIM100 + eu (used by regen, naming_report, tests/sdk); `load_snapshot()` stays CIM100-only. Module root `EuropeanCIMExtensions` -> `cim100.model.european...` (e.g. `cim100.model.european.ext_iec61970.ext_eu_base.ext_eu_core.boundary_point`). A class name in two namespaces raises NormalizeError (none today). `MODEL_VERSIONS` gains `ExtIEC61970Version: 3.0`.
  - Namespace API: `ClassMeta.namespace`, `AttrMeta.namespace`, `EndMeta.namespace` (prefix; keyword arg, default `"cim"`, so existing callers are unchanged); `cim100._runtime.NAMESPACES` maps `cim`/`eu` to URIs. A member's namespace is its own (`ACLineSegment` has `eu:IdentifiedObject.shortName`); both ends of a European association are `eu`. Python names: `short_name`, `energy_ident_code_eic`, `OperationalLimitType.kind`, `ConnectivityNode.boundary_point`, `WindGeneratingUnit.wind_power_plant`, `WindPowerPlant.wind_generating_units` (`add_/num_wind_generating_unit`), same for solar.
  - Serializers: `_common` `ClassPlan/AttrSpec/EndSpec.ns` and `.qname` (`eu:BoundaryPoint.fromEndIsoCode`), `namespace_uri`, `EU_NS`, `enum_resource(..., compact=True)`. CIMXML writes `eu:` tags and `rdf:resource="http://iec.ch/TC57/CIM100-European#LimitKind.patl"`; JSON-LD writes `eu:` types/keys and `{"@id": "eu:LimitKind.patl"}`. `xmlns:eu` / context `eu` are declared only when used (pure-CIM output is byte-identical to before). Readers match by local name; the JSON-LD reader treats prefix `eu` as CIM vocabulary even without a context entry, so DIGIN's `eu:Equipment.networkAnalysisEnabled` now reads into the CIM attribute (test updated). Association direction: BoundaryPoint.ConnectivityNode and the GeneratingUnit -> plant ends are written, matching the profiles.
  - For C4: CGMES files usually declare `xmlns:eu` always; the CGMES writer may want to force it. canonical_dump keys stay unprefixed. Gap test now leaves only CIM17-2 (`VsConverter.uf`, `Simple_Float`) and stale SC gaps; `test_eu_members_modelled` checks every eu snapshot member against the SDK (namespace, type, narrowed multiplicity).
  - Side fix: `codegen/snapshot/naming_report.md` was stale (CIMVersion dates are parsed since an earlier milestone) and now also covers eu.
- R1 (87f58c4): verdict PASS WITH NITS; no code bugs found in C1/C2. 316 passed, 13 skipped; ruff, `regen.py --check`, `dump_profiles.py --check`, `dump_eu_ir.py --check`, `naming_report.py` clean.
  - Verified: an independent re-parse of all 10 OWL files agrees with the snapshot on every class stereotype, profile superclass, property set, min/max and presence of a range (0 differences); spot checks of ACLineSegment, Terminal (EQ/TP/SSH), SSH EnergyConsumer, SV SvVoltage, OperationalLimitType and the 11 `owl:oneOf` enumerations match the raw OWL; every profile `super` and `targets` entry exists, every property domain is in the CIM MRO of its class, restated properties never conflict with the parent's. Pure-CIM CIMXML and JSON-LD of the test network are byte-identical to commit e07eae2. eu round trips (BoundaryPoint <-> ConnectivityNode, WindPowerPlant <-> WindGeneratingUnit, SolarPowerPlant, LimitKind, shortName/energyIdentCodeEic on CIM classes) work in CIMXML and JSON-LD. The CIMXML reader was not changed by C2 (it always matched local names).
  - Fixed: added `tests/profiles/test_direction.py` (pins the finding below).
  - Open, for C4: the generic writer rule (`association_write_end`: single-valued end first, else name order) differs from the profile's owning side for 9 of 142 profile associations (DL VisibilityLayer.VisibleObjects, EQ PowerElectronicsConnection.PowerElectronicsUnit, EQ ThermalGeneratingUnit.CAESPlant, GL Location.PowerSystemResources, OP AccumulatorLimitSet/AnalogLimitSet.Measurements, OP MeasurementValueQuality.MeasurementValue, SV TopologicalIsland.TopologicalNodes, SV DCTopologicalIsland.DCTopologicalNodes). The BoundaryPoint and Wind/Solar plant ends match only by the rule's tie-break. No profile lists both ends. C4 must use the snapshot owner.
  - Open, for C4: `IdentifiedObject.mRID` is never written by the generic writers (`AttrSpec.is_id`); CGMES 3 profiles list it, so the CGMES writer must emit it. The snapshot `min`/`max` are what the OWL says: `max` null means the CIM multiplicity, and associations to classes of another profile have empty `targets` (SV, TP). EQ `Terminal.ConductingEquipment` has no minCardinality in the OWL (source fidelity).
  - Open, for C3: the snapshot lists only a class's own properties; the union along `super` is the API's job. Restated `OperationalLimit.*` on ActivePowerLimit/ApparentPowerLimit are identical to the parent's.
  - Open, for C5: `read_cimxml` returns one `CimDocument` per file; merging files needs a shared id table (a SSH `rdf:about` of an EQ object currently creates a stub of the element's class in that file only). Reading enum resources of a CIMXML written with a custom `namespace` that has no `#` fails (pre-existing: the reader has no namespace argument).
  - Nits: JSON-LD `_is_cim_prefix` treats the prefix `eu` as CIM vocabulary whatever the context maps it to (needed for DIGIN's `https://cim.ucaiug.io/ns/eu#`; `jsonld.py:390`); `test_dump_check_is_clean` and `test_dump_eu_ir_check_is_clean` skip when `build/profiles/` is empty, so drift only shows after `tools/fetch_profiles.py --schema`; `dump_profiles.py --check` downloads when the cache is empty; `test_pyld_expands_output` never runs (pyld not a dev dependency), so JSON-LD validity of the `eu` context is unproven.
- C3 (03b8f4e): runtime profile layer. 354 passed, 13 skipped; ruff, `regen.py --check` and `gen_profile_stubs.py --check` clean. 38 new tests in `tests/profiles/` (`test_api`, `test_facade`, `test_validate`, helper network `eq_network.py`).
  - Modules: `cim100/profiles/_model.py` (`Profile`, `ProfileSet`, `PropertyInfo`), `_validate.py` (`ProfileIssue`, `validate_profile`), `cgmes3.py` + generated `cgmes3.pyi` (written by `tools/gen_profile_stubs.py [--check]`; per-file ruff ignore in pyproject). `from cim100.profiles import cgmes3, Profile, ProfileSet, PropertyInfo, ProfileIssue, validate_profile`. Another snapshot loads with `ProfileSet.load("<file>.json", "<name>")` / `from_snapshot(dict, name)` (the data file must sit in `cim100/profiles/data/`).
  - Facade choice: `cim100.profiles.cgmes3` is both the bundle and the facade (`cgmes3.EQ`, `cgmes3.profiles`, `cgmes3.ACLineSegment is cim100.ACLineSegment`); lazy via module `__getattr__`, `__all__` (computed on demand) and `__dir__`. 249 classes/enums/compounds (eu included); market/asset/work classes are absent.
  - API: `Profile`: `keyword name uri version comment base classes class_names concrete_classes has_class is_concrete is_description is_enumeration superclass properties(cls) property(cls, prop) has_property required(cls) allowed_literals(enum) validate()`. `cls` may be an SDK class or a CIM name (`cim:`/`eu:` prefix allowed). `properties(cls)` is inherited along the profile superclass chain, base class first. `PropertyInfo`: `name` ("ACLineSegment.r", profile-qualified), `namespace`, `python_name` (None for known gaps), `kind`, `min`, `max` (effective: profile max else SDK upper, None = unbounded), `range`, `range_kind`, `targets`, `literals` (CIM spellings or None), `stereotypes`, `owner` (SDK class that lists it), `many`, plus `.qname .required .in_sdk .is_association`. `prop` lookup accepts Python name (`r`), bare CIM name (`mRID`) or `Declaring.prop`. `ProfileSet`: `profiles keywords by_keyword by_uri classes class_names has_class profiles_of(cls, prop=None) defining_profiles(cls) validate(...)`, iterable, `ps["EQ"]`, `ps.EQ`; the `cgmes3` module re-exposes `profiles by_keyword by_uri profiles_of defining_profiles classes class_names profile_set`.
  - Gaps surface as `python_name is None` (never crash, skipped by validation): only `SV VsConverter.uf` and `SC SynchronousMachine.GeneratingUnit` (cim15). The `Simple_Float` range stays a string; orphan restrictions are not exposed.
  - `validate_profile(objects, profiles, *, include_reachable=True)`: `profiles` is a Profile, a ProfileSet or an iterable. Errors: class not in the selected profiles; class concrete in none of the selected profiles that carry it; missing required property (per selected profile that lists it); end count above effective max; enum value outside the profile's literals. Warning: property set but not listed (an end counts as listed when a selected profile lists the opposite end; `mRID` and attributes still at their SDK default are never reported). Uses `collect`; about 0.4 s for 35 000 objects (plans are cached per class and selection). `obj.validate()` unchanged.
  - For C4 (writer): per profile `p` and object class `cls`: `p.has_class(cls)` decides whether the object appears in that file; `cgmes3.defining_profiles(cls)` (concrete and not description) gives where `rdf:ID` goes, a description profile (`p.is_description(cls)`) writes `rdf:about`; write `p.properties(cls)` with `info.python_name` (skip None), `info.qname` as the XML tag (`eu:` for extensions), `info.owner` is the class that owns the association in the profile, i.e. the direction to write (`info.is_association`; the inverse end is never listed). `IdentifiedObject.mRID` is a normal listed attribute (`mrid`, it should become the id, not a tag, as the generic writer does). Skip associations whose target class is not in the profile only if you decide to; `info.targets` is empty for references to other profiles. Attributes of enumeration kind: restrict to `info.literals` when not None. Pre-check with `validate_profile` to warn.
  - For C5 (reader): `cgmes3.by_uri(model_profile_uri)` maps `md:Model.profile` to a Profile (accept the 2.4.15-style URIs later by adding a snapshot); `p.property(cls, "ns:Class.prop")` classifies an incoming tag; `p.has_class(name)` for unknown-class warnings; `None` python_name gaps should be warned about once.
  - Caveats: `Location.PowerSystemResources` is 1..1 in the GL OWL (so >1 resource is an error, source-faithful); a class that is concrete in one selected profile and a plain reference (non-concrete) in another passes; classes outside the profile chain of IdentifiedObject (e.g. TP `BaseVoltage`, `ConnectivityNode` references) have no `mrid` listed, hence the mRID rule.
