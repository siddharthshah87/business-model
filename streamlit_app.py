import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="HEMS Simulator (No SaaS)", layout="wide")
st.title("📊 HEMS Business Simulator – Hardware + VPP/DCR Model")

# Sidebar Inputs
st.sidebar.header("Hardware & Sales Inputs")
bom_cost = st.sidebar.number_input("BOM + Shipping ($)", 400)
install_cost = st.sidebar.number_input("Installer Cost ($)", 250)
asp = st.sidebar.number_input("Retail Price ($)", 1500)
units_y1 = st.sidebar.number_input("Year 1 Units", 1000)
unit_cagr = st.sidebar.slider("Annual Unit Growth", 0.0, 1.0, 0.4)

st.sidebar.header("DCR (VPP) Revenue")
enable_dcr = True
dcr_mw_y1 = st.sidebar.number_input("Year 1 DCR Capacity (MW)", 1.0)
dcr_price_mwmo = st.sidebar.number_input("DCR $/MW/month", 6000)
dcr_hours_per_year = st.sidebar.number_input("Event Hours per Year", 30)
dcr_price_mwh = st.sidebar.number_input("DCR $/MWh for Dispatch", 150)
aggregator_cut = st.sidebar.slider("Aggregator Cut (%)", 0.0, 0.5, 0.3)

st.sidebar.header("GTM Strategy Over Time")
gtm_profiles = {
    "Installer-led": {"attach_start": 0.6, "attach_end": 0.9},
    "OEM Bundle": {"attach_start": 0.4, "attach_end": 0.75},
    "Utility Co-brand": {"attach_start": 0.7, "attach_end": 0.95},
    "Direct-to-Consumer": {"attach_start": 0.3, "attach_end": 0.65}
}
gtm_selected = st.sidebar.selectbox("Initial GTM", list(gtm_profiles.keys()))
gtm_profile = gtm_profiles[gtm_selected]

st.sidebar.header("Dev & Financials")
dev_total = st.sidebar.number_input("Total Dev Cost ($)", 2_000_000)
dev_years = st.sidebar.slider("Dev Amortization (years)", 1, 10, 5)
gm = st.sidebar.slider("Gross Margin (%)", 0.0, 1.0, 0.35)
ebitda_margin = st.sidebar.slider("EBITDA Margin (%)", 0.0, 0.5, 0.15)
years = st.sidebar.slider("Projection Years", 3, 10, 5)
ev_mult = st.sidebar.number_input("EV / Revenue Multiple", 3.0)

# Simulation
def simulate():
    amort = dev_total / dev_years
    hw_units = units_y1
    results = []
    for yr in range(years):
        # GTM attach rate ramp
        attach_rate = np.linspace(gtm_profile["attach_start"], gtm_profile["attach_end"], years)[yr]

        hw_rev = hw_units * asp * attach_rate
        hw_cogs = hw_units * (bom_cost + install_cost)

        mw = dcr_mw_y1 * (1 + 0.5)**yr
        dcr_rev_capacity = mw * dcr_price_mwmo * 12
        dcr_rev_energy = mw * dcr_hours_per_year * dcr_price_mwh
        dcr_rev = (dcr_rev_capacity + dcr_rev_energy) * (1 - aggregator_cut)

        total_rev = hw_rev + dcr_rev
        gross_profit = total_rev * gm
        ebitda = total_rev * ebitda_margin - amort
        ev = total_rev * ev_mult

        results.append({
            "Year": f"Year {yr+1}",
            "HW Units": hw_units,
            "Attach Rate": attach_rate,
            "Revenue ($)": total_rev,
            "DCR Revenue": dcr_rev,
            "Gross Profit": gross_profit,
            "EBITDA": ebitda,
            "Enterprise Value": ev
        })

        hw_units = int(hw_units * (1 + unit_cagr))
    return pd.DataFrame(results).set_index("Year")

df = simulate()

st.subheader("📈 Financial Projections")
st.dataframe(df.style.format("${:,.0f}"))
st.bar_chart(df[["Revenue ($)", "DCR Revenue"]])
st.line_chart(df["Enterprise Value"])

csv = df.to_csv().encode('utf-8')
st.download_button("📥 Download Financials (CSV)", data=csv, file_name="hems_vpp_only.csv", mime="text/csv")
