"""Serialization of CIM object graphs (generic, driven by ``_cim_meta``).

``write_cimxml``, ``read_cimxml`` and ``to_cimxml_string`` handle IEC 61970-552 RDF/XML;
``write_jsonld``, ``read_jsonld``, ``to_jsonld_string`` and ``to_jsonld_dict`` handle CIM JSON-LD.
Both readers return a `CimDocument`.
"""

from cim100.serialization._common import CimDocument
from cim100.serialization.cimxml import (
    CimXmlError,
    read_cimxml,
    to_cimxml_string,
    write_cimxml,
)
from cim100.serialization.jsonld import (
    CimJsonLdError,
    read_jsonld,
    to_jsonld_dict,
    to_jsonld_string,
    write_jsonld,
)

__all__ = [
    "CimDocument",
    "CimJsonLdError",
    "CimXmlError",
    "read_cimxml",
    "read_jsonld",
    "to_cimxml_string",
    "to_jsonld_dict",
    "to_jsonld_string",
    "write_cimxml",
    "write_jsonld",
]
