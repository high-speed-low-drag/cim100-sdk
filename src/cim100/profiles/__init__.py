"""Profiles over the cim100 classes: which classes and properties a profile carries, and
validation of objects against selected profiles.

    from cim100.profiles import cgmes3, validate_profile

    cgmes3.EQ.required(cim100.ACLineSegment)         # r, x, bch, ... (PropertyInfo)
    cgmes3.profiles_of(cim100.Terminal, "connected")  # (SSH,)
    validate_profile(objects, [cgmes3.EQ, cgmes3.TP])

`cim100.profiles.cgmes3` is the CGMES 3.0 profile set and, at the same time, a facade that
re-exports exactly the CGMES 3.0 classes (``from cim100.profiles.cgmes3 import ACLineSegment``).
Further profile sets load with ``ProfileSet.load("<snapshot>.json", "<name>")``.
"""

from cim100.profiles._model import Profile, ProfileSet, PropertyInfo
from cim100.profiles._validate import ProfileIssue, validate_profile

__all__ = [
    "Profile",
    "ProfileIssue",
    "ProfileSet",
    "PropertyInfo",
    "validate_profile",
]
