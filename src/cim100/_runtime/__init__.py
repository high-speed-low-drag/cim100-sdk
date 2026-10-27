"""Hand-written runtime used by the generated ``cim100.model`` package (see docs/RUNTIME.md).

Stdlib only; never imports the generated package at import time.
"""

from cim100._runtime.base import CimObject
from cim100._runtime.ends import Many, One
from cim100._runtime.meta import AttrMeta, ClassMeta, EndMeta, all_metas, cim_attributes, cim_ends
from cim100._runtime.mrid import new_mrid
from cim100._runtime.resolve import resolve
from cim100._runtime.values import CimCompound, CimDatatype, CimEnum

__all__ = [
    "AttrMeta",
    "CimCompound",
    "CimDatatype",
    "CimEnum",
    "CimObject",
    "ClassMeta",
    "EndMeta",
    "Many",
    "One",
    "all_metas",
    "cim_attributes",
    "cim_ends",
    "new_mrid",
    "resolve",
]
