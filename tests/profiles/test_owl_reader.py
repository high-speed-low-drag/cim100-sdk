import pytest

from codegen.owl_reader import OwlError, parse_triples, read_owl

CIM = "http://iec.ch/TC57/CIM100#"
EU = "http://iec.ch/TC57/CIM100-European#"
XSD = "http://www.w3.org/2001/XMLSchema#"

# A tiny CIMTool-style profile using every convention the reader handles.
OWL = b"""<?xml version="1.0"?>
<rdf:RDF
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:owl="http://www.w3.org/2002/07/owl#"
    xmlns:uml="http://langdale.com.au/2005/UML#"
    xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
  xml:base="http://ucaiug.org/ns/CGMES/Tiny-EU/3.0">
  <rdf:Description rdf:about="">
    <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#Ontology"/>
    <rdfs:label>Tiny</rdfs:label>
    <rdfs:comment> A tiny profile. </rdfs:comment>
    <owl:imports rdf:resource="http://iec.ch/TC57/CIM100"/>
  </rdf:Description>
  <rdf:Description rdf:about="#IdentifiedObject">
    <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#Class"/>
    <rdfs:subClassOf rdf:resource="http://iec.ch/TC57/CIM100#IdentifiedObject"/>
    <rdfs:subClassOf rdf:nodeID="name_r"/>
    <rdfs:subClassOf rdf:nodeID="short_r"/>
  </rdf:Description>
  <rdf:Description rdf:nodeID="name_r">
    <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#Restriction"/>
    <owl:onProperty rdf:resource="http://iec.ch/TC57/CIM100#IdentifiedObject.name"/>
    <owl:allValuesFrom rdf:nodeID="name_t"/>
  </rdf:Description>
  <rdf:Description rdf:nodeID="name_t">
    <uml:hasStereotype rdf:resource="http://langdale.com.au/2005/UML#attribute"/>
    <rdf:type rdf:resource="http://www.w3.org/2000/01/rdf-schema#Datatype"/>
    <owl:equivalentClass rdf:resource="http://www.w3.org/2001/XMLSchema#string"/>
  </rdf:Description>
  <rdf:Description rdf:nodeID="short_r">
    <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#Restriction"/>
    <owl:onProperty rdf:resource="http://iec.ch/TC57/CIM100-European#IdentifiedObject.shortName"/>
    <owl:allValuesFrom rdf:nodeID="short_t"/>
  </rdf:Description>
  <rdf:Description rdf:nodeID="short_t">
    <uml:hasStereotype rdf:resource="http://langdale.com.au/2005/UML#attribute"/>
    <uml:hasStereotype rdf:resource="http://langdale.com.au/2005/UML#european"/>
    <rdf:type rdf:resource="http://www.w3.org/2000/01/rdf-schema#Datatype"/>
    <owl:equivalentClass rdf:resource="http://www.w3.org/2001/XMLSchema#string"/>
  </rdf:Description>
  <owl:Class rdf:about="#Terminal">
    <uml:hasStereotype rdf:resource="http://langdale.com.au/2005/UML#concrete"/>
    <uml:hasStereotype rdf:resource="http://langdale.com.au/2005/UML#description"/>
    <rdfs:subClassOf rdf:resource="http://iec.ch/TC57/CIM100#Terminal"/>
    <rdfs:subClassOf rdf:resource="#IdentifiedObject"/>
    <rdfs:subClassOf rdf:resource="#Terminal"/>
    <rdfs:subClassOf rdf:nodeID="tn_min"/>
    <rdfs:subClassOf rdf:nodeID="tn_max"/>
    <rdfs:subClassOf rdf:nodeID="tn_all"/>
    <rdfs:subClassOf rdf:nodeID="phases_all"/>
    <rdfs:subClassOf rdf:nodeID="uf_min"/>
  </owl:Class>
  <rdf:Description rdf:nodeID="tn_min">
    <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#Restriction"/>
    <owl:minCardinality rdf:datatype="http://www.w3.org/2001/XMLSchema#int">1</owl:minCardinality>
    <owl:onProperty rdf:resource="http://iec.ch/TC57/CIM100#Terminal.TopologicalNode"/>
  </rdf:Description>
  <rdf:Description rdf:nodeID="tn_max">
    <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#Restriction"/>
    <owl:maxCardinality rdf:datatype="http://www.w3.org/2001/XMLSchema#int">1</owl:maxCardinality>
    <owl:onProperty rdf:resource="http://iec.ch/TC57/CIM100#Terminal.TopologicalNode"/>
  </rdf:Description>
  <rdf:Description rdf:nodeID="tn_all">
    <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#Restriction"/>
    <owl:onProperty rdf:resource="http://iec.ch/TC57/CIM100#Terminal.TopologicalNode"/>
    <owl:allValuesFrom rdf:nodeID="tn_t"/>
  </rdf:Description>
  <rdf:Description rdf:nodeID="tn_t">
    <uml:hasStereotype rdf:resource="http://langdale.com.au/2005/UML#byreference"/>
    <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#Class"/>
    <rdfs:subClassOf rdf:resource="http://iec.ch/TC57/CIM100#TopologicalNode"/>
    <owl:unionOf rdf:nodeID="tn_l1"/>
  </rdf:Description>
  <rdf:Description rdf:nodeID="tn_l1">
    <rdf:first rdf:resource="#TopologicalNode"/>
    <rdf:rest rdf:resource="http://www.w3.org/1999/02/22-rdf-syntax-ns#nil"/>
  </rdf:Description>
  <rdf:Description rdf:nodeID="phases_all">
    <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#Restriction"/>
    <owl:onProperty rdf:resource="http://iec.ch/TC57/CIM100#Terminal.phases"/>
    <owl:allValuesFrom rdf:nodeID="phases_t"/>
  </rdf:Description>
  <rdf:Description rdf:nodeID="phases_t">
    <uml:hasStereotype rdf:resource="http://langdale.com.au/2005/UML#attribute"/>
    <uml:hasStereotype rdf:resource="http://langdale.com.au/2005/UML#enumeration"/>
    <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#Class"/>
    <rdfs:subClassOf rdf:resource="http://iec.ch/TC57/CIM100#PhaseCode"/>
    <rdfs:subClassOf rdf:resource="#PhaseCode"/>
  </rdf:Description>
  <rdf:Description rdf:nodeID="uf_min">
    <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#Restriction"/>
    <owl:minCardinality rdf:datatype="http://www.w3.org/2001/XMLSchema#int">1</owl:minCardinality>
    <owl:onProperty rdf:resource="http://iec.ch/TC57/CIM100#Terminal.uf"/>
  </rdf:Description>
  <rdf:Description rdf:about="#TopologicalNode">
    <uml:hasStereotype rdf:resource="http://langdale.com.au/2005/UML#concrete"/>
    <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#Class"/>
    <uml:hasMinCardinality>1</uml:hasMinCardinality>
    <rdfs:subClassOf rdf:resource="http://iec.ch/TC57/CIM100#TopologicalNode"/>
    <rdfs:subClassOf rdf:resource="#IdentifiedObject"/>
  </rdf:Description>
  <rdf:Description rdf:about="#PhaseCode">
    <uml:hasStereotype rdf:resource="http://langdale.com.au/2005/UML#enumeration"/>
    <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#Class"/>
    <rdfs:subClassOf rdf:resource="http://iec.ch/TC57/CIM100#PhaseCode"/>
    <owl:oneOf rdf:nodeID="pc_1"/>
  </rdf:Description>
  <rdf:Description rdf:nodeID="pc_1">
    <rdf:first rdf:resource="http://iec.ch/TC57/CIM100#PhaseCode.ABC"/>
    <rdf:rest rdf:nodeID="pc_2"/>
  </rdf:Description>
  <rdf:Description rdf:nodeID="pc_2">
    <rdf:first rdf:resource="http://iec.ch/TC57/CIM100#PhaseCode.A"/>
    <rdf:rest rdf:resource="http://www.w3.org/1999/02/22-rdf-syntax-ns#nil"/>
  </rdf:Description>
  <rdf:Description rdf:about="#BoundaryPoint">
    <uml:hasStereotype rdf:resource="http://langdale.com.au/2005/UML#concrete"/>
    <uml:hasStereotype rdf:resource="http://langdale.com.au/2005/UML#european"/>
    <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#Class"/>
    <rdfs:subClassOf rdf:resource="http://iec.ch/TC57/CIM100-European#BoundaryPoint"/>
    <rdfs:subClassOf rdf:resource="#IdentifiedObject"/>
  </rdf:Description>
  <rdf:Description rdf:nodeID="orphan_r">
    <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#Restriction"/>
    <owl:onProperty rdf:resource="http://iec.ch/TC57/CIM100#Voltage.value"/>
    <owl:minCardinality rdf:datatype="http://www.w3.org/2001/XMLSchema#int">1</owl:minCardinality>
  </rdf:Description>
  <rdf:Description rdf:about="http://iec.ch/TC57/CIM100#PhaseCode.B">
    <rdfs:label>B</rdfs:label>
  </rdf:Description>
</rdf:RDF>
"""


@pytest.fixture(scope="module")
def prof():
    return read_owl(OWL)


def test_ontology_header(prof):
    assert prof.name == "Tiny"
    assert prof.comment == "A tiny profile."
    assert prof.base == "http://ucaiug.org/ns/CGMES/Tiny-EU/3.0"
    assert prof.imports == ("http://iec.ch/TC57/CIM100",)


def test_classes(prof):
    assert [c.name for c in prof.classes] == [
        "BoundaryPoint",
        "IdentifiedObject",
        "PhaseCode",
        "Terminal",
        "TopologicalNode",
    ]
    term = prof.get("Terminal")
    assert term.namespace == CIM and term.superclass == "IdentifiedObject"  # self link ignored
    assert term.concrete and not term.enumeration
    assert term.stereotypes == ("concrete", "description")
    assert prof.get("BoundaryPoint").namespace == EU
    assert not prof.get("IdentifiedObject").concrete
    assert prof.get("IdentifiedObject").superclass is None
    assert prof.get("TopologicalNode").min_instances == 1


def test_enumeration_literals(prof):
    pc = prof.get("PhaseCode")
    assert pc.enumeration and pc.literals == ("ABC", "A")  # list order, unlinked label ignored
    assert prof.get("Terminal").literals is None


def test_attribute_properties(prof):
    name, short = prof.get("IdentifiedObject").properties
    assert (name.name, name.namespace, name.kind) == ("IdentifiedObject.name", CIM, "attribute")
    assert (name.min, name.max, name.range, name.range_kind) == (
        0,
        None,
        XSD + "string",
        "datatype",
    )
    assert short.namespace == EU and short.stereotypes == ("attribute", "european")


def test_association_and_enum_properties(prof):
    props = {p.name: p for p in prof.get("Terminal").properties}
    assert list(props) == ["Terminal.TopologicalNode", "Terminal.phases", "Terminal.uf"]
    tn = props["Terminal.TopologicalNode"]
    assert (tn.kind, tn.min, tn.max) == ("association", 1, 1)
    assert (tn.range, tn.range_kind, tn.targets) == (
        CIM + "TopologicalNode",
        "class",
        ("TopologicalNode",),
    )
    assert tn.stereotypes == ("byreference",)
    ph = props["Terminal.phases"]
    assert (ph.kind, ph.range, ph.range_kind, ph.targets) == (
        "attribute",
        CIM + "PhaseCode",
        "enumeration",
        ("PhaseCode",),
    )
    uf = props["Terminal.uf"]
    assert (uf.kind, uf.min, uf.range) == (None, 1, None)


def test_orphan_restrictions(prof):
    assert prof.orphan_properties == ((CIM, "Voltage.value"),)


def test_parse_triples_typed_node_element():
    graph, base = parse_triples(OWL)
    assert (
        "http://www.w3.org/2002/07/owl#Class"
        in graph["#Terminal"]["http://www.w3.org/1999/02/22-rdf-syntax-ns#type"]
    )
    assert base.endswith("Tiny-EU/3.0")


def test_errors():
    with pytest.raises(OwlError, match="not RDF/XML"):
        read_owl(b"<root/>")
    no_onto = b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"/>'
    with pytest.raises(OwlError, match="owl:Ontology"):
        read_owl(no_onto)
    two_super = OWL.replace(
        b'<rdfs:subClassOf rdf:resource="#Terminal"/>',
        b'<rdfs:subClassOf rdf:resource="#TopologicalNode"/>',
    )
    with pytest.raises(OwlError, match="Terminal super"):
        read_owl(two_super)
