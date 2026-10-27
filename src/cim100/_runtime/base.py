"""`CimObject`: the slotted base of every generated CIM class."""

from __future__ import annotations

from cim100._runtime._compat import TYPE_CHECKING
from cim100._runtime.meta import cim_attributes, cim_ends

if TYPE_CHECKING:
    from typing import Any, ClassVar

    from cim100._runtime.ends import _End
    from cim100._runtime.meta import ClassMeta

# per class: (required attribute names, ends with a lower bound or a finite upper bound)
_checks: dict[type, tuple[tuple[str, ...], tuple[_End[Any], ...]]] = {}


def _validation_plan(cls: type) -> tuple[tuple[str, ...], tuple[_End[Any], ...]]:
    plan = _checks.get(cls)
    if plan is None:
        attrs = tuple(a.name for a in cim_attributes(cls) if a.lower > 0 and not a.static)
        ends = tuple(
            getattr(cls, e.name)
            for e in cim_ends(cls)
            if e.lower > 0 or (e.many and e.upper is not None)
        )
        plan = _checks[cls] = (attrs, ends)
    return plan


class CimObject:
    """Base class. Equality and hashing are identity-based (inherited from object)."""

    __slots__ = ()
    _cim_meta: ClassVar[ClassMeta]

    def __init__(self, **kwargs: Any) -> None:
        if kwargs:
            names = ", ".join(repr(k) for k in kwargs)
            raise TypeError(f"{type(self).__name__}() got unexpected keyword argument(s): {names}")

    def __repr__(self) -> str:
        mrid = getattr(self, "mrid", None)
        if mrid is not None:
            return f"{type(self).__name__}(mrid={mrid!r})"
        return f"{type(self).__name__}(id={id(self):#x})"

    def validate(self) -> list[str]:
        """Multiplicity problems as human-readable strings; never raises."""
        issues: list[str] = []
        try:
            cls = type(self)
            attrs, ends = _validation_plan(cls)
            for name in attrs:
                if getattr(self, name, None) is None:
                    issues.append(f"{self!r}: required attribute {name!r} is not set")
            for end in ends:
                n = end.count(self)
                lower, upper = end.meta.lower, end.meta.upper
                if n < lower:
                    if end.meta.many:
                        issues.append(
                            f"{self!r}: {end.name!r} has {n} item(s), needs at least {lower}"
                        )
                    else:
                        issues.append(f"{self!r}: required association {end.name!r} is not set")
                elif upper is not None and n > upper:
                    issues.append(f"{self!r}: {end.name!r} has {n} item(s), allows at most {upper}")
        except Exception as exc:  # noqa: BLE001 - validate() must never raise
            issues.append(f"{type(self).__name__}: validate() failed: {exc!r}")
        return issues
