"""CIM class SolarGeneratingUnit (TC57CIM/IEC61970/Base/Generation/Production). Generated code: do not edit."""

from __future__ import annotations

from cim100._runtime import ClassMeta
from cim100.model.iec61970.base.generation.production.generating_unit import GeneratingUnit


class SolarGeneratingUnit(GeneratingUnit):
    """A solar thermal generating unit, connected to the grid by means of a rotating machine.
    This class does not represent photovoltaic (PV) generation."""

    __slots__ = ()

    _cim_meta = ClassMeta(
        cim_name="SolarGeneratingUnit",
        package="TC57CIM/IEC61970/Base/Generation/Production",
        guid="{C5A085AB-DDD3-41b0-91DE-9071B466AE9A}",
    )
