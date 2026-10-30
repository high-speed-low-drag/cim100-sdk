"""Read the pinned CGMES 3.0 OWL files and write src/cim100/profiles/data/cgmes_3_0.json.

Usage: dump_profiles.py [--out PATH] [--check]
  --check  do not write; exit 1 if the snapshot on disk differs from a fresh read.

Snapshot schema (keys sorted; URIs compacted to `prefix:Local` with the `namespaces` table):
  source: {repo, commit, license}
  namespaces: {prefix: namespace URI}
  profiles: {keyword: {keyword, name, file, uri, version, base, comment,
                       orphan_properties: ["cim:Class.prop", ...],
                       classes: {CIM name: class}}}
  class: {ns, super, concrete, enumeration, stereotypes, literals (list or null = all),
          min_instances, properties: {"Class.prop": property}}
  property: {ns, kind ("attribute"/"association"/null), min, max (null = CIM multiplicity),
             range, range_kind ("datatype"/"enumeration"/"compound"/"class"/null),
             targets (profile classes allowed as range), stereotypes}
A property sits under the class that owns it in the profile, which is the side written in CIMXML.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from codegen.owl_reader import OwlClass, OwlProfile, OwlProperty, read_owl, split_uri
from codegen.profile_source import ensure_profiles, load_source_config

SNAPSHOT = ROOT / "src" / "cim100" / "profiles" / "data" / "cgmes_3_0.json"
NAMESPACES = {
    "cim": "http://iec.ch/TC57/CIM100#",
    "eu": "http://iec.ch/TC57/CIM100-European#",
    "cim15": "http://iec.ch/TC57/2010/CIM-schema-cim15#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}
_PREFIX = {v: k for k, v in NAMESPACES.items()}


def prefix(ns: str | None) -> str | None:
    return None if ns is None else _PREFIX.get(ns, ns)


def compact(uri: str | None) -> str | None:
    if uri is None:
        return None
    ns, local = split_uri(uri)
    p = _PREFIX.get(ns)
    return f"{p}:{local}" if p else uri


def _prop(p: OwlProperty) -> dict:
    return {
        "ns": prefix(p.namespace),
        "kind": p.kind,
        "min": p.min,
        "max": p.max,
        "range": compact(p.range),
        "range_kind": p.range_kind,
        "targets": list(p.targets),
        "stereotypes": list(p.stereotypes),
    }


def _cls(c: OwlClass) -> dict:
    return {
        "ns": prefix(c.namespace),
        "super": c.superclass,
        "concrete": c.concrete,
        "enumeration": c.enumeration,
        "stereotypes": list(c.stereotypes),
        "literals": None if c.literals is None else list(c.literals),
        "min_instances": c.min_instances,
        "properties": {p.name: _prop(p) for p in c.properties},
    }


def profile_entry(entry: dict, prof: OwlProfile) -> dict:
    return {
        "keyword": entry["keyword"],
        "name": prof.name,
        "file": entry["file"],
        "uri": entry["uri"],
        "version": entry["version"],
        "base": prof.base,
        "comment": prof.comment,
        "orphan_properties": [f"{prefix(ns)}:{name}" for ns, name in prof.orphan_properties],
        "classes": {c.name: _cls(c) for c in prof.classes},
    }


def build_snapshot(config: dict, paths: dict[str, Path]) -> dict:
    return {
        "source": {k: config[k] for k in ("repo", "commit", "license")},
        "namespaces": NAMESPACES,
        "profiles": {
            e["keyword"]: profile_entry(e, read_owl(paths[e["keyword"]]))
            for e in config["profiles"]
        },
    }


def snapshot_text(snapshot: dict) -> str:
    return json.dumps(snapshot, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", type=Path, default=SNAPSHOT)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    config = load_source_config()
    snap = build_snapshot(config, ensure_profiles(config=config))
    text = snapshot_text(snap)
    if args.check:
        same = args.out.is_file() and args.out.read_text(encoding="utf-8") == text
        print("snapshot up to date" if same else f"snapshot differs: {args.out}")
        return 0 if same else 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"wrote {args.out} ({args.out.stat().st_size:,} bytes)")
    for kw, p in snap["profiles"].items():
        props = sum(len(c["properties"]) for c in p["classes"].values())
        print(
            f"  {kw:5} {p['name']:22} classes {len(p['classes']):4}  properties {props:4}"
            f"  orphans {len(p['orphan_properties']):3}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
