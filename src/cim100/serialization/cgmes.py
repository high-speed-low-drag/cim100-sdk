"""CGMES 3.0 writer: one CIMXML file per profile (EQ, SSH, TP, SV, ...), driven by the profile
snapshot of `cim100.profiles` (``cgmes3``).

    from cim100.serialization.cgmes import CgmesHeader, write_cgmes

    report = write_cgmes(network, "out/", name="grid",
                         header=CgmesHeader(scenario_time=t, modeling_authority_set="http://x.eu/"))
    # out/grid_EQ.xml, out/grid_SSH.xml, out/grid_TP.xml, out/grid_SV.xml

`write_cgmes` writes to a directory, or into a zip when `out` ends with ``.zip``; `to_cgmes_strings`
returns ``{keyword: document}``. Value encoding (floats, booleans, dates, enum resources,
compounds) and wire ids follow `cim100.serialization._common`; this module only decides which
object, which property and which header goes into which file.

Conventions (verified against the ENTSO-E CGMES 3.0 conformity test configuration
"MicroGrid BaseCase" v3.0.2, BE and NL EQ/SSH/TP/SV files, as shipped in powsybl-core
``cgmes/cgmes-conformity/src/main/resources/conformity/cas-3-data-3.0.2/MicroGrid/BaseCase/``
at commit f6749ad368fba8dd3776099c040fed07023a1ba3, https://github.com/powsybl/powsybl-core; and
against powsybl-core's CGMES export, ``CgmesExportUtil.java`` / ``CgmesExport.java``, same commit)
------------------------------------------------------------------------------------------------
Root and namespaces
    ``rdf:RDF`` always declares ``cim`` (``http://iec.ch/TC57/CIM100#``), ``md``
    (``http://iec.ch/TC57/61970-552/ModelDescription/1#``), ``rdf`` and ``eu``
    (``http://iec.ch/TC57/CIM100-European#``), in this order, as the samples do (``eu`` even
    when unused). No ``dcat``/``dcterms``: CGMES 3.0 files use the IEC 61970-552:2016
    ``md:FullModel`` header, not the dcat header of later profiles.
Header (``md:FullModel``, IEC 61970-552:2016), first element, in the samples' order:
    ``rdf:about="urn:uuid:<model id>"``; ``md:Model.created``; ``md:Model.scenarioTime`` (both
    ``YYYY-MM-DDTHH:MM:SSZ``, UTC); ``md:Model.description``; ``md:Model.modelingAuthoritySet``;
    ``md:Model.profile`` (the profile URI, e.g. ``http://iec.ch/TC57/ns/CIM/CoreEquipment-EU/3.0``;
    repeatable: the sample EQ files also carry the ShortCircuit URI); ``md:Model.version``;
    ``md:Model.DependentOn`` and ``md:Model.Supersedes`` (``rdf:resource="urn:uuid:..."``).
    See `CgmesHeader`.
Dependencies (``md:Model.DependentOn``)
    The CGMES 3.0 samples chain the files: SSH -> EQ, TP -> SSH, SV -> TP (and EQ -> EQBD).
    powsybl's export uses the CGMES 2.4.15 pattern instead (TP -> EQ, SSH -> EQ, SV -> TP + SSH).
    This writer follows the samples. A profile whose preferred dependency is not written falls
    back to the next one (TP -> EQ without SSH; SV -> SSH, else EQ, without TP); DL, GL, OP and SC
    depend on EQ. Dependencies outside the written set (a boundary set) come from
    ``CgmesHeader.dependent_on``.
Ids
    An object is written with ``rdf:ID="_<mrid>"`` in a profile that defines it (its class is
    concrete there and not a ``description``: `ProfileSet.defining_profiles`) and with
    ``rdf:about="#_<mrid>"`` in every other profile. References are ``rdf:resource="#_<mrid>"``.
    ``cim:IdentifiedObject.mRID`` is written as an element (the plain mrid, no ``_``) in the
    defining file only, when the profile lists it for the class (the samples never repeat it in
    ``rdf:about`` elements; classes outside IdentifiedObject, e.g. ``SvPowerFlow``, have none).
    Objects without an mrid get ``_gen<N>`` as in the generic writer.
Objects and properties per file
    A file holds the profile's properties only (`Profile.properties`, Python name -> profile
    ``qname``, ``eu:`` for extensions). Every property value is written once over the whole
    file set: a description (``rdf:about``) element leaves out the properties that a profile
    defining the class lists (so TP terminals carry ``Terminal.TopologicalNode`` but not the EQ
    name), and among the written profiles the defining ones claim a property first, then the
    others in order. An object appears in a file when that file defines it, or when it has a
    value for one of the file's remaining properties. When the object's own class is not in the
    profile, it is described under its nearest profile ancestor that adds properties: the sample
    SSH files write ``<cim:Equipment rdf:about="#_<line>">`` with ``Equipment.inService`` for
    lines, transformers and busbars. Objects whose class is in no profile of the set are not
    written (reported).
Associations
    Written from the side the profile lists (`PropertyInfo.owner`), which differs from the
    generic writer's rule for e.g. SV ``TopologicalIsland.TopologicalNodes``. A reference may
    point at an object outside the written set (e.g. a boundary ConnectivityNode) when that
    object has an mrid.
Enumerations
    ``rdf:resource="<namespace><Enum>.<literal>"``; ``eu`` enums (``LimitKind``) use the ``eu``
    URI. File names default to ``<name>_<KEYWORD>.xml``; the ENTSO-E convention
    ``<scenarioTime>_<process>_<TSO>_<KEYWORD>_<version>.xml`` is available through
    ``file_name`` (fields ``name keyword version scenario``).

Reporting
    Before writing, `validate_profile` runs against the selected profiles (``validate=True``).
    Every property value, link or object that no written file carries is listed in
    `CgmesReport.dropped`. Without ``strict`` a single ``warnings.warn`` summarises validation
    errors and dropped data; ``strict=True`` raises `CgmesWriteError` instead, before anything
    is written.
"""

from __future__ import annotations

import datetime as _dt
import io
import os
import uuid
import warnings
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from cim100._runtime import CimObject
from cim100.profiles._model import Profile, ProfileSet
from cim100.profiles._validate import ProfileIssue, validate_profile
from cim100.serialization._common import (
    CIM_NS,
    EU_NS,
    assign_ids,
    class_plan,
    collect,
)
from cim100.serialization.cimxml import (
    MD_NS,
    RDF_NS,
    _serialize,
    _wire_ids,
    _write_value,
    _xml_text,
)

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from typing import Any

    from cim100.profiles._model import PropertyInfo

__all__ = [
    "DEFAULT_PROFILES",
    "CgmesHeader",
    "CgmesReport",
    "CgmesWriteError",
    "to_cgmes_strings",
    "write_cgmes",
]

DEFAULT_PROFILES = ("EQ", "SSH", "TP", "SV")
DEFAULT_MAS = "http://cim100-sdk.invalid/modelingAuthoritySet"

# preferred DependentOn, first written alternative wins (see the module docstring)
_DEPENDS: dict[str, tuple[tuple[str, ...], ...]] = {
    "EQ": (("EQBD",),),
    "SSH": (("EQ",),),
    "TP": (("SSH", "EQ"),),
    "SV": (("TP", "SSH", "EQ"),),
    "DL": (("EQ",),),
    "GL": (("EQ",),),
    "OP": (("EQ",),),
    "SC": (("EQ",),),
    "DY": (("SSH", "EQ"),),
}

_ROOT_NS = (("cim", CIM_NS), ("md", MD_NS), ("rdf", RDF_NS), ("eu", EU_NS))


class CgmesWriteError(ValueError):
    """Raised by ``strict=True`` for validation errors or data no written file carries."""


@dataclass(frozen=True)
class CgmesHeader:
    """Header (``md:FullModel``) values for a CGMES file set.

    Scalars apply to every file; ``overrides`` replaces them per profile keyword
    (``{"SSH": {"version": "2"}}``). ``model_ids`` fixes the model id of a file (``urn:uuid:``
    added to a bare UUID; default: a random UUID per file and call). ``dependent_on`` and
    ``supersedes`` add model ids per keyword (e.g. the boundary EQ for ``"EQ"``); dependencies
    between the files written together are added automatically unless ``auto_dependencies`` is
    false. ``profile_uris`` adds ``md:Model.profile`` URIs per keyword (a file holding EQ and SC
    data lists both). ``created`` defaults to now (UTC, one value for the call),
    ``scenario_time`` to ``created``; naive datetimes are taken as UTC.
    """

    scenario_time: _dt.datetime | None = None
    created: _dt.datetime | None = None
    modeling_authority_set: str = DEFAULT_MAS
    description: str | None = None
    version: str | int = "1"
    model_ids: Mapping[str, str] = field(default_factory=dict)
    dependent_on: Mapping[str, Sequence[str]] = field(default_factory=dict)
    supersedes: Mapping[str, Sequence[str]] = field(default_factory=dict)
    profile_uris: Mapping[str, Sequence[str]] = field(default_factory=dict)
    overrides: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    auto_dependencies: bool = True


@dataclass
class CgmesReport:
    """What `write_cgmes` wrote and what it could not place."""

    files: dict[str, str] = field(default_factory=dict)  # keyword -> file name / zip member
    model_ids: dict[str, str] = field(default_factory=dict)  # keyword -> urn:uuid:...
    headers: dict[str, dict[str, Any]] = field(default_factory=dict)  # keyword -> header items
    issues: list[ProfileIssue] = field(default_factory=list)  # validate_profile findings
    dropped: list[ProfileIssue] = field(default_factory=list)  # values no written file carries

    @property
    def errors(self) -> list[ProfileIssue]:
        return [i for i in self.issues if i.severity == "error"]


# --------------------------------------------------------------------------------------
# header
# --------------------------------------------------------------------------------------


def _utc(t: _dt.datetime) -> str:
    if t.tzinfo is not None:
        t = t.astimezone(_dt.UTC)
    return t.replace(tzinfo=None, microsecond=0).isoformat() + "Z"


def _urn(model_id: str) -> str:
    return model_id if ":" in model_id else f"urn:uuid:{model_id}"


def _header_items(
    header: CgmesHeader, profiles: Sequence[Profile], now: _dt.datetime
) -> dict[str, dict[str, Any]]:
    kws = [p.keyword for p in profiles]
    ids = {}
    for kw in kws:
        given = header.model_ids.get(kw)
        ids[kw] = _urn(given) if given else f"urn:uuid:{uuid.uuid4()}"
    out: dict[str, dict[str, Any]] = {}
    for p in profiles:
        kw = p.keyword
        o = dict(header.overrides.get(kw, {}))
        created = o.pop("created", header.created) or now
        scenario = o.pop("scenario_time", header.scenario_time) or created
        deps: list[str] = []
        if header.auto_dependencies:
            for alternatives in _DEPENDS.get(kw, ()):
                dep = next((d for d in alternatives if d in ids), None)
                if dep is not None:
                    deps.append(ids[dep])
        deps += [_urn(d) for d in header.dependent_on.get(kw, ())]
        items: dict[str, Any] = {
            "about": ids[kw],
            "created": _utc(created),
            "scenarioTime": _utc(scenario),
            "description": o.pop("description", header.description),
            "modelingAuthoritySet": o.pop("modeling_authority_set", header.modeling_authority_set),
            "profile": [p.uri, *header.profile_uris.get(kw, ())],
            "version": str(o.pop("version", header.version)),
            "DependentOn": list(dict.fromkeys(deps)),
            "Supersedes": [_urn(d) for d in header.supersedes.get(kw, ())],
        }
        if o:
            raise TypeError(f"unknown header override(s) for {kw}: {', '.join(sorted(o))}")
        out[kw] = items
    return out


def _header_element(items: dict[str, Any]) -> ET.Element:
    el = ET.Element("md:FullModel", {"rdf:about": items["about"]})
    for key, val in items.items():
        if key == "about" or val is None:
            continue
        for v in val if isinstance(val, list) else (val,):
            sub = ET.SubElement(el, f"md:Model.{key}")
            if key in ("DependentOn", "Supersedes"):
                sub.set("rdf:resource", v)
            else:
                sub.text = _xml_text(v, "header", f"Model.{key}")
    return el


# --------------------------------------------------------------------------------------
# per-class plans
# --------------------------------------------------------------------------------------


@dataclass
class _ClassPlan:
    tag: str  # element qname
    defining: bool
    mrid: bool  # write IdentifiedObject.mRID (defining and listed)
    props: tuple[PropertyInfo, ...]  # attributes and ends to write (mRID excluded)


def _plans_for(
    cls: type, profiles: Sequence[Profile], pset: ProfileSet
) -> dict[str, _ClassPlan | None]:
    """Per written profile keyword, how instances of `cls` are written there (None: never)."""
    if not pset.has_class(cls):
        return {p.keyword: None for p in profiles}
    defining_all = pset.defining_profiles(cls)
    defined_props = {i.name for d in defining_all for i in d.properties(cls)}
    order = sorted(profiles, key=lambda p: p not in defining_all)  # defining ones claim first
    claimed: set[str] = set()
    out: dict[str, _ClassPlan | None] = {}
    for p in order:
        el_cls = p.element_class(cls)
        if el_cls is None:
            out[p.keyword] = None
            continue
        defining = p in defining_all
        mrid = False
        props = []
        for info in p.properties(el_cls):
            if info.python_name is None:
                continue
            if info.name == "IdentifiedObject.mRID":
                mrid = defining
                continue
            if not defining and info.name in defined_props:
                continue
            if info.python_name in claimed:
                continue
            claimed.add(info.python_name)
            props.append(info)
        out[p.keyword] = _ClassPlan(class_plan(el_cls).qname, defining, mrid, tuple(props))
    return out


# --------------------------------------------------------------------------------------
# building
# --------------------------------------------------------------------------------------


def _select(
    profiles: Iterable[Profile | str] | Profile | str, pset: ProfileSet
) -> tuple[Profile, ...]:
    if isinstance(profiles, Profile | str):
        profiles = (profiles,)
    out = []
    for p in profiles:
        prof = pset.by_keyword(p) if isinstance(p, str) else p
        if not isinstance(prof, Profile):
            raise TypeError(f"not a Profile or keyword: {p!r}")
        if prof not in out:
            out.append(prof)
    if not out:
        raise ValueError("no profiles selected")
    return tuple(out)


def _default_set() -> ProfileSet:
    from cim100.profiles import cgmes3

    return cgmes3.profile_set  # type: ignore[no-any-return]


def _build(
    objects: Any,
    profiles: Iterable[Profile | str] | Profile | str,
    header: CgmesHeader | None,
    include_reachable: bool,
    validate: bool,
    strict: bool,
    profile_set: ProfileSet | None,
) -> tuple[dict[str, bytes], CgmesReport]:
    pset = profile_set if profile_set is not None else _default_set()
    selected = _select(profiles, pset)
    if isinstance(objects, CimObject):
        objects = [objects]
    objs = collect(objects, include_reachable)
    ids = assign_ids(objs)
    order = {o: i for i, o in enumerate(objs)}
    refs = {o: _wire_ids(i) for o, i in ids.items()}
    report = CgmesReport()
    if validate:
        report.issues = validate_profile(objs, selected, include_reachable=False)

    def ref_of(t: CimObject) -> str | None:
        r = refs.get(t)
        if r is not None:
            return r[1]
        m = getattr(t, "mrid", None)
        return _wire_ids(m)[1] if isinstance(m, str) else None

    plans: dict[type, dict[str, _ClassPlan | None]] = {}
    written_attrs: set[tuple[int, str]] = set()
    written_links: set[tuple[int, str, int]] = set()
    placed: set[int] = set()
    bodies: dict[str, list[ET.Element]] = {p.keyword: [] for p in selected}
    for obj in objs:
        cls = type(obj)
        per = plans.get(cls)
        if per is None:
            per = plans[cls] = _plans_for(cls, selected, pset)
        where = f"{class_plan(cls).cim_name} {ids[obj]!r}"
        for p in selected:
            plan = per[p.keyword]
            if plan is None:
                continue
            children: list[ET.Element] = []
            if plan.mrid and isinstance(getattr(obj, "mrid", None), str):
                mrid_el = ET.Element("cim:IdentifiedObject.mRID")
                mrid_el.text = _xml_text(obj.mrid, where, "IdentifiedObject.mRID")  # type: ignore[attr-defined]
                children.append(mrid_el)
            for info in plan.props:
                name = info.python_name
                assert name is not None
                if info.is_association:
                    desc = getattr(cls, name)
                    v = desc.__get__(obj)
                    targets = list(v) if info.many else ([] if v is None else [v])
                    targets.sort(key=lambda t: (order.get(t, len(order)), ref_of(t) or ""))
                    for t in targets:
                        r = ref_of(t)
                        if r is None:
                            continue
                        children.append(ET.Element(info.qname, {"rdf:resource": r}))
                        written_links.add((id(obj), name, id(t)))
                else:
                    v = getattr(obj, name, None)
                    if v is None:
                        continue
                    el = ET.Element(info.qname)
                    _write_value(el, v, CIM_NS, where, info.name)
                    children.append(el)
                    written_attrs.add((id(obj), name))
            if not plan.defining and not children:
                continue
            ident, ref = refs[obj]
            attrib = dict([ident]) if plan.defining else {"rdf:about": ref}
            el = ET.Element(plan.tag, attrib)
            el.extend(children)
            bodies[p.keyword].append(el)
            placed.add(id(obj))
    report.dropped = _dropped(objs, placed, written_attrs, written_links, ids)

    errors = report.errors
    if strict and (errors or report.dropped):
        lines = [str(i) for i in (errors + report.dropped)[:20]]
        more = len(errors) + len(report.dropped) - len(lines)
        tail = f"\n... and {more} more" if more > 0 else ""
        raise CgmesWriteError("CGMES export problems:\n" + "\n".join(lines) + tail)
    if errors or report.dropped:
        warnings.warn(
            f"CGMES export: {len(errors)} validation error(s), {len(report.dropped)} value(s) "
            f"not written in the selected profiles ({', '.join(p.keyword for p in selected)}); "
            f"see CgmesReport.issues / .dropped",
            stacklevel=3,
        )

    now = _dt.datetime.now(_dt.UTC)
    report.headers = _header_items(header or CgmesHeader(), selected, now)
    report.model_ids = {kw: h["about"] for kw, h in report.headers.items()}
    docs: dict[str, bytes] = {}
    for p in selected:
        root = ET.Element("rdf:RDF", {f"xmlns:{k}": v for k, v in _ROOT_NS})
        root.append(_header_element(report.headers[p.keyword]))
        root.extend(bodies[p.keyword])
        ET.indent(root, space="  ")
        docs[p.keyword] = _serialize(root)
    return docs, report


def _dropped(
    objs: list[CimObject],
    placed: set[int],
    written_attrs: set[tuple[int, str]],
    written_links: set[tuple[int, str, int]],
    ids: dict[CimObject, str],
) -> list[ProfileIssue]:
    out: list[ProfileIssue] = []
    for obj in objs:
        plan = class_plan(type(obj))
        if id(obj) not in placed:
            out.append(
                ProfileIssue("warning", obj, None, None,
                             f"{plan.cim_name} {ids[obj]!r} is in none of the written files")
            )  # fmt: skip
            continue
        for a in plan.attrs:
            if a.is_id:
                continue
            v = getattr(obj, a.name, None)
            if v is None or (a.meta.default is not None and v == a.meta.default):
                continue
            if (id(obj), a.name) not in written_attrs:
                out.append(ProfileIssue("warning", obj, None, a.prop, f"{a.prop} is not written"))
        for e in plan.ends:
            v = e.desc.__get__(obj)  # type: ignore[attr-defined]
            targets = v if e.many else (() if v is None else (v,))
            inv = e.desc.inverse.name  # type: ignore[attr-defined]
            missing = [
                t
                for t in targets
                if (id(obj), e.name, id(t)) not in written_links
                and (id(t), inv, id(obj)) not in written_links
            ]
            if missing:
                out.append(
                    ProfileIssue("warning", obj, None, e.prop,
                                 f"{e.prop} is not written ({len(missing)} link(s))")
                )  # fmt: skip
    return out


# --------------------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------------------


def to_cgmes_strings(
    objects: Any,
    *,
    profiles: Iterable[Profile | str] | Profile | str = DEFAULT_PROFILES,
    header: CgmesHeader | None = None,
    include_reachable: bool = True,
    validate: bool = True,
    strict: bool = False,
    profile_set: ProfileSet | None = None,
) -> dict[str, str]:
    """The CGMES documents as ``{keyword: CIMXML string}`` (same content as `write_cgmes`;
    problems are reported by ``warnings.warn``, or raised with ``strict=True``)."""
    docs, _ = _build(objects, profiles, header, include_reachable, validate, strict, profile_set)
    return {kw: d.decode("utf-8") for kw, d in docs.items()}


def write_cgmes(
    objects: Any,
    out: str | os.PathLike[str],
    *,
    profiles: Iterable[Profile | str] | Profile | str = DEFAULT_PROFILES,
    header: CgmesHeader | None = None,
    name: str = "model",
    file_name: str = "{name}_{keyword}.xml",
    include_reachable: bool = True,
    validate: bool = True,
    strict: bool = False,
    profile_set: ProfileSet | None = None,
) -> CgmesReport:
    """Write `objects` (and, by default, everything reachable) as a CGMES file set.

    `profiles` are keywords or `Profile` objects of `profile_set` (default: CGMES 3.0 EQ, SSH,
    TP, SV). `out` is a directory (created when missing) or a ``.zip`` file. Each file is named
    by `file_name`, formatted with ``name``, ``keyword``, ``version`` and ``scenario``
    (``YYYYMMDDTHHMMZ``). Returns a `CgmesReport` (file names, model ids, headers, validation
    issues, dropped values). See the module docstring for the conventions.
    """
    docs, report = _build(
        objects, profiles, header, include_reachable, validate, strict, profile_set
    )
    for kw, items in report.headers.items():
        scen = items["scenarioTime"].replace("-", "").replace(":", "")[:13] + "Z"
        report.files[kw] = file_name.format(
            name=name, keyword=kw, version=items["version"], scenario=scen
        )
    target = Path(out)
    if target.suffix.lower() == ".zip":
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for kw, data in docs.items():
                info = zipfile.ZipInfo(report.files[kw], date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, data)
        target.write_bytes(buf.getvalue())
    else:
        target.mkdir(parents=True, exist_ok=True)
        for kw, data in docs.items():
            (target / report.files[kw]).write_bytes(data)
    return report
