# cim100-networks

Builds CIM100 models of four real Australian MV distribution networks with the generated
[`cim100-sdk`](../cim100-sdk). Package `mvlv_cim` reads the workbooks and returns an in-memory
object graph. Exporting it (CIMXML / JSON-LD) is milestone S4.

| Workbook | Type | Feeder | Lines | Dist. transformers | ISO | REG | In-line | Caps |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `Network_1_Rural_SMR8.xlsx` | rural, 22 kV + SWER | SMR8 | 3611 | 704 | 10 | 2 | 0 | 2 |
| `Network_2_Rural_KLO14.xlsx` | rural, 22 kV + SWER | KLO14 | 3824 | 700 | 7 | 2 | 1 | 2 |
| `Network_3_Urban_HPK11.xlsx` | urban, 22 kV | HPK11 | 593 | 44 | 0 | 0 | 0 | 0 |
| `Network_4_Urban_CRE21.xlsx` | urban, 22 kV | CRE21 | 649 | 79 | 0 | 0 | 0 | 0 |

## Source data and licence

The data comes from [Team-Nando/MV-LV-Networks](https://github.com/Team-Nando/MV-LV-Networks)
(commit `8429f8a`, BSD-3-Clause, © 2024 Team Nando). The networks are operated by AusNet Services.
The workbooks are **not** copied into this repository. Point `MVLV_DATA` at a checkout of that
repository; by default it is the sibling folder `../MV-LV-Networks`. The workbooks are read as
untrusted data with openpyxl (values only, nothing executed). Their `backend.py` (OpenDSS) is the
reference for what each column means. The LV sheets (`lv_lines`, `lv_loads`) are not read.

## Usage

```
uv sync
uv run pytest -q          # builds all four networks; prints build time and memory at the end
uv run ruff check .
```

```python
from mvlv_cim.builder import build_network

net = build_network("../MV-LV-Networks/Network_1_Rural_SMR8.xlsx")
net.objects  # every CIM object (IdentifiedObjects plus Name and PositionPoint)
net.feeder  # the Feeder; net.zone_substation, net.source (ExternalNetworkInjection)
net.counts  # Counter of objects per class
net.element_counts  # line, distribution_transformer, isolating_transformer, regulator, ...
net.issues  # data problems found and handled (Issue(code, message, sheet, source_id))
net.validate()  # validate() messages without the known instance_set quirk
```

Modules: `excel.py` (typed row loading), `builder.py`, `phases.py`, `ids.py` (mRIDs).

## Containers

```
GeographicalRegion "AusNet"                 (shared mRID across networks)
└─ SubGeographicalRegion  <network>
   ├─ Substation "<zone> zone substation"   (normal_energizing_substation of the Feeder)
   │  ├─ VoltageLevel 66 kV : ConnectivityNode SourceBus, ExternalNetworkInjection
   │  ├─ VoltageLevel 22 kV : ConnectivityNode of mv_net_txs.Bus2 (feeder head)
   │  └─ PowerTransformer <zone>  (66/22 kV)
   └─ Substation <Substation_ID>, one per lvtx row (normal_energizing_feeder = the Feeder)
      ├─ PowerTransformer <Substation_ID>
      └─ VoltageLevel 0.433 / 0.24 kV : LV ConnectivityNode, EquivalentInjection
Feeder <zone>  : MV ConnectivityNodes, ACLineSegments, mvtx transformers, capacitors
                 normal_head_terminal = zone transformer terminal 2
```

Each network has 5 BaseVoltages: 66, 22, 12.7, 0.433 and 0.24 kV. Their mRIDs are shared across
networks. A rating within 5 % of one of these maps to it (for example the zone secondary
22.9 kV maps to 22 kV); any other value would get its own BaseVoltage (none occur).

## CIM mapping

| Sheet / column | CIM | Unit / conversion |
|---|---|---|
| buscoords `Node_ID` | `ConnectivityNode` (name `N<id>`) | only buses used by a modelled element |
| buscoords `NodeStartX/Y` | `Location` + 1 `PositionPoint` of transformers, capacitors, injections | anonymised local x/y; `CoordinateSystem.crs_urn = urn:x-local:anonymised-xy` |
| connections `Xcor1/Ycor1/Xcor2/Ycor2` | line `Location` with 2 `PositionPoint`s (seq 1 = Start_Node) | as above |
| lines row | `ACLineSegment` (name `Element_Name`) in the Feeder | rows named `Delete` are skipped (as in backend.py) |
| lines `Length`, `Units` | `ACLineSegment.length` | km × 1000 → m |
| lines `Start_Node`, `End_Node` | `Terminal` 1 / 2 → `ConnectivityNode` | |
| lines `Start_Node_Phase`, `Phases` | `Terminal.phases`; 1-phase: `ACLineSegmentPhase(phase, sequence_number=1)` | see phase table |
| lines `Linecode` + `Phases` | `per_length_impedance` → `PerLengthSequenceImpedance` `lc_<Linecode>-<n>ph` (one per used linecode) | |
| linecodes `r1, x1, r0, x0` | `r, x, r0, x0` | Ω/km ÷ 1000 → Ω/m |
| linecodes `b1, b0` | `bch, b0ch` (`gch = g0ch = 0`) | OpenDSS µS/km × 1e-6 ÷ 1000 → S/m |
| linecodes `Ampacity1/2` | `OperationalLimitSet` + `CurrentLimit` (`value = normal_value = min(Ampacity1, Ampacity2)`), type `PATL` | A (OpenDSS `normamp`) |
| linecodes `Full_Name_Code, Material, Size` | `PerLengthSequenceImpedance.description` | |
| mv_net_txs | `PowerTransformer` in the zone Substation; `ExternalNetworkInjection` at SourceBus | |
| lvtx / mvtx / mv_net_txs `kvas_*` | `PowerTransformerEnd.rated_s` | kVA × 1000 → VA |
| `kvs_*` | `rated_u` | kV × 1000 → V (line-to-line for 3-phase units, winding voltage for 1-phase units) |
| `Connection_*` | `connection_kind`: delta → `D`, wye → `Yn` (OpenDSS wye is grounded); 1-phase units `I`; regulators `Yn` | `vector_group`, `phase_angle_clock` (D/Yn → 1, OpenDSS ANSI lag) |
| `%loadloss`, `xhl` | end 1 `r`, `x` | % × Z_base, Z_base = rated_u₁² / rated_s (Ω referred to end 1); end 2 `r = x = 0` |
| `%noloadloss` | end 1 `g` (`b = 0`, no `%imag` in the data) | % / 100 / Z_base (S) |
| `wdg1_numtaps, wdg1_tap, wdg1_maxtap, wdg1_mintap` | `RatioTapChanger` on end 1 when numtaps > 1, tap ≠ 1, or the unit is a regulator | see below |
| `Conn_Type` | primary `Terminal.phases`; the colour order is kept in the transformer `description` | see phase table |
| lvtx `Bus2` (always 0) | synthesised LV `ConnectivityNode` `<Substation_ID> LV` | |
| lvtx `Type, Customers, PVs, Feeders` | `EquivalentInjection.description` `type=RES; customers=69; pvs=16; lv_feeders=2` | `PVs = 'Null'` → `pvs=unknown` |
| mvcaps row | `LinearShuntCompensator` in the Feeder (`Y`, grounded) | `b_per_section = kvar·1e3 / U²` (S), `nom_u` V, `sections = maximum_sections = normal_sections = 1` |
| `Element_ID` | `Name` with `NameType "source_element_id"` on lines, transformers, capacitors | |
| — | every mRID is `uuid5(NAMESPACE, f"{network}/{kind}/{source_id}")` (see `ids.py`) | rebuilding gives identical mRIDs |

**Tap changers.** For a range in the sheet (the regulators: 17 taps, 0.7478–1.0582):
`step_voltage_increment = (max − min) / (numtaps − 1)`, `high_step = round((max − 1) / inc)`,
`low_step = high_step − (numtaps − 1)`, `neutral_step = 0`, and `normal_step`/`step` come from
`wdg1_tap`. Regulators get `ltc_flag = control_enabled = True`; backend.py's RegControl settings
(vreg 100, band 3, ptratio 127) are in the description. No `TapChangerControl` is modelled.
Distribution transformers give only a fixed off-load tap (1.05, 1.025, 0.975, 0.95) with
`numtaps = 1`. The sheet gives no range, so none is invented (see "Review notes" below).

**Source.** The `ExternalNetworkInjection` uses backend.py's `vsource` (66 kV, R1 = 0.52824,
X1 = 2.113, R0 = 0.59157, X0 = 1.7 Ω). It is stored as `max_initial_sym_sh_c_current` (17.5 kA),
`max_r1_to_x1_ratio`, `max_r0_to_x0_ratio`, `max_z0_to_z1_ratio` and `voltage_factor = 1`.

## Phase mapping

backend.py: `char_to_num = {'R': 1, 'W': 2, 'B': 3}`, so OpenDSS conductor nodes 1, 2, 3 map to
CIM phases A, B, C.

| Source | Example | CIM `Terminal.phases` |
|---|---|---|
| colour R / W / B | | A / B / C |
| 3-phase line (`1.2.3`) | | `ABC` |
| 1-phase SWER line (`Start_Node_Phase` 1) | | `A` on both terminals + `ACLineSegmentPhase.phase = A` |
| 3-colour `Conn_Type` (any order) | `RWB`, `BWR` | primary `ABC`, secondary `ABC` |
| 2-colour lvtx (1-phase across two MV phases) | `RB`, `BR` | primary `AC` (sorted; CIM has no `CA`), secondary `s12N` (backend: centre-tapped `busbar.1.0 busbar.0.2`) |
| 1-colour lvtx (SWER, or phase-to-earth on 22 kV) | `R` | primary `A`, secondary `s1N` (backend: `busbar.1`) |
| 2-colour isolating transformer (mvtx, 22 → 12.7 kV) | `WB` | primary `BC`, secondary `A` (backend: `Bus2.1.0 Bus2.0.2`; the SWER lines use node 1) |
| regulator / in-line mvtx | `WRB` | `ABC` / `ABC` |
| capacitor (`bus1.1.2.3`) | | `ABC` |
| EquivalentInjection | | the transformer's secondary (`ABC`, `s12N` or `s1N`) |

Every 1-phase line in the data is `1`/`1`, i.e. phase A of a SWER system behind an isolating
transformer. "A" there is SWER conductor 1, not MV phase A.

## LV equivalent instead of LV networks

Michael's requirement: the LV networks (`lv_lines`, `lv_loads`) are not modelled. Each distribution
transformer secondary instead gets one LV `ConnectivityNode` and one `EquivalentInjection`. The
injection uses the LV BaseVoltage, its terminal phases match the secondary,
`regulation_capability = False`, and `p`/`q` are unset (a static model). Its name is
`"<Substation_ID> LV equivalent"`. Its description holds the lvtx Type, Customers, PVs and Feeders.

## Known data issues (all handled and reported in `issues`)

| Network | Issue | Handling |
|---|---|---|
| all | linecodes `4-3ph`, `4-1ph`, `4c_.0225-3ph`, `4c_.0225-1ph` are defined twice (`4-*` with different r/x/ampacity, `4c_.0225-*` with different ampacity) | the last definition wins, as on a repeated OpenDSS `new`; none are used by a line |
| 1 | 539 lines named `Delete` (0.19 km, dangling stubs) | skipped like backend.py; their 539 end nodes are not created |
| 1 | 4 lines (Element_ID 4879–4882) have no `connections` row | line geometry from buscoords |
| 1 | 6 `SecondarySub` connections rows match no lvtx row | ignored (connections are only used for geometry) |
| 1 | two pairs of distribution transformers share an MV bus (2102, 648) | each gets its own LV node and injection |
| 1, 2, 3 | buscoords nodes not used by any element (13, 21, 4; in network 1 also the 539 end nodes of the `Delete` lines) | no node created (`orphan_buscoords`) |
| 2 | buscoords Node_ID 3861 listed twice (unused) | first kept |
| 2 | mvtx `PLENTY_VLY_RISE`: connections Type `InLineTransformer` (no -ISO/-REG), 22/22 kV, 1 tap | 3-phase in-line transformer without tap changer; backend.py would treat it as a regulator |
| 2 | 44 single-colour (`R`) lvtx at 22/0.433 kV on the 3-phase 22 kV network (phase-to-earth, so they see 12.7 kV) | rating kept as given, the same as backend.py |
| 1, 2, 4 | `PVs = 'Null'` (37, 38, 19 rows) | `pvs=unknown` |
| 4 | lvtx Element_IDs (e.g. 2105094600) don't match the `connections` IDs; one is empty | keyed by `Substation_ID` when empty |
| all | sheet `delta/wye` on 22/22 kV regulators | modelled as Yn/Yn (backend.py: single-phase grounded-wye autotransformers) |
| all | 2-colour lvtx: the sheet says 0.433 kV secondary, but backend.py builds 22/0.25/0.25 kV centre-tapped | 2 ends, `s12N` secondary rated per the sheet (433 V) |

No islands: every node is reachable from the source in all four networks. The builder would
report islands as `island` issues and assign them a voltage from their equipment.

## Review notes (S3)

Each note gives the source and the choice made.

- **Fixed off-load taps (tap encoding).** Source: lvtx/mvtx `wdg1_tap` ≠ 1 with
  `wdg1_numtaps` ≤ 1 and no range (backend.py's `numtaps=4 maxtap=1.137 mintap=1.028` override is
  not in the sheet and is not used). Choice: never invent data, so one `RatioTapChanger` with
  `low_step = neutral_step = 0`, `high_step = normal_step = step = 1`,
  `step_voltage_increment = (tap − 1) × 100` (5.0 for 1.05, −2.5 for 0.975), `neutral_u` = the end's
  `rated_u`, `ltc_flag = False`, description "fixed off-load tap from sheet (no range given)". This
  keeps low ≤ neutral ≤ high (CGMES) and gives exactly `rated_u × tap` at the current step. A tap of
  exactly 1 with no range gets no tap changer.
- **Regulators without a range.** None in the data. If one appears, no `RatioTapChanger` is
  emitted (no ±10 % fallback) and the issue `regulator_no_tap_range` is recorded.
- **2-colour secondaries.** Source: the sheet's 0.433 kV secondary. Choice: we model `s12N` at
  433 V. backend.py builds a 0.25+0.25 kV centre tap with the kVA on each leg; the difference is
  recorded once per network, with a count, as the issue `backend_centre_tap_differs`.
- **1-phase lines.** Source: linecodes `r1, x1, r0, x0`. Choice: CIM carries the sequence values
  (`r, x, r0, x0`) unchanged. OpenDSS uses Zs = (2·z1 + z0) / 3 for a 1-phase line, so the CIM
  consumer must derive it.
- **Regulator impedance base.** Source: the sheet's kVA rating and `xhl`/`%loadloss`. Choice: we use
  the sheet's rating as the impedance base. backend.py builds per-phase autotransformers, so its
  effective base differs.
