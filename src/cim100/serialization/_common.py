"""Format-neutral layer shared by the CIMXML (S1) and JSON-LD (S2) serializers.

Everything here is driven by ``_cim_meta`` (see ``cim100._runtime``); no format is written here.

Rules (the contract both formats follow)
----------------------------------------
Object collection and order
    `collect` returns the given roots plus everything reachable through association ends
    (``include_reachable=True``), deduplicated and sorted by ``(CIM class name, id)``.
    Objects without an id (see below) sort by a content key (attribute values and the mRIDs of
    linked objects) and then by encounter order, so the order, and with it the generated ids,
    is stable across runs and across a write/read round trip.

Object ids
    An object with an ``mrid`` uses it. Two different objects with the same mrid raise
    ``ValueError``. Any other object (classes outside IdentifiedObject, or an IdentifiedObject
    whose mrid was set to None) gets ``gen<N>`` (N counts in sort order, skipping ids already
    taken); formats show it as ``_gen<N>``. `assign_ids` does this. A reader must create such
    objects but must not invent an mrid for classes without one. (An IdentifiedObject that was
    written with a generated id comes back with ``mrid="gen<N>"``, because the id is all that
    the file holds.)

Property names
    ``<DeclaringClassCimName>.<cimName>`` where the declaring class is the class whose
    ``_cim_meta`` declares the attribute or end (may be an ancestor; for an override, the
    overriding class). An end uses its CIM role name. The 200 ends without a CIM role (they
    come from 66 associations that carry no role name in the model) use the generated Python
    name of the end instead, e.g. ``AssemblyManifest.model_part_versions``; this is not
    standard CIM, so other tools will not know those properties. Readers also accept the
    ancestor-qualified name of an overridden attribute.
    ``IdentifiedObject.mRID`` is the object id, not a property, and is never written.
    Static (class-level constant) attributes are not serialized.

Values
    float ``repr`` (INF, -INF, NaN as in XSD), bool ``true``/``false``, int ``str``, Decimal
    ``str``, datetime/date/time ISO 8601, str as is. The encoding follows the actual Python
    value, decoding follows the declared type (``AttrMeta.py_type``; for a CIMDatatype
    attribute the datatype's ``value_type``, because the attribute holds the plain value).
    An enum member is the resource ``<ns><EnumCimName>.<literal>`` where literal is
    ``member.value`` (the exact CIM spelling). A compound is nested: a blank node holding the
    compound's own properties ``<CompoundCimName>.<cimName>``, recursively.

Associations
    Each association is written from exactly one end (`association_write_end`): the
    single-valued end when the other end is many; for 1:1 and N:M the end whose
    ``<OwnerCimName>.<Role>`` sorts first (plain string order). ``write_both_ends=True`` writes
    both. Readers accept either or both.

Duplicate CIM names
    ``_registry.BY_NAME`` holds one canonical class per name, but the model has 4 classes whose
    CIM name occurs twice (``IEC61968CIMVersion``, ``TroubleReportingKind``, ``Profile``,
    ``ResourceCertification``; the extra ones are not in BY_NAME, e.g.
    ``IEC61968CIMVersion_2``). `resolve_class` always returns the canonical BY_NAME class
    (after checking the class's own CIM name, so ``MeasurementKind-Old`` works although its
    registry key is ``MeasurementKind_Old``). A non-canonical duplicate is written with the shared
    CIM name and reads back as the canonical class (its properties missing there are reported
    as warnings). Enum literals are looked up in the canonical enum first, then in the other
    enums with the same CIM name (`class_candidates`), so duplicate enums still round-trip.
"""

from __future__ import annotations

import datetime as _dt
import math
import re
from decimal import Decimal
from enum import Enum

from cim100._runtime import (
    CimCompound,
    CimDatatype,
    CimEnum,
    CimObject,
    EndMeta,
    all_metas,
    resolve,
)

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from typing import Any

    from cim100._runtime.ends import _End
    from cim100._runtime.meta import AttrMeta

CIM_NS = "http://iec.ch/TC57/CIM100#"

__all__ = [
    "CIM_NS",
    "AttrSpec",
    "ClassPlan",
    "EndSpec",
    "assign_ids",
    "association_write_end",
    "canonical_dump",
    "class_candidates",
    "class_plan",
    "collect",
    "decode_enum",
    "decode_literal",
    "encode_value",
    "enum_resource",
    "is_write_end",
    "literal_text",
    "resolve_class",
    "resolve_property",
]

# --------------------------------------------------------------------------------------
# class resolution
# --------------------------------------------------------------------------------------

_class_cache: dict[str, type | None] = {}
_cand_cache: dict[str, tuple[type, ...]] = {}


def _safe(name: str) -> str:
    return re.sub(r"\W", "_", name)


def _cim_name(cls: type) -> str:
    return cls._cim_meta.cim_name  # type: ignore[attr-defined, no-any-return]


def class_candidates(cim_name: str) -> tuple[type, ...]:
    """Every SDK class (class, enum, compound, datatype) with this CIM name, canonical first."""
    r = _cand_cache.get(cim_name)
    if r is not None:
        return r
    from cim100 import _registry

    safe = _safe(cim_name)
    found: list[type] = []
    ref = _registry.BY_NAME.get(cim_name) or _registry.BY_NAME.get(safe)
    if ref is not None:
        cls = resolve(ref)
        if _cim_name(cls) == cim_name:
            found.append(cls)
    pattern = re.compile(re.escape(safe) + r"(_\d+)?")
    for other in _registry.BY_GUID.values():
        if pattern.fullmatch(other.rpartition(":")[2]):
            cls = resolve(other)
            if _cim_name(cls) == cim_name and cls not in found:
                found.append(cls)
    r = _cand_cache[cim_name] = tuple(found)
    return r


def resolve_class(cim_name: str) -> type | None:
    """The canonical SDK class for a CIM class name, or None (see the module docstring)."""
    try:
        return _class_cache[cim_name]
    except KeyError:
        pass
    cands = class_candidates(cim_name)
    cls = _class_cache[cim_name] = cands[0] if cands else None
    return cls


# --------------------------------------------------------------------------------------
# literals
# --------------------------------------------------------------------------------------


def literal_text(value: Any) -> str:
    """Text form of a primitive value (format-neutral)."""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "INF" if value > 0 else "-INF"
        return repr(value)
    if isinstance(value, int | Decimal):
        return str(value)
    if isinstance(value, _dt.datetime | _dt.date | _dt.time):
        return value.isoformat()
    if isinstance(value, CimDatatype):
        return literal_text(value.value)
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _parse_bool(s: str) -> bool:
    t = s.strip().lower()
    if t in ("true", "1"):
        return True
    if t in ("false", "0"):
        return False
    raise ValueError(f"not a boolean: {s!r}")


def _parse_date(s: str) -> _dt.date:
    s = s.strip()
    return _dt.date.fromisoformat(s.removesuffix("Z"))  # XSD allows a timezone suffix


_DECODERS: dict[str, Callable[[str], Any]] = {
    "str": lambda s: s,
    "float": lambda s: float(s.strip()),
    "int": lambda s: int(s.strip()),
    "bool": _parse_bool,
    "Decimal": lambda s: Decimal(s.strip()),
    "datetime": lambda s: _dt.datetime.fromisoformat(s.strip()),
    "date": _parse_date,
    "time": lambda s: _dt.time.fromisoformat(s.strip()),
}


def decode_literal(text: str, type_name: str) -> Any:
    """Parse `text` as the Python type `type_name` (``str float int bool Decimal datetime date
    time``). Raises ValueError or ArithmeticError when it does not parse."""
    return _DECODERS[type_name](text)


# --------------------------------------------------------------------------------------
# enums
# --------------------------------------------------------------------------------------


def enum_resource(member: Enum, namespace: str = CIM_NS) -> str:
    """``<ns><EnumCimName>.<literal>`` for an enum member."""
    return f"{namespace}{_cim_name(type(member))}.{member.value}"


def _strip_ns(resource: str, namespace: str | None) -> str:
    if namespace and resource.startswith(namespace):
        return resource[len(namespace) :]
    if "#" in resource:
        return resource.rpartition("#")[2]
    return resource


def decode_enum(
    resource: str, candidates: Iterable[type] = (), namespace: str | None = None
) -> Enum | None:
    """The enum member named by an enum resource, or None.

    `candidates` are the enum classes to try first (an attribute's declared enum, see
    `class_candidates`); otherwise the enum is found from the name in the resource.
    """
    s = _strip_ns(resource.strip(), namespace)
    tried = list(candidates)
    head = s.partition(".")[0]
    other = resolve_class(head) if head else None
    if other is not None and other not in tried:
        tried.append(other)
    for enum_cls in tried:
        if not (isinstance(enum_cls, type) and issubclass(enum_cls, CimEnum)):
            continue
        prefix = _cim_name(enum_cls) + "."
        if s.startswith(prefix):
            member = enum_cls._value2member_map_.get(s[len(prefix) :])
            if member is not None:
                return member  # type: ignore[return-value]
    return None


# --------------------------------------------------------------------------------------
# per-class plans
# --------------------------------------------------------------------------------------


class AttrSpec:
    """One serializable attribute of a class."""

    __slots__ = (
        "cim_name",
        "decode",
        "is_id",
        "kind",
        "meta",
        "name",
        "owner",
        "prop",
        "type_name",
    )

    def __init__(self, meta: AttrMeta, owner: str) -> None:
        self.meta = meta
        self.name = meta.name
        self.cim_name = meta.cim_name
        self.owner = owner
        self.prop = f"{owner}.{meta.cim_name}"
        self.kind = meta.kind
        self.type_name = meta.py_type
        self.is_id = meta.cim_name == "mRID" and owner == "IdentifiedObject"
        # literal parser: primitives by py_type, CIMDatatype by the datatype's value type
        self.decode: Callable[[str], Any] | None = None
        if meta.kind == "primitive":
            self.decode = _DECODERS.get(meta.py_type)
        elif meta.kind == "cimdatatype":
            dt = resolve_class(meta.py_type)
            vt = getattr(dt, "value_type", float)
            self.decode = _DECODERS.get(vt.__name__)

    def type_classes(self) -> tuple[type, ...]:
        """Enum or compound classes for this attribute (empty for literals)."""
        if self.kind in ("enumeration", "compound"):
            return class_candidates(self.type_name)
        return ()


class EndSpec:
    """One association end of a class."""

    __slots__ = ("desc", "many", "meta", "name", "owner", "prop", "role", "writes")

    def __init__(self, desc: _End[Any], owner: str) -> None:
        self.desc = desc
        self.meta: EndMeta = desc.meta
        self.name = desc.meta.name
        self.many = desc.meta.many
        self.owner = owner
        self.role = desc.meta.cim_role or desc.meta.name
        self.prop = f"{owner}.{self.role}"
        self.writes = is_write_end(desc)


class ClassPlan:
    """What a serializer needs to know about one class, computed once."""

    __slots__ = (
        "attrs",
        "by_prop",
        "cim_name",
        "cls",
        "defaulted",
        "ends",
        "many_descs",
        "mrid_name",
        "one_descs",
        "static_props",
    )

    cls: type
    cim_name: str
    attrs: tuple[AttrSpec, ...]  # writable attributes, sorted by property name
    ends: tuple[EndSpec, ...]  # sorted by property name
    by_prop: dict[str, AttrSpec | EndSpec]  # includes ancestor-qualified names of overrides
    static_props: frozenset[str]
    mrid_name: str | None  # Python name of the mRID attribute, if the class has one
    defaulted: tuple[str, ...]  # attribute names whose constructor default is not None
    one_descs: tuple[_End[Any], ...]  # for graph traversal
    many_descs: tuple[_End[Any], ...]


_plans: dict[type, ClassPlan] = {}


def class_plan(cls: type) -> ClassPlan:
    """The cached `ClassPlan` of an SDK class, enum-free (classes and compounds)."""
    plan = _plans.get(cls)
    if plan is not None:
        return plan
    metas = all_metas(cls)
    eff: dict[str, AttrSpec] = {}
    static: set[str] = set()
    for m in metas:
        for a in m.attributes:
            if a.static:
                static.add(f"{m.cim_name}.{a.cim_name}")
                continue
            eff[a.name] = AttrSpec(a, m.cim_name)
    by_prop: dict[str, AttrSpec | EndSpec] = {}
    for m in metas:
        for a in m.attributes:
            if not a.static:
                by_prop.setdefault(f"{m.cim_name}.{a.cim_name}", eff[a.name])
    attrs = tuple(sorted(eff.values(), key=lambda s: s.prop))
    for s in attrs:
        by_prop[s.prop] = s
    ends: list[EndSpec] = []
    for m in metas:
        for e in m.ends:
            ends.append(EndSpec(getattr(cls, e.name), m.cim_name))
    ends.sort(key=lambda s: s.prop)
    for es in ends:
        by_prop[es.prop] = es
    mrid = next((s.name for s in attrs if s.is_id), None)
    plan = ClassPlan.__new__(ClassPlan)
    plan.cls = cls
    plan.cim_name = _cim_name(cls)
    plan.attrs = attrs
    plan.ends = tuple(ends)
    plan.by_prop = by_prop
    plan.static_props = frozenset(static)
    plan.mrid_name = mrid
    plan.defaulted = tuple(s.name for s in attrs if s.meta.default is not None)
    plan.one_descs = tuple(s.desc for s in ends if not s.many)
    plan.many_descs = tuple(s.desc for s in ends if s.many)
    _plans[cls] = plan
    return plan


def resolve_property(cls: type, prop: str) -> AttrSpec | EndSpec | None:
    """The attribute or end of `cls` (inherited ones included) named by ``Declaring.cimName``."""
    return class_plan(cls).by_prop.get(prop)


# --------------------------------------------------------------------------------------
# association direction
# --------------------------------------------------------------------------------------

_write_cache: dict[int, bool] = {}


def _end_key(end: _End[Any]) -> str:
    return f"{_cim_name(end.owner)}.{end.meta.cim_role or end.meta.name}"


def association_write_end(end: _End[Any] | EndMeta, owner: type | None = None) -> _End[Any]:
    """The end (descriptor) from which the association of `end` is written.

    `end` is the descriptor (``Terminal.conducting_equipment``) or, with `owner` given, its
    ``EndMeta``. The single-valued end wins over a many end; for 1:1 and N:M the end whose
    ``<OwnerCimName>.<Role>`` sorts first (ties by Python name) wins.
    """
    if isinstance(end, EndMeta):
        if owner is None:
            raise TypeError("association_write_end(EndMeta) needs the owner class")
        desc: _End[Any] = getattr(owner, end.name)
    else:
        desc = end
    inv = desc.inverse
    if desc.meta.many != inv.meta.many:
        return inv if desc.meta.many else desc
    a, b = (_end_key(desc), desc.name), (_end_key(inv), inv.name)
    return desc if a <= b else inv


def is_write_end(end: _End[Any]) -> bool:
    """True when `end` is the one that carries its association (cached)."""
    r = _write_cache.get(id(end))
    if r is None:
        r = _write_cache[id(end)] = association_write_end(end) is end
    return r


# --------------------------------------------------------------------------------------
# collection and ids
# --------------------------------------------------------------------------------------


def _content_key(obj: CimObject, plan: ClassPlan) -> tuple[Any, ...]:
    attrs = tuple(repr(getattr(obj, s.name, None)) for s in plan.attrs)
    links = []
    for s in plan.ends:
        v = s.desc.__get__(obj)  # type: ignore[attr-defined]
        for t in v if s.many else (() if v is None else (v,)):
            m = getattr(t, "mrid", None)
            if m is not None:
                links.append(f"{s.prop}={m}")
    return (attrs, tuple(sorted(links)))


def collect(objects: Iterable[CimObject], include_reachable: bool = True) -> list[CimObject]:
    """The roots (plus everything reachable through association ends), deduplicated and
    sorted by ``(CIM class name, id)``; ``include_reachable=False`` keeps only the roots."""
    seen: dict[CimObject, None] = {}
    stack: list[CimObject] = []
    for o in objects:
        if not isinstance(o, CimObject):
            raise TypeError(f"not a CIM object: {o!r}")
        if o not in seen:
            seen[o] = None
            stack.append(o)
    if include_reachable:
        i = 0
        while i < len(stack):  # encounter order is deterministic (breadth first)
            obj = stack[i]
            i += 1
            plan = class_plan(type(obj))
            for d in plan.one_descs:
                t = d.__get__(obj)  # type: ignore[attr-defined]
                if t is not None and t not in seen:
                    seen[t] = None
                    stack.append(t)
            for d in plan.many_descs:
                for t in d.__get__(obj):  # type: ignore[attr-defined]
                    if t not in seen:
                        seen[t] = None
                        stack.append(t)
    keyed = []
    for n, obj in enumerate(stack):
        plan = class_plan(type(obj))
        mrid = getattr(obj, "mrid", None)
        if isinstance(mrid, str):
            keyed.append(((plan.cim_name, mrid, ()), n, obj))
        else:
            keyed.append(((plan.cim_name, "", _content_key(obj, plan)), n, obj))
    keyed.sort(key=lambda k: (k[0], k[1]))
    return [k[2] for k in keyed]


def assign_ids(objects: list[CimObject]) -> dict[CimObject, str]:
    """Id of every object (see the module docstring); `objects` should come from `collect`."""
    ids: dict[CimObject, str] = {}
    taken: dict[str, CimObject] = {}
    for obj in objects:
        mrid = getattr(obj, "mrid", None)
        if isinstance(mrid, str):
            other = taken.get(mrid)
            if other is not None and other is not obj:
                raise ValueError(f"duplicate id {mrid!r}: {other!r} and {obj!r}")
            taken[mrid] = obj
            ids[obj] = mrid
    n = 0
    for obj in objects:
        if obj not in ids:
            while f"gen{n}" in taken:
                n += 1
            ids[obj] = f"gen{n}"
            taken[f"gen{n}"] = obj
            n += 1
    return ids


# --------------------------------------------------------------------------------------
# value encoding and the canonical dump
# --------------------------------------------------------------------------------------


def encode_value(value: Any, namespace: str = CIM_NS) -> str | dict[str, Any]:
    """Format-neutral form of an attribute value: a string for primitives and enums (the enum
    resource), a ``{property: encoded}`` dict for a compound (unset members omitted)."""
    if isinstance(value, CimEnum):
        return enum_resource(value, namespace)
    if isinstance(value, CimCompound):
        out: dict[str, Any] = {}
        for s in class_plan(type(value)).attrs:
            v = getattr(value, s.name, None)
            if v is not None:
                out[s.prop] = encode_value(v, namespace)
        return out
    return literal_text(value)


def canonical_dump(
    objects: Iterable[CimObject], include_reachable: bool = True
) -> list[dict[str, Any]]:
    """A comparable description of a graph: per object (sorted) its class, id, encoded
    attribute values and, per end (both directions), the sorted ids of the linked objects.
    Links to objects outside the collected set are left out."""
    objs = collect(objects, include_reachable)
    ids = assign_ids(objs)
    out: list[dict[str, Any]] = []
    for obj in objs:
        plan = class_plan(type(obj))
        attrs = {}
        for s in plan.attrs:
            v = getattr(obj, s.name, None)
            if v is not None and not s.is_id:
                attrs[s.prop] = encode_value(v)
        links = {}
        for es in plan.ends:
            v = es.desc.__get__(obj)  # type: ignore[attr-defined]
            targets = v if es.many else (() if v is None else (v,))
            tids = sorted(ids[t] for t in targets if t in ids)
            if tids:
                links[es.prop] = tids
        out.append({"class": plan.cim_name, "id": ids[obj], "attrs": attrs, "links": links})
    return out
