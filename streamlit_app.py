
import streamlit as st
import pandas as pd
import numpy as np

############################################################
# Helper texts (hover tool‑tips)
############################################################
HELP = {
    "bom": "ELI5: Cost to build & ship ONE collar + smart‑sub‑panel kit (before profit).",
    "install": "ELI5: Cash we pay the electrician/channel partner for each install.",
    "asp": "ELI5: Sticker price the homeowner pays for the hardware kit.",
    "units_y1": "ELI5: Kits we expect to ship in the first forecast year.",
    "unit_cagr": "ELI5: Annual shipment growth. 0.6 means +60 % per year.",
    "dev_total": "ELI5: Up‑front R&D + UL/FCC/app costs before selling units.",
    "dev_years": "ELI5: Years over which we amortize that dev spend.",
    "arr": "ELI5: Yearly software/VPP subscription fee per house.",
    "loads": "ELI5: Big controllable loads per house (EV, heat‑pump, etc.).",
    "kwh": "ELI5: kWh per load we can shift off‑peak each day.",
    "spread": "ELI5: Average $ difference between off‑peak and peak electricity.",
    "share": "ELI5: Our share of the savings (0.4 ⇒ we keep 40 %).",
    "mw_y1": "ELI5: Flexible‑load capacity (MW) we aggregate in year 1.",
    "mw_cagr": "ELI5: Annual growth of that MW portfolio.",
    "fee": "ELI5: ISO/utility fees we pay per MWh transacted.",
    "gm": "ELI5: % of revenue left after hardware COGS + 2222 fees.",
    "ebitda": "ELI5: EBITDA margin *before* dev‑cost amortization.",
    "mult_e": "ELI5: How many × EBITDA investors might pay (set 0 to ignore).",
    "mult_r": "ELI5: How many × Revenue investors might pay (set 0 to ignore)."
}

############################################################
# Minimal state dataset (replace with real census/EV data)
############################################################
@st.cache_data(show_spinner=False)
def load_state_market():
    return pd.DataFrame({
        "state": ["CA", "TX", "FL", "NY", "IL"],
        "housing_units": [14_000_000, 11_000_000, 9_600_000, 8_300_000, 5_200_000],
    })

############################################################
# SOM curve builder with per‑state timing & attach‑rate ramps
############################################################
def calc_som_curve(df_states, params, panel_pct, pen_start, pen_end, years):
    sam_progression = np.linspace(pen_start, pen_end, years)
    som_by_year = np.zeros(years)
    for state, p in params.items():
        units = df_states.loc[df_states.state == state, "housing_units"].values[0]
        tam = units * panel_pct
        sam = tam * p["ev_ready"]          # ev‑ready filter
        attach_curve = np.linspace(p["attach_start"], p["attach_end"], years)
        for yr in range(years):
            if yr < p["delay"]:
                continue
            idx = yr - p["delay"]
            som_by_year[yr] += sam * sam_progression[idx] * attach_curve[idx]
    return som_by_year

############################################################
# Financial simulator (uses year‑specific attach rates)
############################################################
def run_financial(years,
                  hw_cost, install_cost, asp,
                  units_y1, unit_cagr,
                  arr_site, loads_site, kwh_shift, spread, share_savings,
                  mw_y1, mw_cagr,
                  order_fee,
                  gross_margin, ebitda_margin,
                  dev_total, dev_years,
                  mult_e, mult_r,
                  attach_rate_years):
    amort = dev_total / dev_years if dev_years else 0
    data = []
    hw_units = units_y1
    mw = mw_y1
    for yr in range(years):
        hw_rev = hw_units * asp
        sites = mw * 250                       # sites derived from MW capacity
        attached = sites * attach_rate_years[yr]
        saas_rev = attached * arr_site
        arb_rev = attached * loads_site * kwh_shift * 365 * spread * share_savings
        total_rev = hw_rev + saas_rev + arb_rev

        core_ebitda = total_rev * ebitda_margin
        rpt_ebitda = core_ebitda - amort

        ev_e = rpt_ebitda * mult_e if mult_e else 0
        ev_r = total_rev * mult_r if mult_r else 0
        ev = ev_r if mult_r else ev_e

        data.append({
            "Year": f"Year {yr+1}",
            "HW Units": hw_units,
            "Attach Rate": attach_rate_years[yr],
            "Revenue": total_rev,
            "Reported EBITDA": rpt_ebitda,
            "Enterprise Value": ev
        })

        hw_units = int(hw_units * (1 + unit_cagr))
        mw *= (1 + mw_cagr)

    return pd.DataFrame(data).set_index("Year")

############################################################
# Streamlit UI
############################################################
st.set_page_config(page_title="Collar + Sub‑panel Model v6", layout="wide")
side = st.sidebar
side.title("Inputs (hover for help)")

years = side.slider("Projection years", 3, 10, 5)

# --- Hardware economics
side.subheader("Hardware")
hw_cost = side.number_input("BOM + landing cost ($)", 400.0, step=50.0, help=HELP["bom"])
install_cost = side.number_input("Installer payment ($)", 250.0, step=25.0, help=HELP["install"])
asp = side.number_input("Sale price to customer ($)", 1_500.0, step=50.0, help=HELP["asp"])
units_y1 = side.number_input("Units shipped in Year 1", 1_000, step=100, help=HELP["units_y1"])
unit_cagr = side.slider("Annual unit growth rate", 0.0, 1.0, 0.4, help=HELP["unit_cagr"])

# --- Development cost
side.subheader("Development & Cert")
dev_total = side.number_input("Total dev cost ($)", 2_000_000, step=100_000, help=HELP["dev_total"])
dev_years = side.slider("Amortization years", 1, years, 5, help=HELP["dev_years"])

# --- SaaS constants
side.subheader("SaaS / DER")
arr_site = side.number_input("ARR per site ($/yr)", 120.0, step=10.0, help=HELP["arr"])
loads_site = side.number_input("Loads per site", 4, step=1, help=HELP["loads"])
kwh_shift = side.number_input("kWh shifted per load/day", 3.0, step=0.5, help=HELP["kwh"])
spread = side.number_input("Price spread ($/kWh)", 0.05, step=0.01, help=HELP["spread"])
share_savings = side.slider("Platform share of savings", 0.0, 1.0, 0.4, help=HELP["share"])

# --- Aggregation
side.subheader("Aggregation / Order 2222")
mw_y1 = side.number_input("MW under management – Year 1", 4.0, step=0.5, help=HELP["mw_y1"])
mw_cagr = side.slider("Annual MW growth", 0.0, 1.0, 0.6, help=HELP["mw_cagr"])
order_fee = side.number_input("Market fee ($/MWh)", 1.0, step=0.5, help=HELP["fee"])

# --- Financial assumptions
side.subheader("Financial")
gross_margin = side.slider("Blended gross‑margin", 0.0, 0.9, 0.35, help=HELP["gm"])
ebitda_margin = side.slider("Core EBITDA margin", 0.0, 0.5, 0.15, help=HELP["ebitda"])
mult_e = side.number_input("EV / EBITDA multiple", 8.0, step=0.5, help=HELP["mult_e"])
mult_r = side.number_input("EV / Revenue multiple", 0.0, 50.0, 0.0, help=HELP["mult_r"])

# ---------------- Tabs
tab_fin, tab_gtm = st.tabs(["Financial Model", "GTM & Region Detail"])

########## GTM TAB ##########
with tab_gtm:
    st.header("Per‑state market settings")
    df_states = load_state_market()
    selected_states = st.multiselect(
        "Target states", df_states.state.tolist(), default=df_states.state.tolist()[:3]
    )

    panel_pct = st.slider("% homes with ≤100 A service", 0.0, 1.0, 0.4)

    pen_start = st.number_input("SAM penetration Year 1 (%)", 0.0, 100.0, 0.5) / 100
    pen_end = st.number_input(f"SAM penetration Year {years} (%)", 0.0, 100.0, 5.0) / 100

    # Per‑state expanders
    state_params = {}
    for st_name in selected_states:
        with st.expander(st_name, expanded=False):
            delay = st.slider(f"Activation delay (years) – {st_name}", 0, years - 1, 0)
            ev_ready = st.slider(f"EV‑ready share – {st_name}", 0.0, 1.0, 0.5)
            attach_start = st.slider(f"Attach rate Year 1 – {st_name}", 0.0, 1.0, 0.6)
            attach_end = st.slider(f"Attach rate Year {years} – {st_name}", 0.0, 1.0, 0.9)
            state_params[st_name] = dict(
                delay=delay,
                ev_ready=ev_ready,
                attach_start=attach_start,
                attach_end=attach_end,
            )

    som_curve = calc_som_curve(df_states, state_params, panel_pct, pen_start, pen_end, years)
    st.bar_chart(pd.DataFrame({"SOM units": som_curve}))

########## FINANCIAL TAB ##########
with tab_fin:
    # Build global attach‑rate curve (simple average across active states each year)
    attach_curve = []
    for yr in range(years):
        rates = []
        for p in state_params.values():
            if yr < p["delay"]:
                continue
            idx = yr - p["delay"]
            rates.append(np.linspace(p["attach_start"], p["attach_end"], years)[idx])
        attach_curve.append(np.mean(rates) if rates else 0.0)

    df_fin = run_financial(
        years,
        hw_cost, install_cost, asp,
        units_y1, unit_cagr,
        arr_site, loads_site, kwh_shift, spread, share_savings,
        mw_y1, mw_cagr,
        order_fee,
        gross_margin, ebitda_margin,
        dev_total, dev_years,
        mult_e, mult_r,
        attach_curve,
    )

    st.header("Financial Projection")
    st.dataframe(df_fin.style.format("${:,.0f}"))
    st.bar_chart(df_fin["Revenue"])
    st.line_chart(df_fin["Enterprise Value"])
