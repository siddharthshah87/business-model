
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="HEMS + VPP Simulator", layout="wide")

HELP = {
    "bom": "Cost to build & ship one kit.",
    "install": "Paid to installer per unit.",
    "asp": "Retail price for customer.",
    "units_y1": "Year 1 shipment forecast.",
    "unit_cagr": "Annual shipment growth rate.",
    "dev_total": "Total R&D + certification spend.",
    "dev_years": "Years to amortize dev cost.",
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

def run_financial(years, hw_cost, install_cost, asp, units_y1, unit_cagr,
                  loads_site, kwh_shift, spread, share_savings,
                  mw_y1, mw_cagr, order_fee, gross_margin, ebitda_margin,
                  dev_total, dev_years, mult_e, mult_r):
    amort = dev_total / dev_years if dev_years else 0
    data = []
    hw_units = units_y1
    mw = mw_y1
    for yr in range(years):
        hw_rev = hw_units * asp
        vpp_sites = mw * 250
        vpp_rev = vpp_sites * loads_site * kwh_shift * 365 * spread * share_savings
        total_rev = hw_rev + vpp_rev
        core_ebitda = total_rev * ebitda_margin
        rpt_ebitda = core_ebitda - amort
        ev_e = rpt_ebitda * mult_e if mult_e else 0
        ev_r = total_rev * mult_r if mult_r else 0
        ev = ev_r if mult_r else ev_e
        data.append({
            "Year": f"Year {yr+1}",
            "HW Units": hw_units,
            "Hardware Revenue": hw_rev,
            "VPP Revenue": vpp_rev,
            "Total Revenue": total_rev,
            "Reported EBITDA": rpt_ebitda,
            "Enterprise Value": ev
        })
        hw_units = int(hw_units * (1 + unit_cagr))
        mw *= (1 + mw_cagr)
    return pd.DataFrame(data).set_index("Year")

st.title("HEMS + VPP Business Model Simulator")

years = st.sidebar.slider("Projection Years", 3, 10, 5)
hw_cost = st.sidebar.number_input("BOM + Shipping", 400.0, step=25.0, help=HELP["bom"])
install_cost = st.sidebar.number_input("Installer Payment", 250.0, step=25.0, help=HELP["install"])
asp = st.sidebar.number_input("Retail Price", 1500.0, step=50.0, help=HELP["asp"])
units_y1 = st.sidebar.number_input("Year 1 Units", 1000, step=100, help=HELP["units_y1"])
unit_cagr = st.sidebar.slider("Unit Growth Rate", 0.0, 1.0, 0.4, help=HELP["unit_cagr"])
dev_total = st.sidebar.number_input("Total Dev Cost", 2_000_000, step=100_000)
dev_years = st.sidebar.slider("Dev Amort Years", 1, years, 5)
loads_site = st.sidebar.number_input("Controllable Loads/site", 4)
kwh_shift = st.sidebar.number_input("kWh/Load/Day", 3.0)
spread = st.sidebar.number_input("TOU Spread $/kWh", 0.15)
share_savings = st.sidebar.slider("Your Cut of Savings", 0.0, 1.0, 0.4)
mw_y1 = st.sidebar.number_input("MW in Year 1", 4.0)
mw_cagr = st.sidebar.slider("MW Growth", 0.0, 1.0, 0.6)
order_fee = st.sidebar.number_input("Market Fees $/MWh", 1.0)
gross_margin = st.sidebar.slider("Gross Margin", 0.0, 1.0, 0.35)
ebitda_margin = st.sidebar.slider("EBITDA Margin", 0.0, 0.5, 0.15)
mult_e = st.sidebar.number_input("EV/EBITDA", 8.0)
mult_r = st.sidebar.number_input("EV/Revenue", 0.0)

df = run_financial(
    years, hw_cost, install_cost, asp, units_y1, unit_cagr,
    loads_site, kwh_shift, spread, share_savings,
    mw_y1, mw_cagr, order_fee, gross_margin, ebitda_margin,
    dev_total, dev_years, mult_e, mult_r
)

st.subheader("Financial Projection")
st.dataframe(df.style.format("${:,.0f}"))
st.bar_chart(df[["Hardware Revenue", "VPP Revenue"]])
st.line_chart(df["Enterprise Value"])
