import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from math import pow

st.set_page_config(page_title="HEMS → Grid Investor Simulator", layout="wide")
st.title("🏠→⚡  Hardware-to-Grid Investor Simulator (multi-ISO)")

# ──────────────────────────────────────────────────────────
#  Capacity-price look-ups ($/kW-yr)  — P10 / P50 / P90
# ──────────────────────────────────────────────────────────
ISO_CAP = {
    "CAISO": (40, 55, 75),
    "ISO-NE": (30, 40, 55),
    "NYISO": (28, 36, 48),
    "PJM":  (60,100,150),
    "MISO": (25, 35, 50),
}
# Event payout ($/MWh) for each ISO
ISO_EVT = {"CAISO":150,"ISO-NE":125,"NYISO":100,"PJM":150,"MISO":100}

# Carbon factor (t CO₂ per MWh shifted) – optional ESG metric
CARBON = {"CAISO":0.19,"ISO-NE":0.30,"NYISO":0.26,"PJM":0.45,"MISO":0.50}

# Scenario presets
SCEN = {
    "Base": dict(asp=1200, g=0.40, tier=1),   # P50 cap price
    "Bull": dict(asp=1000, g=0.50, tier=2),   # P90
    "Bear": dict(asp=1500, g=0.25, tier=0),   # P10
}

# --- tiny IRR solver (no extra libs) ---------------------------------
def irr(cflows, guess=0.1):
    """Return IRR -- cash list must start with a negative outflow."""
    r = guess
    for _ in range(40):                          # Newton iterations
        npv   = sum(cf / (1+r)**i for i, cf in enumerate(cflows))
        d_npv = sum(-i*cf / (1+r)**(i+1) for i, cf in enumerate(cflows))
        if abs(npv) < 1e-9 or d_npv == 0:
            break
        r -= npv / d_npv
    return r*100

# Helper
def cap_price(iso, tier):      # tier = 0/1/2  ⇒  P10/P50/P90
    return ISO_CAP[iso][tier]

def npv(arr, r):
    """simple NPV of an equal stream using discount r"""
    return sum(v / pow(1 + r, i) for i, v in enumerate(arr, 1))


# ──────────────────────────────────────────────────────────
#  Core simulation: returns DF + cash list + IRR
# ──────────────────────────────────────────────────────────
def simulate(
    years,
    roadmap,         # {iso: go-live year}
    asp,
    unit_cagr,
    bom_drop,
    rebate_share,
    kw_home,
    evt_prob,
    hrs_evt,
    units0,
    churn,
    installer,
    marketing,
    gm,
    disc,
):
    rows, cash = [], []
    units, cum_units = units0, 0
    bom0 = asp * (1 - gm)

    for y in range(years):
        cur_bom = bom0 * pow(1 - bom_drop, y)
        hw_gp   = (asp - cur_bom) * units
        rebate  = rebate_share * 500 * units
        hw_rev  = asp * units + rebate

        # active fleet
        cum_units += units
        active_units = int(cum_units * enroll * pow(1-churn, y))
        mw = active_units * kw_home / 1000

        # grid revenue across ISOs that are live
        vpp_cap = vpp_evt = co2 = 0
        for iso, live_year in roadmap.items():
            if y + 1 >= live_year:                 # ISO live in this year
                tier = SCEN[scenario]["tier"]
                vpp_cap += mw * 1000 * cap_price(iso, tier)
                vpp_evt += mw * hrs_evt * ISO_EVT[iso] * evt_prob
                co2     += mw * hrs_evt * CARBON[iso]  * evt_prob

        vpp_rev   = vpp_cap + vpp_evt
        total_rev = hw_rev + vpp_rev

        # simple “cash” = HW gross-profit + VPP – CAC
        cash.append(hw_gp + vpp_rev - (installer + marketing) * units)

        ltv = npv([(vpp_rev / active_units)] * 7, disc)

        rows.append(
            dict(
                Year     = f"Y{y+1}",
                Units    = units,
                MW       = round(mw, 2),
                Hardware = hw_rev,
                VPP      = vpp_rev,
                Revenue  = total_rev,
                Cash     = cash[-1],
                CO2      = co2,
                LTV      = ltv,
            )
        )
        units = int(units * (1 + unit_cagr))

    irr_val = irr([-abs(cash[0])] + cash[1:]) * 100 if len(cash) > 1 else float("nan")
    return pd.DataFrame(rows).set_index("Year"), irr_val, cash


# ── Sidebar inputs ────────────────────────────────────────
side      = st.sidebar
scenario  = side.radio("Scenario", list(SCEN))
years     = side.slider("Projection horizon (yrs)", 5, 10, 7)

asp       = side.number_input("Retail ASP ($)", SCEN[scenario]["asp"], step=50)
unit_cagr = side.slider("Unit CAGR", 0.0, 1.0, SCEN[scenario]["g"])
units0    = side.number_input("Units sold Year 1", 1_000, step=100)

kw_home   = side.number_input("Curtailable kW / home", 3.0)

bom_drop      = side.slider("BOM learning %/yr", 0.0, 0.2, 0.05, step=0.01)
rebate_share  = side.slider("Rebate share retained", 0.0, 1.0, 0.25)

evt_prob = side.slider("Event probability", 0.0, 1.0, 0.3)
hrs_evt  = side.number_input("Event hours per year", 10)

churn      = side.slider("Churn %/yr", 0.0, 0.2, 0.03, step=0.01)
installer  = side.number_input("Installer fee $", 300)
marketing  = side.number_input("Marketing $ per sale", 200)
gm         = side.slider("Initial HW gross-margin", 0.0, 1.0, 0.35)
disc       = side.slider("Discount rate", 0.05, 0.20, 0.10)
enroll     = st.sidebar.slider("Enrollment rate", 0.0, 1.0, 0.80)

side.markdown("### ISO roll-out (enter **live** year)")
roadmap = {}
for iso in ISO_CAP:
    roadmap[iso] = side.number_input(
        f"{iso} live year", 1, years, value=1 if iso == "CAISO" else years
    )

# ── Run simulation ───────────────────────────────────────
df, irr_val, cash = simulate(
    years,
    roadmap,
    asp,
    unit_cagr,
    bom_drop,
    rebate_share,
    kw_home,
    evt_prob,
    hrs_evt,
    units0,
    churn,
    installer,
    marketing,
    gm,
    disc,
)

# ── Charts ───────────────────────────────────────────────
st.subheader("Revenue evolution")
st.area_chart(df[["Hardware", "VPP"]])

# Pie mix
mix = df.iloc[-1][["Hardware","VPP"]].astype(float).reset_index()
mix.columns = ["Source", "Value"]
pie = (
    alt.Chart(mix)
        .mark_arc(innerRadius=30)
        .encode(theta="Value:Q", color="Source:N",
                tooltip=["Source:N", alt.Tooltip("Value:Q", format="$.0f")])
)
st.altair_chart(pie, use_container_width=True)


# Table
st.dataframe(df.style.format("${:,.0f}"))

# Cashflow & IRR
st.subheader("Fleet cashflow & IRR")
st.metric("Unlevered IRR", f"{irr_val:,.1f}%")
st.bar_chart(
    pd.Series(cash, index=[f"Y{i+1}" for i in range(years)], name="Cash")
)

# Quick bear–stress
if st.button("Bear-stress (P10 cap, churn +5 %)"):
    bear_roadmap = roadmap.copy()
    df_bear, _, _ = simulate(
        years,
        bear_roadmap,
        asp,
        unit_cagr,
        bom_drop,
        rebate_share,
        kw_home,
        evt_prob,
        hrs_evt,
        units0,
        churn + 0.05,
        installer,
        marketing,
        gm,
        disc,
    )
    st.warning("Bear-case revenue trajectory")
    st.line_chart(df_bear["Revenue"])
    
