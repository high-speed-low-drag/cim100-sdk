# CIM100 SDK: progress and resume log

This file is the source of truth for resuming work after an interruption (usage limit, crash, new session).
Update it and commit it at the end of every milestone, and whenever a milestone is paused partway through.

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
| M3 | Normalize | done, in review | 27fcbe3 |
| M4 | Runtime | todo | |
| M5 | Generator | todo | |
| M6 | Generated package + tests | todo | |

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
