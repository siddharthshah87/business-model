import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Enhanced HEMS Business Simulator", layout="wide")
st.title("📊 Enhanced HEMS Business Simulator")

# Sidebar Inputs
st.sidebar.header("Hardware & Sales Inputs")
bom_cost = st.sidebar.number_input("BOM + Shipping ($)", 400)
install_cost = st.sidebar.number_input("Installer Cost ($)", 250)
asp = st.sidebar.number_input("Retail Price ($)", 1500)
units_y1 = st.sidebar.number_input("Year 1 Units", 1000)
unit_cagr = st.sidebar.slider("Annual Unit Growth", 0.0, 1.0, 0.4)

st.sidebar.header("SaaS & DR Settings")
enable_saas = st.sidebar.checkbox("Enable SaaS Subscription", value=True)
arr = st.sidebar.number_input("SaaS Revenue per Site ($/yr)", 120) if enable_saas else 0

enable_dcr = st.sidebar.checkbox("Enable DCR (Order 2222) Revenue", value=True)
if enable_dcr:
    dcr_mw_y1 = st.sidebar.number_input("Year 1 DCR Capacity (MW)", 1.0)
    dcr_price_mwmo = st.sidebar.number_input("DCR $/MW/month", 6000)
    dcr_hours_per_year = st.sidebar.number_input("Event Hours per Year", 30)
    dcr_price_mwh = st.sidebar.number_input("DCR $/MWh for Dispatch", 150)

aggregator_cut = st.sidebar.slider("Aggregator Cut (%)", 0.0, 0.5, 0.3)
region = st.sidebar.selectbox("ISO Region", ["CAISO", "PJM", "ISO-NE", "NYISO", "MISO"])

st.sidebar.header("Dev Costs")
dev_total = st.sidebar.number_input("Total Dev Cost ($)", 2_000_000)
dev_years = st.sidebar.slider("Dev Cost Amortization (years)", 1, 10, 5)

st.sidebar.header("Financial Settings")
gm = st.sidebar.slider("Gross Margin (%)", 0.0, 1.0, 0.35)
ebitda_margin = st.sidebar.slider("EBITDA Margin (%)", 0.0, 0.5, 0.15)
years = st.sidebar.slider("Projection Years", 3, 10, 5)
ev_mult = st.sidebar.number_input("EV / Revenue Multiple", 3.0)

# Simulator
def simulate():
    amort = dev_total / dev_years
    hw_units = units_y1
    results = []
    for yr in range(years):
        hw_rev = hw_units * asp
        hw_cogs = hw_units * (bom_cost + install_cost)
        saas_rev = hw_units * arr if enable_saas else 0

        # DCR revenue modeling
        if enable_dcr:
            mw = dcr_mw_y1 * (1 + 0.5)**yr
            dcr_rev_capacity = mw * dcr_price_mwmo * 12
            dcr_rev_energy = mw * dcr_hours_per_year * dcr_price_mwh
            dcr_rev = dcr_rev_capacity + dcr_rev_energy
            dcr_rev *= (1 - aggregator_cut)
        else:
            dcr_rev = 0

        total_rev = hw_rev + saas_rev + dcr_rev
        gross_profit = total_rev * gm
        ebitda = total_rev * ebitda_margin - amort
        ev = total_rev * ev_mult

        results.append({
            "Year": f"Year {yr+1}",
            "HW Units": hw_units,
            "Revenue ($)": total_rev,
            "SaaS Revenue": saas_rev,
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
st.bar_chart(df[["Revenue ($)", "SaaS Revenue", "DCR Revenue"]])
st.line_chart(df["Enterprise Value"])

csv = df.to_csv().encode('utf-8')
st.download_button("📥 Download Financials (CSV)", data=csv, file_name="hems_financials.csv", mime="text/csv")
