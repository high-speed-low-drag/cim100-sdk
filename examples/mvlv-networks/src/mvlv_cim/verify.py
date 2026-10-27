"""Round-trip verification: build, write, read back, compare."""

from __future__ import annotations

import tempfile
import time
import warnings
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from cim100.serialization import read_cimxml, read_jsonld
from cim100.serialization._common import canonical_dump

from mvlv_cim.builder import BuiltNetwork, build_network
from mvlv_cim.export import Workbook, make_header, out_path, write_files

_READERS = {"cimxml": read_cimxml, "jsonld": read_jsonld}
FMT_LIST = ("cimxml", "jsonld")


@dataclass
class FormatResult:
    size: int = 0
    write_s: float = 0.0
    read_s: float = 0.0
    equal: bool = False
    deterministic: bool = False
    warnings: list[str] = field(default_factory=list)
    dangling: int = 0
    diff: str = ""


@dataclass
class NetworkResult:
    workbook: Workbook
    counts: Counter[str]
    n_objects: int
    formats: dict[str, FormatResult]
    cross_equal: bool

    @property
    def ok(self) -> bool:
        return self.cross_equal and all(
            r.equal and r.deterministic and not r.warnings and r.dangling == 0
            for r in self.formats.values()
        )


def describe_diff(a: list[dict], b: list[dict], limit: int = 3) -> str:
    """A short description of the first differences between two canonical dumps."""
    if a == b:
        return ""
    out = [f"{len(a)} vs {len(b)} objects"]
    ia = {(d["class"], d["id"]): d for d in a}
    ib = {(d["class"], d["id"]): d for d in b}
    only_a, only_b = sorted(set(ia) - set(ib)), sorted(set(ib) - set(ia))
    if only_a or only_b:
        out.append(
            f"only in first: {len(only_a)} {only_a[:limit]}; "
            f"only in second: {len(only_b)} {only_b[:limit]}"
        )
    n = 0
    for k in sorted(set(ia) & set(ib)):
        if ia[k] != ib[k]:
            out.append(f"{k}: {ia[k]} != {ib[k]}")
            n += 1
            if n >= limit:
                break
    return "\n".join(out)


def verify_built(
    wb: Workbook, net: BuiltNetwork, out: Path, formats=FMT_LIST, created: str | None = None
) -> NetworkResult:
    header = make_header(wb, net, created)
    built_dump = canonical_dump(net.objects)
    results: dict[str, FormatResult] = {}
    read_dumps: dict[str, list[dict]] = {}
    for fmt in formats:
        res = FormatResult()
        path = out_path(out, wb, fmt)
        t0 = time.perf_counter()
        res.warnings += write_files(net, header, {fmt: path})
        res.write_s = time.perf_counter() - t0
        res.size = path.stat().st_size
        t0 = time.perf_counter()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            doc = _READERS[fmt](path)
        res.read_s = time.perf_counter() - t0
        res.warnings += [f"{fmt} read: {w}" for w in doc.warnings]
        res.warnings += [f"{fmt} read: {w.message}" for w in caught]
        res.dangling = len(doc.dangling)
        dump = canonical_dump(doc.objects)
        read_dumps[fmt] = dump
        res.equal = dump == built_dump
        res.diff = describe_diff(built_dump, dump)
        with tempfile.TemporaryDirectory() as tmp:
            p2 = Path(tmp) / path.name
            write_files(net, header, {fmt: p2})
            res.deterministic = p2.read_bytes() == path.read_bytes()
        results[fmt] = res
    cross = len(read_dumps) < 2 or read_dumps["cimxml"] == read_dumps["jsonld"]
    return NetworkResult(wb, net.counts, len(net.objects), results, cross)


def verify_network(
    wb: Workbook, out: Path, formats=FMT_LIST, created: str | None = None
) -> NetworkResult:
    return verify_built(wb, build_network(wb.path), out, formats, created)
