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
| S2 | JSON-LD | todo | |
| S3 | Network builder | todo | |
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
