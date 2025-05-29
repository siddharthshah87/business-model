
import streamlit as st
import pandas as pd
import numpy as np

HELP = {
    "bom": "Cost to build & ship one kit.",
    "install": "Paid to installer per unit.",
    "asp": "Retail price for customer.",
    "units_y1": "Year 1 shipment forecast.",
    "unit_cagr": "Annual shipment growth rate.",
    "dev_total": "Total R&D + certification spend.",
    "dev_years": "Years to amortize dev cost.",
    "arr": "Annual SaaS revenue per site.",
    "loads": "Controllable loads per site.",
    "kwh": "Daily kWh shifted per load.",
    "spread": "Rate difference ($/kWh).",
    "share": "Your share of bill savings.",
    "mw_y1": "MW capacity managed year 1.",
    "mw_cagr": "Annual MW growth.",
    "fee": "ISO/utility fee per MWh.",
    "gm": "Gross margin after hardware.",
    "ebitda": "EBITDA margin before amort.",
    "mult_e": "Valuation multiple on EBITDA.",
    "mult_r": "Valuation multiple on revenue."
}

GTM_PROFILES = {
    "Installer-led": {"delay": 0, "attach_start": 0.6, "attach_end": 0.9, "install_cost": 300},
    "OEM Bundle": {"delay": 1, "attach_start": 0.4, "attach_end": 0.75, "install_cost": 150},
    "Utility Co-brand": {"delay": 2, "attach_start": 0.7, "attach_end": 0.95, "install_cost": 200},
    "Direct-to-Consumer": {"delay": 0, "attach_start": 0.3, "attach_end": 0.65, "install_cost": 0},
}

@st.cache_data
def load_state_data():
    return pd.DataFrame({
        "state": ["CA", "TX", "FL", "NY", "IL"],
        "housing_units": [14_000_000, 11_000_000, 9_600_000, 8_300_000, 5_200_000],
        "ev_penetration": [0.25, 0.10, 0.08, 0.12, 0.09],
        "tou_rate_spread": [0.22, 0.18, 0.15, 0.20, 0.17],
        "percent_100A": [0.45, 0.35, 0.38, 0.50, 0.42],
    })

def calc_state_som(df, profile, panel_filter, years, pen_start, pen_end):
    som = np.zeros(years)
    ramp = np.linspace(pen_start, pen_end, years)
    for _, row in df.iterrows():
        tam = row["housing_units"] * row["percent_100A"] * panel_filter
        sam = tam * row["ev_penetration"]
        attach_curve = np.linspace(profile["attach_start"], profile["attach_end"], years)
        for y in range(years):
            if y < profile["delay"]:
                continue
            idx = y - profile["delay"]
            som[y] += sam * ramp[idx] * attach_curve[idx]
    return som

def run_financial(years, hw_cost, install_cost, asp, units_y1, unit_cagr,
                  arr_site, loads_site, kwh_shift, spread, share_savings,
                  mw_y1, mw_cagr, order_fee, gross_margin, ebitda_margin,
                  dev_total, dev_years, mult_e, mult_r, attach_curve):
    amort = dev_total / dev_years if dev_years else 0
    data = []
    hw_units = units_y1
    mw = mw_y1
    for yr in range(years):
        hw_rev = hw_units * asp
        sites = mw * 250
        attached = sites * attach_curve[yr]
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
            "Attach Rate": attach_curve[yr],
            "Revenue": total_rev,
            "Reported EBITDA": rpt_ebitda,
            "Enterprise Value": ev
        })
        hw_units = int(hw_units * (1 + unit_cagr))
        mw *= (1 + mw_cagr)
    return pd.DataFrame(data).set_index("Year")

# Streamlit App
st.set_page_config(page_title="HEMS + VPP Simulator", layout="wide")
side = st.sidebar
side.title("Inputs")

years = side.slider("Projection Years", 3, 10, 5)
gtm = side.selectbox("GTM Strategy", list(GTM_PROFILES.keys()))
profile = GTM_PROFILES[gtm]

hw_cost = side.number_input("BOM + Shipping", 400.0, step=25.0)
install_cost = side.number_input("Installer Payment", float(profile["install_cost"]), step=25.0)
asp = side.number_input("Retail Price", 1500.0, step=50.0)
units_y1 = side.number_input("Year 1 Units", 1000, step=100)
unit_cagr = side.slider("Unit Growth Rate", 0.0, 1.0, 0.4)

dev_total = side.number_input("Total Dev Cost", 2_000_000, step=100_000)
dev_years = side.slider("Dev Amort Years", 1, years, 5)

arr_site = side.number_input("SaaS ARR/site", 120.0)
loads_site = side.number_input("Controllable Loads/site", 4)
kwh_shift = side.number_input("kWh/Load/Day", 3.0)
spread = side.number_input("TOU Spread $/kWh", 0.15)
share_savings = side.slider("Your Cut of Savings", 0.0, 1.0, 0.4)

mw_y1 = side.number_input("MW in Year 1", 4.0)
mw_cagr = side.slider("MW Growth", 0.0, 1.0, 0.6)
order_fee = side.number_input("Market Fees $/MWh", 1.0)

gross_margin = side.slider("Gross Margin", 0.0, 1.0, 0.35)
ebitda_margin = side.slider("EBITDA Margin", 0.0, 0.5, 0.15)
mult_e = side.number_input("EV/EBITDA", 8.0)
mult_r = side.number_input("EV/Revenue", 0.0)

df_states = load_state_data()
panel_filter = side.slider("Filter for 100A TAM", 0.0, 1.0, 0.4)
pen_start = side.slider("Year 1 SAM %", 0.0, 10.0, 0.5) / 100
pen_end = side.slider("Final Year SAM %", 0.0, 100.0, 5.0) / 100

som_curve = calc_state_som(df_states, profile, panel_filter, years, pen_start, pen_end)
attach_curve = som_curve / (250 * mw_y1)

df_fin = run_financial(
    years, hw_cost, install_cost, asp, units_y1, unit_cagr,
    arr_site, loads_site, kwh_shift, spread, share_savings,
    mw_y1, mw_cagr, order_fee, gross_margin, ebitda_margin,
    dev_total, dev_years, mult_e, mult_r, attach_curve
)

st.title("Smart Panel + Subpanel HEMS Financial Simulator")
st.subheader(f"GTM Strategy: {gtm}")
st.line_chart(pd.DataFrame({"SOM Units": som_curve}))
st.dataframe(df_fin.style.format("${:,.0f}"))
st.bar_chart(df_fin["Revenue"])
st.line_chart(df_fin["Enterprise Value"])
