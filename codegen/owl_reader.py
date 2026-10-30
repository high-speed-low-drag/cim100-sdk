"""Read a CIMTool profile OWL file (RDF/XML) into plain frozen dataclasses.

Conventions of the CGMES 3.0 CIMTool OWL files (cimug-org/CGMES-CIM17, checked on all 10 files):

- Flat RDF/XML: the root holds only `rdf:Description` elements, each with `rdf:about` (a named
  node) or `rdf:nodeID` (a blank node), and property children that carry `rdf:resource`,
  `rdf:nodeID` or literal text. Profile-local names are relative (`#Terminal`) to `xml:base`
  (`http://ucaiug.org/ns/CGMES/<Name>-EU/3.0`).
- The ontology is the node `rdf:about=""` with `rdf:type owl:Ontology`, `rdfs:label` (the profile
  name), optional `rdfs:comment` and `owl:imports <http://iec.ch/TC57/CIM100>`. It has no keyword,
  version or conformsTo URI (those come from profile-source.toml).
- A profile class is a named node `#X` with `rdf:type owl:Class` and `rdfs:subClassOf` pointing
  to (a) its CIM class (`cim:X` = `http://iec.ch/TC57/CIM100#X`, `eu:X` =
  `http://iec.ch/TC57/CIM100-European#X`), (b) at most one profile superclass `#Super` (a few
  classes also list themselves, which is ignored) and (c) one blank `owl:Restriction` per facet of
  each property. Class stereotypes (`uml:hasStereotype`): `concrete` (instantiable in the
  profile), `description` (instances describe objects defined in another profile, i.e. they are
  written with `rdf:about`), `enumeration`, `european`, `deprecated`.
  `uml:hasMinCardinality` on a class (only SV `TopologicalIsland`) is kept as `min_instances`.
- An enumeration class lists the literals the profile allows with `owl:oneOf` (an `rdf:first`/
  `rdf:rest` list of `cim:Kind.literal`). Most enumerations (all of EQ) have no `owl:oneOf`; then
  `literals` is None, meaning every literal of the CIM enumeration. Some files also carry
  `rdfs:label`s for literals that no list references; they are ignored.
- A property is the set of restrictions with the same `owl:onProperty` (full CIM URI whose local
  name is `Class.prop`) on one class. Facets: `owl:minCardinality` and `owl:maxCardinality`
  (`xsd:int` literals, only ever 1) and `owl:allValuesFrom` (the range, always a blank node). A
  missing max means the profile does not restrict the CIM multiplicity. The owning class is
  usually the property's domain, but EQ restates `OperationalLimit.*` on two of the limit
  classes too; the properties of a class are the union along its profile superclasses. A few
  properties have no `allValuesFrom` (SV `VsConverter.uf`, one SC property); their kind and
  range are None.
- Range kinds: an `rdfs:Datatype` with `owl:equivalentClass` (an `xsd:` type or a CIM datatype such
  as `cim:Voltage`) is an attribute. An `owl:Class` that is a subclass of the CIM range class plus
  an optional `owl:unionOf` list of profile classes (the allowed targets) is an attribute when it
  has the stereotype `enumeration` or `compound`, otherwise an association. Range stereotypes:
  `attribute`, `byreference` (the target is referenced, not nested), `european`, `deprecated`,
  `ofAggregate`/`aggregateOf`, `enumeration`, `compound`.
- Restrictions that no class references (SSH/SV datatype members such as `ActivePower.value` or
  `Simple_Float.value`, and stale CIM15 members in SC) are kept as `orphan_properties`.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
OWL = "http://www.w3.org/2002/07/owl#"
UML = "http://langdale.com.au/2005/UML#"
XML_BASE = "{http://www.w3.org/XML/1998/namespace}base"

_TYPE = RDF + "type"
_SUBCLASS = RDFS + "subClassOf"
_LABEL = RDFS + "label"
_STEREO = UML + "hasStereotype"


@dataclass(frozen=True)
class OwlProperty:
    name: str  # CIM local name "Class.prop"
    namespace: str  # e.g. "http://iec.ch/TC57/CIM100#"
    kind: str | None  # "attribute" / "association"; None without allValuesFrom
    min: int  # 0 or the owl:minCardinality
    max: int | None  # owl:maxCardinality; None = not restricted by the profile
    range: str | None  # full URI: xsd/CIM datatype, enumeration, compound or target class
    range_kind: str | None  # "datatype" / "enumeration" / "compound" / "class"
    targets: tuple[str, ...] = ()  # profile classes in the range's owl:unionOf (local names)
    stereotypes: tuple[str, ...] = ()  # of the range node, sorted


@dataclass(frozen=True)
class OwlClass:
    name: str  # CIM local name
    namespace: str | None  # namespace of the CIM class, None if the class has no CIM parent
    superclass: str | None  # profile superclass (local name)
    stereotypes: tuple[str, ...] = ()
    literals: tuple[str, ...] | None = None  # owl:oneOf literal names; None = all
    min_instances: int | None = None
    properties: tuple[OwlProperty, ...] = ()

    @property
    def concrete(self) -> bool:
        return "concrete" in self.stereotypes

    @property
    def enumeration(self) -> bool:
        return "enumeration" in self.stereotypes


@dataclass(frozen=True)
class OwlProfile:
    name: str  # rdfs:label of the ontology
    comment: str
    base: str  # xml:base
    imports: tuple[str, ...]
    classes: tuple[OwlClass, ...]
    orphan_properties: tuple[tuple[str, str], ...] = ()  # (namespace, "Class.prop"), sorted

    def get(self, name: str) -> OwlClass | None:
        return next((c for c in self.classes if c.name == name), None)


class OwlError(ValueError):
    pass


def split_uri(uri: str) -> tuple[str, str]:
    """('http://ns#', 'Local') for 'http://ns#Local'."""
    ns, sep, local = uri.rpartition("#")
    if not sep:
        raise OwlError(f"URI without '#': {uri}")
    return ns + "#", local


Graph = dict[str, dict[str, list]]


def parse_triples(source: str | Path | bytes) -> tuple[Graph, str]:
    """Parse flat RDF/XML into {subject: {predicate: [object, ...]}} and xml:base.

    Subjects and resource objects are URIs as written (relative `#X` kept), blank nodes are
    `_:id`, literals are `str`.
    """
    if isinstance(source, bytes):
        root = ET.fromstring(source)
    else:
        root = ET.parse(source).getroot()
    if root.tag != f"{{{RDF}}}RDF":
        raise OwlError(f"not RDF/XML: root element {root.tag}")
    graph: defaultdict[str, defaultdict[str, list]] = defaultdict(lambda: defaultdict(list))
    for el in root:
        about = el.get(f"{{{RDF}}}about")
        node_id = el.get(f"{{{RDF}}}nodeID")
        if about is not None:
            subject = about
        elif node_id is not None:
            subject = "_:" + node_id
        else:
            raise OwlError(f"node without rdf:about or rdf:nodeID: {el.tag}")
        if el.tag != f"{{{RDF}}}Description":  # typed node element
            graph[subject][_TYPE].append(el.tag[1:].replace("}", ""))
        for child in el:
            if len(child):
                raise OwlError(f"nested RDF/XML not supported under {subject}")
            pred = child.tag[1:].replace("}", "")
            res = child.get(f"{{{RDF}}}resource")
            ref = child.get(f"{{{RDF}}}nodeID")
            if res is not None:
                obj = res
            elif ref is not None:
                obj = "_:" + ref
            else:
                obj = child.text or ""
            graph[subject][pred].append(obj)
    return {k: dict(v) for k, v in graph.items()}, root.get(XML_BASE, "")


def _one(values: list, what: str) -> str | None:
    if len(values) > 1:
        raise OwlError(f"more than one {what}: {values}")
    return values[0] if values else None


def _stereotypes(node: dict) -> tuple[str, ...]:
    return tuple(sorted(split_uri(s)[1] for s in node.get(_STEREO, ())))


def _rdf_list(graph: Graph, head: str | None) -> list[str]:
    out: list[str] = []
    while head and head != RDF + "nil":
        node = graph.get(head)
        if node is None:
            raise OwlError(f"broken rdf:List at {head}")
        out.extend(node.get(RDF + "first", ()))
        head = _one(node.get(RDF + "rest", []), "rdf:rest")
    return out


def _local(ref: str) -> str:
    return ref[1:] if ref.startswith("#") else split_uri(ref)[1]


def _property(graph: Graph, prop_uri: str, facets: list[dict]) -> OwlProperty:
    ns, name = split_uri(prop_uri)
    mins = [int(v) for f in facets for v in f.get(OWL + "minCardinality", ())]
    maxs = [int(v) for f in facets for v in f.get(OWL + "maxCardinality", ())]
    ranges = [v for f in facets for v in f.get(OWL + "allValuesFrom", ())]
    lo = _one(mins, f"minCardinality on {name}")
    hi = _one(maxs, f"maxCardinality on {name}")
    rng = _one(ranges, f"allValuesFrom on {name}")
    if rng is None:
        return OwlProperty(name, ns, None, lo or 0, hi, None, None)
    node = graph.get(rng)
    if node is None:
        raise OwlError(f"range node {rng} of {name} missing")
    types = node.get(_TYPE, [])
    stereo = _stereotypes(node)
    if RDFS + "Datatype" in types:
        datatype = _one(node.get(OWL + "equivalentClass", []), f"datatype of {name}")
        return OwlProperty(name, ns, "attribute", lo or 0, hi, datatype, "datatype", (), stereo)
    if OWL + "Class" not in types:
        raise OwlError(f"range of {name} is neither rdfs:Datatype nor owl:Class")
    supers = node.get(_SUBCLASS, [])
    cim = [s for s in supers if not s.startswith(("#", "_:"))]
    union = _rdf_list(graph, _one(node.get(OWL + "unionOf", []), f"unionOf of {name}"))
    targets = tuple(sorted({_local(t) for t in union + [s for s in supers if s.startswith("#")]}))
    kind, range_kind = "association", "class"
    for k in ("enumeration", "compound"):
        if k in stereo:
            kind, range_kind = "attribute", k
    rng_cls = _one(cim, f"range class of {name}")
    return OwlProperty(name, ns, kind, lo or 0, hi, rng_cls, range_kind, targets, stereo)


def read_owl(source: str | Path | bytes) -> OwlProfile:
    """Read one CIMTool profile OWL file."""
    graph, base = parse_triples(source)
    onto = graph.get("")
    if onto is None or OWL + "Ontology" not in onto.get(_TYPE, []):
        raise OwlError("no owl:Ontology node (rdf:about='')")
    label = _one(onto.get(_LABEL, []), "ontology label")
    comment = _one(onto.get(RDFS + "comment", []), "ontology comment") or ""

    attached: set[str] = set()
    classes: list[OwlClass] = []
    for subj, node in graph.items():
        if not subj.startswith("#") or OWL + "Class" not in node.get(_TYPE, []):
            continue
        name = subj[1:]
        supers = node.get(_SUBCLASS, [])
        cim = _one([s for s in supers if not s.startswith(("#", "_:"))], f"CIM class of {name}")
        if cim is not None and split_uri(cim)[1] != name:
            raise OwlError(f"profile class #{name} refines {cim}")
        parent = _one([s[1:] for s in supers if s.startswith("#") and s != subj], f"{name} super")
        facets: dict[str, list[dict]] = defaultdict(list)
        for s in supers:
            if s.startswith("_:"):
                r = graph.get(s, {})
                if OWL + "Restriction" not in r.get(_TYPE, []):
                    raise OwlError(f"{name}: blank superclass {s} is not an owl:Restriction")
                facets[_one(r[OWL + "onProperty"], "onProperty")].append(r)
                attached.add(s)
        props = sorted((_property(graph, p, f) for p, f in facets.items()), key=lambda p: p.name)
        names = [p.name for p in props]
        if len(set(names)) != len(names):
            raise OwlError(f"{name}: one local property name in two namespaces")
        one_of = _one(node.get(OWL + "oneOf", []), f"oneOf of {name}")
        literals = None
        if one_of is not None:
            literals = tuple(split_uri(u)[1].split(".", 1)[1] for u in _rdf_list(graph, one_of))
        min_inst = _one(node.get(UML + "hasMinCardinality", []), f"{name} hasMinCardinality")
        classes.append(
            OwlClass(
                name=name,
                namespace=split_uri(cim)[0] if cim else None,
                superclass=parent,
                stereotypes=_stereotypes(node),
                literals=literals,
                min_instances=int(min_inst) if min_inst is not None else None,
                properties=tuple(props),
            )
        )

    orphans = {
        split_uri(_one(node[OWL + "onProperty"], "onProperty"))
        for subj, node in graph.items()
        if subj.startswith("_:")
        and OWL + "Restriction" in node.get(_TYPE, [])
        and subj not in attached
    }
    return OwlProfile(
        name=label or "",
        comment=comment.strip(),
        base=base,
        imports=tuple(sorted(onto.get(OWL + "imports", []))),
        classes=tuple(sorted(classes, key=lambda c: c.name)),
        orphan_properties=tuple(sorted(orphans)),
    )
