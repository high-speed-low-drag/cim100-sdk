"""Serialization of CIM object graphs (generic, driven by ``_cim_meta``).

``write_cimxml``, ``read_cimxml`` and ``to_cimxml_string`` handle IEC 61970-552 RDF/XML.
"""

from cim100.serialization.cimxml import (
    CimDocument,
    CimXmlError,
    read_cimxml,
    to_cimxml_string,
    write_cimxml,
)

__all__ = ["CimDocument", "CimXmlError", "read_cimxml", "to_cimxml_string", "write_cimxml"]
