"""Snapshot members the SDK does not model, pinned exactly (see PLAN.md Phase 3 facts)."""

import importlib
import json
from importlib import resources

from cim100._registry import BY_NAME
from cim100._runtime.meta import cim_attributes, cim_ends

PRIMITIVES = {
    "Boolean",
    "Date",
    "DateTime",
    "Decimal",
    "Duration",
    "Float",
    "Integer",
    "MonthDay",
    "String",
    "Time",
}

# European extensions (C2 adds them to the model).
EU_CLASSES = {
    "eu:BoundaryPoint": ["EQ", "EQBD"],
    "eu:LimitKind": ["EQ"],
    "eu:SolarPowerPlant": ["EQ"],
    "eu:WindPowerPlant": ["EQ"],
}
EU_PROPERTIES = {
    **{
        f"eu:BoundaryPoint.{p}": ["EQ", "EQBD"]
        for p in (
            "ConnectivityNode",
            "fromEndIsoCode",
            "fromEndName",
            "fromEndNameTso",
            "isDirectCurrent",
            "isExcludedFromAreaInterchange",
            "toEndIsoCode",
            "toEndName",
            "toEndNameTso",
        )
    },
    "eu:IdentifiedObject.energyIdentCodeEic": ["EQ", "EQBD", "TP"],
    "eu:IdentifiedObject.shortName": ["EQ", "EQBD", "TP"],
    "eu:OperationalLimitType.kind": ["EQ"],
    "eu:SolarGeneratingUnit.SolarPowerPlant": ["EQ"],
    "eu:WindGeneratingUnit.WindPowerPlant": ["EQ"],
}
EU_RANGES = {"eu:LimitKind": ["EQ"], "eu:SolarPowerPlant": ["EQ"], "eu:WindPowerPlant": ["EQ"]}

# CIM17-2 members missing from CIM100, and stale CIM15 members left in the ShortCircuit OWL.
CIM17_PROPERTIES = {"cim:VsConverter.uf": ["SV"]}
CIM17_RANGES = {"cim:Simple_Float": ["SSH", "SV"]}
STALE_SC_PROPERTIES = {"cim15:SynchronousMachine.GeneratingUnit": ["SC"]}
STALE_SC_RANGES = {
    f"cim15:{t}": ["SC"] for t in ("Conductance", "Reactance", "Resistance", "Susceptance")
}
ORPHANS = {
    "cim:Simple_Float.value": ["SSH", "SV"],
    **{
        f"cim15:{p}": ["SC"]
        for p in (
            "PhaseTapChangerNonLinear.xMedian",
            "RotatingMachine.parametersFormType",
            "Season.name",
            "ShuntCompensator.bPerSection",
            "ShuntCompensator.gPerSection",
            "Terminal.sequenceNumber",
        )
    },
    **{
        f"cim:{p}": ["SC"]
        for p in (
            "Measurement.Unit",
            "OperationalLimit.type",
            "PhaseTapChanger.TransformerWinding",
            "PhaseTapChanger.phaseTapChangerType",
            "PhaseTapChanger.stepPhaseShiftIncrement",
            "RatioTapChanger.TransformerWinding",
            "ShuntCompensator.reactivePerSection",
            "TapChanger.RegulatingControl",
        )
    },
}


def _cls(name):
    module, cls = BY_NAME[name].split(":")
    return getattr(importlib.import_module(module), cls)


def _in_sdk(qname: str) -> bool:
    cls, prop = qname.split(".", 1)
    if cls not in BY_NAME:
        return False
    k = _cls(cls)
    return any(a.cim_name == prop for a in cim_attributes(k)) or any(
        e.cim_role == prop for e in cim_ends(k)
    )


def _gaps():
    snap = json.loads(
        resources.files("cim100.profiles").joinpath("data/cgmes_3_0.json").read_text("utf-8")
    )
    gaps: dict[str, dict[str, set]] = {k: {} for k in ("class", "property", "range", "orphan")}

    def add(kind, key, kw):
        gaps[kind].setdefault(key, set()).add(kw)

    for kw, p in snap["profiles"].items():
        for cname, c in p["classes"].items():
            if c["ns"] != "cim" or cname not in BY_NAME:
                add("class", f"{c['ns']}:{cname}", kw)
            for pname, prop in c["properties"].items():
                if prop["ns"] != "cim" or not _in_sdk(pname):
                    add("property", f"{prop['ns']}:{pname}", kw)
                rng = prop["range"]
                if rng and not rng.startswith("xsd:"):
                    pre, local = rng.split(":", 1)
                    if pre != "cim" or (local not in BY_NAME and local not in PRIMITIVES):
                        add("range", rng, kw)
        for o in p["orphan_properties"]:
            pre, qname = o.split(":", 1)
            if pre != "cim" or not _in_sdk(qname):
                add("orphan", o, kw)
    return {k: {n: sorted(v) for n, v in d.items()} for k, d in gaps.items()}


def test_known_gaps_exact():
    gaps = _gaps()
    assert gaps["class"] == EU_CLASSES
    assert gaps["property"] == {**EU_PROPERTIES, **CIM17_PROPERTIES, **STALE_SC_PROPERTIES}
    assert gaps["range"] == {**EU_RANGES, **CIM17_RANGES, **STALE_SC_RANGES}
    assert gaps["orphan"] == ORPHANS


def test_every_cim_class_and_in_profile_target_exists():
    snap = json.loads(
        resources.files("cim100.profiles").joinpath("data/cgmes_3_0.json").read_text("utf-8")
    )
    for p in snap["profiles"].values():
        for cname, c in p["classes"].items():
            if c["ns"] == "cim":
                assert cname in BY_NAME
            for prop in c["properties"].values():
                if prop["kind"] == "association" and prop["range"].startswith("cim:"):
                    assert prop["range"][4:] in BY_NAME
