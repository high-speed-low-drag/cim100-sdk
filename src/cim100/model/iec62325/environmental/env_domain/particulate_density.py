"""CIM datatype ParticulateDensity (TC57CIM/IEC62325/Environmental/EnvDomain). Generated code: do not edit."""

from __future__ import annotations

from cim100._runtime import AttrMeta, CimDatatype, ClassMeta
from cim100.model.iec61970.base.domain.unit_multiplier import UnitMultiplier
from cim100.model.iec61970.base.domain.unit_symbol import UnitSymbol


class ParticulateDensity(CimDatatype):
    """Particulate density as kg/m3."""

    __slots__ = ()

    value_type = float
    multiplier = UnitMultiplier.none
    unit = UnitSymbol.kgPerm3

    _cim_meta = ClassMeta(
        cim_name="ParticulateDensity",
        package="TC57CIM/IEC62325/Environmental/EnvDomain",
        guid="{47AA7054-AC2F-4daf-B509-136A5802F368}",
        kind="cimdatatype",
        attributes=(
            AttrMeta(
                "multiplier",
                "multiplier",
                "UnitMultiplier",
                0,
                1,
                "enumeration",
                UnitMultiplier.none,
                static=True,
            ),
            AttrMeta(
                "unit", "unit", "UnitSymbol", 0, 1, "enumeration", UnitSymbol.kgPerm3, static=True
            ),
            AttrMeta("value", "value", "float", 0, 1, "primitive"),
        ),
    )
