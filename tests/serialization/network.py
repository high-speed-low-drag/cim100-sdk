"""The rich CIM network shared by the CIMXML and JSON-LD tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import cim100


def _terminal(eq, seq, node, phases=cim100.PhaseCode.ABC):
    return cim100.Terminal(
        mrid=f"{eq.mrid}-t{seq}",
        name=f"{eq.name}-T{seq}",
        sequence_number=seq,
        phases=phases,
        conducting_equipment=eq,
        connectivity_node=node,
    )


def build_network() -> dict[str, object]:
    sub = cim100.Substation(name="Zone Sub", mrid="sub-1")
    bv = cim100.BaseVoltage(name="22kV", nominal_voltage=22000.0, mrid="bv-22")
    vl = cim100.VoltageLevel(name="22kV bus", substation=sub, base_voltage=bv, mrid="vl-1")
    cn1 = cim100.ConnectivityNode(name="CN1", connectivity_node_container=vl, mrid="cn-1")
    cn2 = cim100.ConnectivityNode(name="CN2", connectivity_node_container=vl, mrid="cn-2")
    cn3 = cim100.ConnectivityNode(name="CN3", connectivity_node_container=vl, mrid="cn-3")
    feeder = cim100.Feeder(name="F1", normal_energizing_substation=sub, mrid="feeder-1")
    imp = cim100.PerLengthSequenceImpedance(name="Z", r=0.3, x=0.4, bch=1e-6, mrid="plsi-1")
    line = cim100.ACLineSegment(
        name="Line", length=12.5, per_length_impedance=imp, base_voltage=bv,
        equipment_container=feeder, in_service=True, mrid="line-1",
    )  # fmt: skip
    t1 = _terminal(line, 1, cn1)
    t2 = _terminal(line, 2, cn2)
    phase = cim100.ACLineSegmentPhase(
        name="phase A", phase=cim100.SinglePhaseKind.A, sequence_number=1,
        ac_line_segment=line, mrid="phase-1",
    )  # fmt: skip
    tx = cim100.PowerTransformer(name="Tx", vector_group=None, equipment_container=sub, mrid="tx-1")
    tt1 = _terminal(tx, 1, cn2)
    tt2 = _terminal(tx, 2, cn3)
    e1 = cim100.PowerTransformerEnd(
        name="End1", end_number=1, rated_u=22000.0, rated_s=5e6, r=1.5, power_transformer=tx,
        terminal=tt1, base_voltage=bv, connection_kind=cim100.WindingConnection.D, mrid="pte-1",
    )  # fmt: skip
    e2 = cim100.PowerTransformerEnd(
        name="End2", end_number=2, rated_u=415.0, power_transformer=tx, terminal=tt2,
        connection_kind=cim100.WindingConnection.Yn, mrid="pte-2",
    )  # fmt: skip
    rtc = cim100.RatioTapChanger(
        name="OLTC", high_step=17, low_step=1, step=9.0, ltc_flag=True, transformer_end=e1,
        mrid="rtc-1",
    )  # fmt: skip
    inj = cim100.EquivalentInjection(
        name="Grid", r=0.1, regulation_status=False, equipment_container=sub, mrid="inj-1"
    )
    tinj = _terminal(inj, 1, cn1)
    shunt = cim100.LinearShuntCompensator(
        name="Cap", b_per_section=2.5e-4, sections=1.0, maximum_sections=4,
        switch_on_date=dt.datetime(2024, 5, 6, 7, 8, 9), equipment_container=vl, mrid="shunt-1",
    )  # fmt: skip
    tshunt = _terminal(shunt, 1, cn3)
    # Location with a compound attribute and PositionPoints (no mrid)
    loc = cim100.Location(
        mrid="loc-1",
        type="geo",
        main_address=cim100.StreetAddress(
            street_detail=None, postal_code="2000", town_detail=None, po_box="Box <1> & 2"
        ),
    )
    p1 = cim100.PositionPoint(
        sequence_number=1, x_position="151.2", y_position="-33.8", location=loc
    )
    p2 = cim100.PositionPoint(
        sequence_number=2, x_position="151.3", y_position="-33.9", location=loc
    )
    line.location = loc
    # N:M association Asset <-> PowerSystemResource
    asset = cim100.Asset(name="Asset", serial_number="SN-9", mrid="asset-1")
    asset.add_power_system_resource(line)
    asset.add_power_system_resource(tx)
    # Decimal and date attributes
    price = cim100.Price(amount=Decimal("12.3400"))
    tariff = cim100.Tariff(name="T", start_date=dt.date(2025, 1, 2), mrid="tariff-1")
    # an enum with a non-identifier-like literal and a datatype that holds a plain value
    return dict(locals())


def roots(net):
    return [net["sub"], net["asset"], net["price"], net["tariff"], net["p1"]]
