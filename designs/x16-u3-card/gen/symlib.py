"""Custom schematic symbols (KiCad 7 .kicad_sym) for the U.3 adapter project."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SYMLIB = os.path.join(HERE, "..", "lib", "u3adapter.kicad_sym")

# --- U.3 (SFF-8639 used per SFF-TA-1001) pin names.  Source: SNIA SFF-9639 rev 2.2,
# tables 5-1..5-3, "SFF-TA1001" column.  Signal naming is host-centric like the PCIe CEM:
# PETx = host transmitter (drive receiver), PERx = host receiver (drive transmitter).
U3_PINS = {
    "S1": "GND", "S2": "PETp0", "S3": "PETn0", "S4": "GND", "S5": "PERn0", "S6": "PERp0", "S7": "GND",
    "S8": "GND", "S9": "PETp1", "S10": "PETn1", "S11": "GND", "S12": "PERn1", "S13": "PERp1", "S14": "GND",
    "S15": "HPT0", "S16": "GND", "S17": "PETp2", "S18": "PETn2", "S19": "GND", "S20": "PERn2", "S21": "PERp2",
    "S22": "GND", "S23": "PETp3", "S24": "PETn3", "S25": "GND", "S26": "PERn3", "S27": "PERp3", "S28": "GND",
    "E1": "REFCLK1+", "E2": "REFCLK1-", "E3": "3V3_AUX", "E4": "PERST1#", "E5": "PERST0#", "E6": "IFDET2#",
    "E7": "REFCLK0+", "E8": "REFCLK0-", "E9": "GND", "E10": "U2_PETp0", "E11": "U2_PETn0", "E12": "GND",
    "E13": "U2_PERn0", "E14": "U2_PERp0", "E15": "GND", "E16": "HPT1", "E17": "U2_PETp3", "E18": "U2_PETn3",
    "E19": "GND", "E20": "U2_PERn3", "E21": "U2_PERp3", "E22": "GND", "E23": "SMBCLK", "E24": "SMBDAT",
    "E25": "DUALPORTEN#",
    "P1": "WAKE#", "P2": "RSVD", "P3": "PWRDIS", "P4": "IFDET#", "P5": "GND", "P6": "GND", "P7": "5V_PRE",
    "P8": "5V", "P9": "5V", "P10": "PRSNT#", "P11": "ACTIVITY#", "P12": "GND", "P13": "12V_PRE", "P14": "12V",
    "P15": "12V",
}

# OCuLink 4i connector pins (Amphenol G14A421211112HR numbering).  Names below are the
# *device-end* meaning when used with a standard SFF-8611 crossover cable (A row of the host
# end lands on the B row of the device end).  Verified against Antmicro's open-source
# OCuLink-to-PCIe device adapter (net names on its J1).
OCU_DEV_PINS = {
    "A1": "VACT_RX", "A2": "GND", "A3": "PETp0", "A4": "PETn0", "A5": "GND", "A6": "PETp1", "A7": "PETn1",
    "A8": "GND", "A9": "SMBCLK", "A10": "SMBDAT", "A11": "GND", "A12": "PERST#", "A13": "CPRSNT#", "A14": "GND",
    "A15": "PETp2", "A16": "PETn2", "A17": "GND", "A18": "PETp3", "A19": "PETn3", "A20": "GND", "A21": "5V_A",
    "B1": "5V_B", "B2": "GND", "B3": "PERp0", "B4": "PERn0", "B5": "GND", "B6": "PERp1", "B7": "PERn1",
    "B8": "GND", "B9": "NC_B9", "B10": "WAKE#", "B11": "GND", "B12": "REFCLK+", "B13": "REFCLK-", "B14": "GND",
    "B15": "PERp2", "B16": "PERn2", "B17": "GND", "B18": "PERp3", "B19": "PERn3", "B20": "GND", "B21": "VACT_TX",
    "SH": "SHIELD",
}
# Host-end meaning (Williamson Yang's M.2-to-OCuLink host adapter, mirrored by the crossover).
OCU_HOST_PINS = {
    "A1": "VACT_RX", "A2": "GND", "A3": "PERp0", "A4": "PERn0", "A5": "GND", "A6": "PERp1", "A7": "PERn1",
    "A8": "GND", "A9": "CBLPRSNT#", "A10": "WAKE#", "A11": "GND", "A12": "REFCLK+", "A13": "REFCLK-",
    "A14": "GND", "A15": "PERp2", "A16": "PERn2", "A17": "GND", "A18": "PERp3", "A19": "PERn3", "A20": "GND",
    "A21": "5V_A", "B1": "5V_B", "B2": "GND", "B3": "PETp0", "B4": "PETn0", "B5": "GND", "B6": "PETp1",
    "B7": "PETn1", "B8": "GND", "B9": "SMBCLK", "B10": "SMBDAT", "B11": "GND", "B12": "PERST#",
    "B13": "CPRSNT#", "B14": "GND", "B15": "PETp2", "B16": "PETn2", "B17": "GND", "B18": "PETp3",
    "B19": "PETn3", "B20": "GND", "B21": "VACT_TX", "SH": "SHIELD",
}


def _pin(name, num, x, y, ang, etype="passive", hide=False):
    h = " hide" if hide else ""
    return (f'      (pin {etype} line (at {x} {y} {ang}) (length 2.54){h}\n'
            f'        (name "{name}" (effects (font (size 1.016 1.016))))\n'
            f'        (number "{num}" (effects (font (size 1.016 1.016))))\n      )\n')


def box_symbol(name, ref, descr, left, right, width=30.48, fp="", extra_props=""):
    """left/right: list of (pin_number, pin_name) top to bottom; None = gap."""
    n = max(len(left), len(right))
    h = (n + 1) * 2.54
    top = h / 2
    top = round(top / 2.54) * 2.54
    s = f'  (symbol "{name}" (in_bom yes) (on_board yes)\n'
    s += f'    (property "Reference" "{ref}" (at 0 {top + 2.54:.2f} 0) (effects (font (size 1.27 1.27))))\n'
    s += f'    (property "Value" "{name}" (at 0 {-top - 2.54:.2f} 0) (effects (font (size 1.27 1.27))))\n'
    s += f'    (property "Footprint" "{fp}" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
    s += f'    (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
    s += f'    (property "ki_description" "{descr}" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
    s += extra_props
    s += f'    (symbol "{name}_0_1"\n      (rectangle (start {-width/2} {top}) (end {width/2} {-top - 2.54 * 0})\n' \
         f'        (stroke (width 0.254) (type default)) (fill (type background)))\n    )\n'
    s += f'    (symbol "{name}_1_1"\n'
    seen = {}
    for col, pins, x, ang in ((0, left, -width / 2 - 2.54, 0), (1, right, width / 2 + 2.54, 180)):
        y = top - 2.54
        for p in pins:
            if p is not None:
                num, pname = p
                # stack identically-named pins (e.g. GND) is fine; KiCad needs unique numbers only
                s += _pin(pname, num, round(x, 2), round(y, 2), ang)
            y -= 2.54
    s += "    )\n  )\n"
    return s


def u3_symbol():
    order_l = ["S2", "S3", "S6", "S5", None, "S9", "S10", "S13", "S12", None, "S17", "S18", "S21", "S20", None,
               "S23", "S24", "S27", "S26", None, "E7", "E8", "E1", "E2", None, "E5", "E4", "E23", "E24", None,
               "E10", "E11", "E14", "E13", "E17", "E18", "E21", "E20"]
    order_r = ["P13", "P14", "P15", "P7", "P8", "P9", "E3", None, "P3", "P11", "P10", "P1", "P2", "P4", "E6",
               "E25", "S15", "E16", None] + [p for p in U3_PINS if U3_PINS[p] == "GND"]
    used = set(x for x in order_l + order_r if x)
    assert used == set(U3_PINS), set(U3_PINS) - used
    left = [(p, U3_PINS[p]) if p else None for p in order_l]
    right = [(p, U3_PINS[p]) if p else None for p in order_r] + [("MP", "MOUNT")]
    return box_symbol("U3_SFF-TA-1001_Receptacle", "J", "SFF-8639 receptacle wired as U.3 (SFF-TA-1001) host",
                      left, right, width=33.02,
                      fp="u3adapter:Amphenol_PSAS4F213002_SFF-8639_U3_RA_SMD")


def ocu_symbol(name, pins, descr):
    sig = [p for p in pins if pins[p] not in ("GND", "SHIELD")]
    gnd = [p for p in pins if pins[p] == "GND"]
    left = [(p, pins[p]) for p in sorted(sig, key=lambda q: (q[0], int(q[1:])))]
    right = [(p, pins[p]) for p in gnd] + [None, ("SH", "SHIELD")]
    return box_symbol(name, "J", descr, left, right, width=22.86,
                      fp="u3adapter:Amphenol_G14A421211112HR_OCuLink_4i_RA_SMD")


def write():
    s = "(kicad_symbol_lib (version 20220914) (generator u3adapter_gen)\n"
    s += u3_symbol()
    s += ocu_symbol("OCuLink_4i_DeviceEnd", OCU_DEV_PINS, "OCuLink 4i receptacle, pins named for the device (drive) end")
    s += ocu_symbol("OCuLink_4i_HostEnd", OCU_HOST_PINS, "OCuLink 4i receptacle, pins named for the host end")
    s += ")\n"
    with open(SYMLIB, "w") as f:
        f.write(s)


if __name__ == "__main__":
    write()
    print("wrote", SYMLIB)
