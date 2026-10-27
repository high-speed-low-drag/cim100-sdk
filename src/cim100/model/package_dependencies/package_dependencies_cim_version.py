"""CIM class PackageDependenciesCIMVersion (TC57CIM/PackageDependencies). Generated code: do not edit."""

from __future__ import annotations

from cim100._runtime import AttrMeta, CimObject, ClassMeta

TYPE_CHECKING = False
if TYPE_CHECKING:
    import datetime as _dt
    from typing import ClassVar


class PackageDependenciesCIMVersion(CimObject):
    """The version of dependencies description among top level subpackages of the combined CIM
    model. This is not the same as the combined packages version."""

    __slots__ = ()

    date: ClassVar[_dt.date | None] = None
    version: ClassVar[str] = "10"

    _cim_meta = ClassMeta(
        cim_name="PackageDependenciesCIMVersion",
        package="TC57CIM/PackageDependencies",
        guid="{EEB4990E-A0CF-4f4b-981C-2A2C774153BC}",
        attributes=(
            AttrMeta("date", "date", "date", 0, 1, "primitive", static=True),
            AttrMeta("version", "version", "str", 0, 1, "primitive", "10", static=True),
        ),
    )
