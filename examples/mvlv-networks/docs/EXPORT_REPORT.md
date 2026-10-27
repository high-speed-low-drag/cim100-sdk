# Export report (S4)

Generated from a real run of `mvlv-cim verify --all` (all four networks, both formats). The
generated files are in `out/` (gitignored, not committed).

## Result

Every network round-trips in both formats: `canonical_dump` of the built graph equals that of the
graph read back from CIMXML and from JSON-LD, the two read graphs equal each other, exporting twice
gives byte-identical files, and there are 0 warnings and 0 dangling references.

### Objects by main class

| Network | Objects | ACLineSegment | Terminal | ConnectivityNode | PowerTransformer | PowerTransformerEnd | RatioTapChanger | EquivalentInjection | LinearShuntCompensator |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Network_1_Rural_SMR8 | 47074 | 3611 | 9363 | 4329 | 717 | 1434 | 542 | 704 | 2 |
| Network_2_Rural_KLO14 | 48566 | 3824 | 9773 | 4533 | 711 | 1422 | 502 | 700 | 2 |
| Network_3_Urban_HPK11 | 6538 | 593 | 1321 | 639 | 45 | 90 | 0 | 44 | 0 |
| Network_4_Urban_CRE21 | 7548 | 649 | 1538 | 723 | 80 | 160 | 0 | 79 | 0 |

Other classes per network (Location, PositionPoint, Name, CurrentLimit, ...) are counted in the
total and in `mvlv-cim summary`.

### Files, times and checks

Times are wall clock on the 4-CPU server (the writes include nothing but serialization).

| Network | Format | Size (MB) | Write (s) | Read (s) | Round-trip equal | Deterministic | Warnings | Dangling |
|---|---|---:|---:|---:|---|---|---:|---:|
| Network_1_Rural_SMR8 | .xml | 21.1 | 3.2 | 1.7 | yes | yes | 0 | 0 |
| Network_1_Rural_SMR8 | .jsonld | 23.3 | 2.4 | 1.4 | yes | yes | 0 | 0 |
| Network_1_Rural_SMR8 | xml = jsonld | | | | yes | | | |
| Network_2_Rural_KLO14 | .xml | 21.7 | 3.1 | 1.7 | yes | yes | 0 | 0 |
| Network_2_Rural_KLO14 | .jsonld | 24.0 | 2.4 | 1.4 | yes | yes | 0 | 0 |
| Network_2_Rural_KLO14 | xml = jsonld | | | | yes | | | |
| Network_3_Urban_HPK11 | .xml | 2.8 | 0.3 | 0.4 | yes | yes | 0 | 0 |
| Network_3_Urban_HPK11 | .jsonld | 3.1 | 0.3 | 0.1 | yes | yes | 0 | 0 |
| Network_3_Urban_HPK11 | xml = jsonld | | | | yes | | | |
| Network_4_Urban_CRE21 | .xml | 3.3 | 0.4 | 0.2 | yes | yes | 0 | 0 |
| Network_4_Urban_CRE21 | .jsonld | 3.6 | 0.3 | 0.2 | yes | yes | 0 | 0 |
| Network_4_Urban_CRE21 | xml = jsonld | | | | yes | | | |

Each file holds every object of its network, including the 5 shared BaseVoltages and the shared
GeographicalRegion. The only round-trip discrepancy found was in the builder, not the SDK:
`RatioTapChanger.step` of the fixed off-load taps was the int `1` and came back as the float `1.0`.
It is now a float in `builder.py` (as for the regulators).

`canonical_dump` already handles objects without an mRID (`Name`, `PositionPoint`, `Location`
children): their `gen<N>` ids come from a content-based sort, so they compare by content.

## Header

The `created` timestamp is the UTC mtime of the source workbook (or `--created`), so output is
deterministic for a given checkout. Source URL and licence are in the `description` entries.

```xml
<md:FullModel rdf:about="urn:uuid:c43abbdd-d9fd-5b77-98f8-f0831b3a9f45">
    <md:Model.created>2026-10-27T09:27:58Z</md:Model.created>
    <md:Model.version>1</md:Model.version>
    <md:Model.modelingAuthoritySet>urn:x-mvlv-cim:authority:ausnet-mv-lv-networks</md:Model.modelingAuthoritySet>
    <md:Model.description>CIM100 model of Network_3_Urban_HPK11 (feeder HPK11); MV network with LV equivalents (EquivalentInjection per distribution transformer)</md:Model.description>
    <md:Model.description>Source data: https://github.com/Team-Nando/MV-LV-Networks (workbook Network_3_Urban_HPK11.xlsx), licence BSD-3-Clause, (c) 2024 Team Nando</md:Model.description>
  </md:FullModel>
```

```json
{
  "@id": "urn:uuid:c43abbdd-d9fd-5b77-98f8-f0831b3a9f45",
  "@type": "dcat:Dataset",
  "prov:generatedAtTime": {
    "@value": "2026-10-27T09:27:58Z",
    "@type": "xsd:dateTime"
  },
  "dcterms:issued": {
    "@value": "2026-10-27",
    "@type": "xsd:date"
  },
  "dcat:version": "1",
  "dcat:isVersionOf": {
    "@id": "urn:x-mvlv-cim:authority:ausnet-mv-lv-networks"
  },
  "dcterms:description": [
    {
      "@value": "CIM100 model of Network_3_Urban_HPK11 (feeder HPK11); MV network with LV equivalents (EquivalentInjection per distribution transformer)",
      "@language": "en"
    },
    {
      "@value": "Source data: https://github.com/Team-Nando/MV-LV-Networks (workbook Network_3_Urban_HPK11.xlsx), licence BSD-3-Clause, (c) 2024 Team Nando",
      "@language": "en"
    }
  ]
}
```

## Reproduce

```
cd ~/claude_code/cim100-networks
uv sync
uv run mvlv-cim export --all --format both --out out/ --source ~/claude_code/MV-LV-Networks
uv run mvlv-cim verify --all          # build, write, read, compare, determinism (about 55 s)
uv run mvlv-cim summary               # counts by class
uv run pytest -q                      # N3 and N4 round trip
MVLV_FULL=1 uv run pytest -q          # also N1 and N2 (about 2 min)
```

## Sample from Network_3_Urban_HPK11

One ACLineSegment, its two Terminals, one distribution PowerTransformer with its two ends, and the
EquivalentInjection of the first listed injection (ids and order as written).

### CIMXML (`out/Network_3_Urban_HPK11.xml`)

```xml
  <cim:ACLineSegment rdf:ID="_01a9bc18-aa54-52ec-87fd-da5f7c8bbb77">
    <cim:Conductor.length>55.313</cim:Conductor.length>
    <cim:IdentifiedObject.description>linecode=2-3ph; line_number=428</cim:IdentifiedObject.description>
    <cim:IdentifiedObject.name>CDR017</cim:IdentifiedObject.name>
    <cim:ACLineSegment.PerLengthImpedance rdf:resource="#_5b83b26e-ebb5-577a-a541-de586d3ed253" />
    <cim:ConductingEquipment.BaseVoltage rdf:resource="#_d73b3142-13eb-5b25-ba19-3b678882f4be" />
    <cim:Equipment.EquipmentContainer rdf:resource="#_38608542-69a8-5329-9092-7adbccda990d" />
    <cim:PowerSystemResource.Location rdf:resource="#_0aac0de7-4b94-5647-b016-6c3f93750d37" />
  </cim:ACLineSegment>
  <cim:Terminal rdf:ID="_68cd08c3-8bab-5a84-80ae-a0489726c870">
    <cim:ACDCTerminal.connected>true</cim:ACDCTerminal.connected>
    <cim:ACDCTerminal.sequenceNumber>1</cim:ACDCTerminal.sequenceNumber>
    <cim:IdentifiedObject.name>CDR017 T1</cim:IdentifiedObject.name>
    <cim:Terminal.phases rdf:resource="http://iec.ch/TC57/CIM100#PhaseCode.ABC" />
    <cim:Terminal.ConductingEquipment rdf:resource="#_01a9bc18-aa54-52ec-87fd-da5f7c8bbb77" />
    <cim:Terminal.ConnectivityNode rdf:resource="#_f06139e9-f4e2-555a-ae06-311675555235" />
  </cim:Terminal>
  <cim:Terminal rdf:ID="_e428767e-c4c6-5771-bc5e-a5c4c0235788">
    <cim:ACDCTerminal.connected>true</cim:ACDCTerminal.connected>
    <cim:ACDCTerminal.sequenceNumber>2</cim:ACDCTerminal.sequenceNumber>
    <cim:IdentifiedObject.name>CDR017 T2</cim:IdentifiedObject.name>
    <cim:Terminal.phases rdf:resource="http://iec.ch/TC57/CIM100#PhaseCode.ABC" />
    <cim:Terminal.ConductingEquipment rdf:resource="#_01a9bc18-aa54-52ec-87fd-da5f7c8bbb77" />
    <cim:Terminal.ConnectivityNode rdf:resource="#_9e6a8e3d-9be0-5319-b8ec-1d6abcb2c7f8" />
  </cim:Terminal>
  <cim:PowerTransformer rdf:ID="_0103d791-2113-5379-9f41-f13a93823b47">
    <cim:IdentifiedObject.description>source=lvtx; conn_type=RWB; wdg1_tap=1</cim:IdentifiedObject.description>
    <cim:IdentifiedObject.name>MICHELLE_SIMON</cim:IdentifiedObject.name>
    <cim:PowerTransformer.vectorGroup>Dyn1</cim:PowerTransformer.vectorGroup>
    <cim:Equipment.EquipmentContainer rdf:resource="#_19a4d483-c096-5b1a-8cea-112048127744" />
    <cim:PowerSystemResource.Location rdf:resource="#_d9f60ee3-595a-5351-84f0-6e51de336207" />
  </cim:PowerTransformer>
  <cim:PowerTransformerEnd rdf:ID="_5876226c-e947-52d8-b994-2ae95e789aad">
    <cim:IdentifiedObject.name>MICHELLE_SIMON end 1</cim:IdentifiedObject.name>
    <cim:PowerTransformerEnd.b>0.0</cim:PowerTransformerEnd.b>
    <cim:PowerTransformerEnd.connectionKind rdf:resource="http://iec.ch/TC57/CIM100#WindingConnection.D" />
    <cim:PowerTransformerEnd.g>7.8099173553719e-07</cim:PowerTransformerEnd.g>
    <cim:PowerTransformerEnd.phaseAngleClock>0</cim:PowerTransformerEnd.phaseAngleClock>
    <cim:PowerTransformerEnd.r>19.97460317460318</cim:PowerTransformerEnd.r>
    <cim:PowerTransformerEnd.ratedS>315000.0</cim:PowerTransformerEnd.ratedS>
    <cim:PowerTransformerEnd.ratedU>22000.0</cim:PowerTransformerEnd.ratedU>
    <cim:PowerTransformerEnd.x>59.15555555555556</cim:PowerTransformerEnd.x>
    <cim:TransformerEnd.endNumber>1</cim:TransformerEnd.endNumber>
    <cim:PowerTransformerEnd.PowerTransformer rdf:resource="#_0103d791-2113-5379-9f41-f13a93823b47" />
    <cim:TransformerEnd.BaseVoltage rdf:resource="#_d73b3142-13eb-5b25-ba19-3b678882f4be" />
    <cim:TransformerEnd.Terminal rdf:resource="#_568d8dd4-8920-553a-b12c-f42b9991935a" />
  </cim:PowerTransformerEnd>
  <cim:PowerTransformerEnd rdf:ID="_995340e0-9ef4-553a-9c40-c7fe57dfcf77">
    <cim:IdentifiedObject.name>MICHELLE_SIMON end 2</cim:IdentifiedObject.name>
    <cim:PowerTransformerEnd.b>0.0</cim:PowerTransformerEnd.b>
    <cim:PowerTransformerEnd.connectionKind rdf:resource="http://iec.ch/TC57/CIM100#WindingConnection.Yn" />
    <cim:PowerTransformerEnd.g>0.0</cim:PowerTransformerEnd.g>
    <cim:PowerTransformerEnd.phaseAngleClock>1</cim:PowerTransformerEnd.phaseAngleClock>
    <cim:PowerTransformerEnd.r>0.0</cim:PowerTransformerEnd.r>
    <cim:PowerTransformerEnd.ratedS>315000.0</cim:PowerTransformerEnd.ratedS>
    <cim:PowerTransformerEnd.ratedU>433.0</cim:PowerTransformerEnd.ratedU>
    <cim:PowerTransformerEnd.x>0.0</cim:PowerTransformerEnd.x>
    <cim:TransformerEnd.endNumber>2</cim:TransformerEnd.endNumber>
    <cim:TransformerEnd.grounded>true</cim:TransformerEnd.grounded>
    <cim:PowerTransformerEnd.PowerTransformer rdf:resource="#_0103d791-2113-5379-9f41-f13a93823b47" />
    <cim:TransformerEnd.BaseVoltage rdf:resource="#_d7f0a76a-e700-5a32-8fab-10abb4d982a8" />
    <cim:TransformerEnd.Terminal rdf:resource="#_7e0388b0-6320-50d9-b003-68950338d29d" />
  </cim:PowerTransformerEnd>
  <cim:EquivalentInjection rdf:ID="_02eee1ac-15d7-56fd-bd21-55045548417f">
    <cim:EquivalentInjection.regulationCapability>false</cim:EquivalentInjection.regulationCapability>
    <cim:IdentifiedObject.description>type=RES; customers=136; pvs=47; lv_feeders=4</cim:IdentifiedObject.description>
    <cim:IdentifiedObject.name>VON_NIDA_DULWICH LV equivalent</cim:IdentifiedObject.name>
    <cim:ConductingEquipment.BaseVoltage rdf:resource="#_d7f0a76a-e700-5a32-8fab-10abb4d982a8" />
    <cim:Equipment.EquipmentContainer rdf:resource="#_325713d7-1b7a-5a7c-94c3-bc86db93f2a9" />
    <cim:PowerSystemResource.Location rdf:resource="#_602779d7-3b1c-5efe-87ee-8916e92321a9" />
  </cim:EquivalentInjection>
```

### JSON-LD (`out/Network_3_Urban_HPK11.jsonld`)

```json
{
  "@id": "urn:uuid:01a9bc18-aa54-52ec-87fd-da5f7c8bbb77",
  "@type": "cim:ACLineSegment",
  "cim:Conductor.length": 55.313,
  "cim:IdentifiedObject.description": "linecode=2-3ph; line_number=428",
  "cim:IdentifiedObject.mRID": "01a9bc18-aa54-52ec-87fd-da5f7c8bbb77",
  "cim:IdentifiedObject.name": "CDR017",
  "cim:ACLineSegment.PerLengthImpedance": {
    "@id": "urn:uuid:5b83b26e-ebb5-577a-a541-de586d3ed253"
  },
  "cim:ConductingEquipment.BaseVoltage": {
    "@id": "urn:uuid:d73b3142-13eb-5b25-ba19-3b678882f4be"
  },
  "cim:Equipment.EquipmentContainer": {
    "@id": "urn:uuid:38608542-69a8-5329-9092-7adbccda990d"
  },
  "cim:PowerSystemResource.Location": {
    "@id": "urn:uuid:0aac0de7-4b94-5647-b016-6c3f93750d37"
  }
},
{
  "@id": "urn:uuid:68cd08c3-8bab-5a84-80ae-a0489726c870",
  "@type": "cim:Terminal",
  "cim:ACDCTerminal.connected": true,
  "cim:ACDCTerminal.sequenceNumber": 1,
  "cim:IdentifiedObject.mRID": "68cd08c3-8bab-5a84-80ae-a0489726c870",
  "cim:IdentifiedObject.name": "CDR017 T1",
  "cim:Terminal.phases": {
    "@id": "cim:PhaseCode.ABC"
  },
  "cim:Terminal.ConductingEquipment": {
    "@id": "urn:uuid:01a9bc18-aa54-52ec-87fd-da5f7c8bbb77"
  },
  "cim:Terminal.ConnectivityNode": {
    "@id": "urn:uuid:f06139e9-f4e2-555a-ae06-311675555235"
  }
},
{
  "@id": "urn:uuid:e428767e-c4c6-5771-bc5e-a5c4c0235788",
  "@type": "cim:Terminal",
  "cim:ACDCTerminal.connected": true,
  "cim:ACDCTerminal.sequenceNumber": 2,
  "cim:IdentifiedObject.mRID": "e428767e-c4c6-5771-bc5e-a5c4c0235788",
  "cim:IdentifiedObject.name": "CDR017 T2",
  "cim:Terminal.phases": {
    "@id": "cim:PhaseCode.ABC"
  },
  "cim:Terminal.ConductingEquipment": {
    "@id": "urn:uuid:01a9bc18-aa54-52ec-87fd-da5f7c8bbb77"
  },
  "cim:Terminal.ConnectivityNode": {
    "@id": "urn:uuid:9e6a8e3d-9be0-5319-b8ec-1d6abcb2c7f8"
  }
},
{
  "@id": "urn:uuid:0103d791-2113-5379-9f41-f13a93823b47",
  "@type": "cim:PowerTransformer",
  "cim:IdentifiedObject.description": "source=lvtx; conn_type=RWB; wdg1_tap=1",
  "cim:IdentifiedObject.mRID": "0103d791-2113-5379-9f41-f13a93823b47",
  "cim:IdentifiedObject.name": "MICHELLE_SIMON",
  "cim:PowerTransformer.vectorGroup": "Dyn1",
  "cim:Equipment.EquipmentContainer": {
    "@id": "urn:uuid:19a4d483-c096-5b1a-8cea-112048127744"
  },
  "cim:PowerSystemResource.Location": {
    "@id": "urn:uuid:d9f60ee3-595a-5351-84f0-6e51de336207"
  }
},
{
  "@id": "urn:uuid:5876226c-e947-52d8-b994-2ae95e789aad",
  "@type": "cim:PowerTransformerEnd",
  "cim:IdentifiedObject.mRID": "5876226c-e947-52d8-b994-2ae95e789aad",
  "cim:IdentifiedObject.name": "MICHELLE_SIMON end 1",
  "cim:PowerTransformerEnd.b": 0.0,
  "cim:PowerTransformerEnd.connectionKind": {
    "@id": "cim:WindingConnection.D"
  },
  "cim:PowerTransformerEnd.g": 7.8099173553719e-07,
  "cim:PowerTransformerEnd.phaseAngleClock": 0,
  "cim:PowerTransformerEnd.r": 19.97460317460318,
  "cim:PowerTransformerEnd.ratedS": 315000.0,
  "cim:PowerTransformerEnd.ratedU": 22000.0,
  "cim:PowerTransformerEnd.x": 59.15555555555556,
  "cim:TransformerEnd.endNumber": 1,
  "cim:PowerTransformerEnd.PowerTransformer": {
    "@id": "urn:uuid:0103d791-2113-5379-9f41-f13a93823b47"
  },
  "cim:TransformerEnd.BaseVoltage": {
    "@id": "urn:uuid:d73b3142-13eb-5b25-ba19-3b678882f4be"
  },
  "cim:TransformerEnd.Terminal": {
    "@id": "urn:uuid:568d8dd4-8920-553a-b12c-f42b9991935a"
  }
},
{
  "@id": "urn:uuid:995340e0-9ef4-553a-9c40-c7fe57dfcf77",
  "@type": "cim:PowerTransformerEnd",
  "cim:IdentifiedObject.mRID": "995340e0-9ef4-553a-9c40-c7fe57dfcf77",
  "cim:IdentifiedObject.name": "MICHELLE_SIMON end 2",
  "cim:PowerTransformerEnd.b": 0.0,
  "cim:PowerTransformerEnd.connectionKind": {
    "@id": "cim:WindingConnection.Yn"
  },
  "cim:PowerTransformerEnd.g": 0.0,
  "cim:PowerTransformerEnd.phaseAngleClock": 1,
  "cim:PowerTransformerEnd.r": 0.0,
  "cim:PowerTransformerEnd.ratedS": 315000.0,
  "cim:PowerTransformerEnd.ratedU": 433.0,
  "cim:PowerTransformerEnd.x": 0.0,
  "cim:TransformerEnd.endNumber": 2,
  "cim:TransformerEnd.grounded": true,
  "cim:PowerTransformerEnd.PowerTransformer": {
    "@id": "urn:uuid:0103d791-2113-5379-9f41-f13a93823b47"
  },
  "cim:TransformerEnd.BaseVoltage": {
    "@id": "urn:uuid:d7f0a76a-e700-5a32-8fab-10abb4d982a8"
  },
  "cim:TransformerEnd.Terminal": {
    "@id": "urn:uuid:7e0388b0-6320-50d9-b003-68950338d29d"
  }
},
{
  "@id": "urn:uuid:02eee1ac-15d7-56fd-bd21-55045548417f",
  "@type": "cim:EquivalentInjection",
  "cim:EquivalentInjection.regulationCapability": false,
  "cim:IdentifiedObject.description": "type=RES; customers=136; pvs=47; lv_feeders=4",
  "cim:IdentifiedObject.mRID": "02eee1ac-15d7-56fd-bd21-55045548417f",
  "cim:IdentifiedObject.name": "VON_NIDA_DULWICH LV equivalent",
  "cim:ConductingEquipment.BaseVoltage": {
    "@id": "urn:uuid:d7f0a76a-e700-5a32-8fab-10abb4d982a8"
  },
  "cim:Equipment.EquipmentContainer": {
    "@id": "urn:uuid:325713d7-1b7a-5a7c-94c3-bc86db93f2a9"
  },
  "cim:PowerSystemResource.Location": {
    "@id": "urn:uuid:602779d7-3b1c-5efe-87ee-8916e92321a9"
  }
}
```
