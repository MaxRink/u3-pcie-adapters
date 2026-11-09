"""Analytical (1-D network) thermal + airflow model for 2.5" U.3 drives in a ducted shroud.

Geometry (matches the "drives upright on the card" layout): N drives, 15 mm thick, stand side by
side with `gap` mm between their 100 x 69.85 mm faces and to the shroud walls. Air from one fan,
ducted by the shroud, flows along the 69.85 mm dimension through the N+1 parallel channels and
a `top` mm bypass gap over the drive tops.

Model:
- parallel-plate channels, hydraulic diameter Dh = 2*gap
- laminar: Stephan's simultaneously-developing mean Nusselt number (both plates heated);
  single-side-heated outer channels scaled by 5.385/7.541 (fully developed ratio)
- turbulent: Gnielinski; linear blend over Re 2300..4000
- each drive is treated as isothermal (aluminium case, k ~ 150 W/mK) and sees the inlet air:
  T_drive = T_in + P / (m_dot cp (1 - exp(-NTU))), NTU = h A / (m_dot cp)
- pressure drop: Shah apparent (developing) laminar friction, floored at Blasius turbulent, + entry 0.5 + exit 1.0
  + 0.3 dynamic heads for the fan-to-stack funnel, evaluated at the channel velocity
- fan curves: parabolic fits through datasheet free-air flow and max static pressure

All inputs are in SI unless the name says mm/CFM. Run as a script to write the plots/tables.
"""
import json
import math
import os

import numpy as np

AIR = dict(rho=1.12, cp=1007.0, k=0.0275, nu=1.70e-5, Pr=0.71)   # ~40 C
CFM = 4.71947e-4                                                   # m^3/s per CFM

DRIVE = dict(L=0.06985, H=0.100, T=0.015)                          # flow length, height, thickness


def nu_lam(xstar, Pr):
    """Stephan, mean Nu for simultaneously developing flow between isothermal parallel plates."""
    return 7.55 + 0.024 * xstar ** -1.14 / (1 + 0.0358 * Pr ** 0.17 * xstar ** -0.64)


def nu_turb(Re, Pr):
    f = (0.79 * math.log(Re) - 1.64) ** -2
    return (f / 8) * (Re - 1000) * Pr / (1 + 12.7 * math.sqrt(f / 8) * (Pr ** (2 / 3) - 1))


def nusselt(Re, Pr, L, Dh):
    lam = nu_lam(L / (Dh * Re * Pr), Pr)
    if Re <= 2300:
        return lam
    turb = nu_turb(max(Re, 3000), Pr) * (1 + (Dh / L) ** (2 / 3))
    if Re >= 4000:
        return max(lam, turb)
    w = (Re - 2300) / 1700
    return max(lam, (1 - w) * lam + w * turb)


def fanning(Re, L, Dh):
    """Apparent Fanning friction: Shah developing-laminar, never below Blasius turbulent."""
    xp = L / (Dh * Re)
    fr = 3.44 / math.sqrt(xp) + (24 + 0.674 / (4 * xp) - 3.44 / math.sqrt(xp)) / (1 + 2.9e-5 * xp ** -2)
    return max(fr / Re, 0.079 * Re ** -0.25)


def stack(n, gap_mm, Q, P=25.0, T_in=35.0, top_mm=5.0, air=AIR):
    """Return dict with drive temperatures (C), pressure drop (Pa), velocities for flow Q (m^3/s)."""
    g, top = gap_mm / 1000, top_mm / 1000
    L, H, T = DRIVE["L"], DRIVE["H"], DRIVE["T"]
    W = n * T + (n + 1) * g
    A = (n + 1) * g * H + top * W
    V = Q / A
    Dh = 2 * g
    Re = V * Dh / air["nu"]
    Nu = nusselt(Re, air["Pr"], L, Dh)
    h2 = Nu * air["k"] / Dh                          # channel heated both sides
    h1 = h2 * 5.385 / 7.541 if Re < 2300 else h2     # outer channel, one side heated
    Dh_top = 2 * top
    Re_t = V * Dh_top / air["nu"]
    h_top = nusselt(Re_t, air["Pr"], L, Dh_top) * air["k"] / Dh_top * 5.385 / 7.541
    temps = []
    mdot_ch = air["rho"] * V * g * H                 # per side channel
    for i in range(n):
        outer_l, outer_r = i == 0, i == n - 1
        hl, hr = (h1 if outer_l else h2), (h1 if outer_r else h2)
        Af = L * H
        # flow share: a whole outer channel, half a shared channel, plus the bypass over the top
        m = mdot_ch * ((1 if outer_l else 0.5) + (1 if outer_r else 0.5)) + air["rho"] * V * top * T
        hA = hl * Af + hr * Af + h_top * L * T + 0.5 * (hl + hr) * 2 * H * T * 0.5   # faces, top, ends
        ntu = hA / (m * air["cp"])
        temps.append(T_in + P / (m * air["cp"] * (1 - math.exp(-ntu))))
    f = fanning(Re, L, Dh)
    dyn = 0.5 * air["rho"] * V ** 2
    dp = (4 * f * L / Dh + 0.5 + 1.0 + 0.3) * dyn
    return dict(Q=Q, CFM=Q / CFM, V=V, Re=Re, h=h2, dp=dp, T=temps, Tmax=max(temps),
                air_rise=n * P / (air["rho"] * air["cp"] * Q), A=A)


# Approximate 92 mm fan curves: (name, free-air CFM, max static Pa). Parabolic p = p0 (1 - (Q/Q0)^2).
FANS = [
    ("92x25 quiet (NF-A9 class, 2000 rpm)", 46.4, 22.4),
    ("92x25 high-speed (3000 rpm class)", 60.0, 45.0),
    ("92x38 server (Delta/Sunon class, ~5000 rpm)", 75.0, 150.0),
]


def fan_dp(Q, cfm0, p0):
    q = Q / (cfm0 * CFM)
    return p0 * max(0.0, 1 - q * q)


def operating_point(n, gap_mm, fan, **kw):
    _, cfm0, p0 = fan
    lo, hi = 1e-5, cfm0 * CFM * 0.999
    for _ in range(80):
        mid = (lo + hi) / 2
        if stack(n, gap_mm, mid, **kw)["dp"] < fan_dp(mid, cfm0, p0):
            lo = mid
        else:
            hi = mid
    return stack(n, gap_mm, lo, **kw)


def required_cfm(n, gap_mm, Tlim, **kw):
    lo, hi = 1e-4, 0.2
    if stack(n, gap_mm, hi, **kw)["Tmax"] > Tlim:
        return float("nan")
    for _ in range(80):
        mid = (lo + hi) / 2
        if stack(n, gap_mm, mid, **kw)["Tmax"] > Tlim:
            lo = mid
        else:
            hi = mid
    return hi / CFM


def main(out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(out_dir, exist_ok=True)
    res = dict(assumptions=dict(power_W=25.0, T_in_C=35.0, top_bypass_mm=5.0, air=AIR, drive_mm=[69.85, 100, 15],
                                fans=FANS), cases=[])
    cfms = np.linspace(4, 80, 200)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), dpi=150)
    colors = {3: "#1f6fb2", 5: "#d1495b", 8: "#2a9d5c"}
    for ax, n in zip(axes, (2, 4)):
        for g in (3, 5, 8):
            t = [stack(n, g, c * CFM)["Tmax"] for c in cfms]
            ax.plot(cfms, t, color=colors[g], lw=2, label=f"{g} mm gaps")
        ax.axhline(70, color="#444", ls="--", lw=1)
        ax.text(79, 71, "70 °C case limit", ha="right", fontsize=8, color="#444")
        ax.axhline(60, color="#888", ls=":", lw=1)
        ax.text(79, 61, "60 °C target", ha="right", fontsize=8, color="#888")
        ax.set_ylim(35, 130)
        ax.set_xlim(4, 80)
        ax.set_xlabel("airflow through the shroud (CFM)")
        ax.set_title(f"{n} drives x 25 W, 35 °C inlet: hottest drive")
        ax.grid(alpha=0.3)
        ax.legend(frameon=False)
    axes[0].set_ylabel("drive case temperature (°C)")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "analytic_temp_vs_airflow.png"))
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), dpi=150)
    for ax, n in zip(axes, (2, 4)):
        for g in (3, 5, 8):
            ax.plot(cfms, [stack(n, g, c * CFM)["dp"] for c in cfms], color=colors[g], lw=2, label=f"system, {g} mm gaps")
        for (name, c0, p0), ls in zip(FANS, ("-", "--", "-.")):
            ax.plot(cfms, [fan_dp(c * CFM, c0, p0) for c in cfms], color="#333", ls=ls, lw=1.2, label=name)
        ax.set_ylim(0, 160)
        ax.set_xlim(4, 80)
        ax.set_xlabel("airflow (CFM)")
        ax.set_title(f"{n} drives: shroud pressure drop vs 92 mm fan curves")
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=7)
    axes[0].set_ylabel("static pressure (Pa)")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "analytic_fan_operating_points.png"))
    plt.close(fig)

    for n in (2, 4):
        for g in (3, 5, 8):
            row = dict(drives=n, gap_mm=g, need_cfm_70C=round(required_cfm(n, g, 70), 1),
                       need_cfm_60C=round(required_cfm(n, g, 60), 1), fans=[])
            for fan in FANS:
                op = operating_point(n, g, fan)
                row["fans"].append(dict(fan=fan[0], cfm=round(op["CFM"], 1), dp_Pa=round(op["dp"], 1),
                                        V_ms=round(op["V"], 2), Re=round(op["Re"]), h=round(op["h"], 1),
                                        Tmax_C=round(op["Tmax"], 1), air_rise_K=round(op["air_rise"], 1)))
            res["cases"].append(row)
    json.dump(res, open(os.path.join(out_dir, "analytic_results.json"), "w"), indent=1)
    lines = ["| drives | gap | CFM for 70 °C | CFM for 60 °C | " + " | ".join(f[0] for f in FANS) + " |",
             "| --- | --- | --- | --- | " + " | ".join("---" for _ in FANS) + " |"]
    for r in res["cases"]:
        cells = [f"{f['Tmax_C']:.0f} °C @ {f['cfm']:.0f} CFM" for f in r["fans"]]
        lines.append(f"| {r['drives']} | {r['gap_mm']} mm | {r['need_cfm_70C']} | {r['need_cfm_60C']} | " + " | ".join(cells) + " |")
    open(os.path.join(out_dir, "analytic_table.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else "out")
