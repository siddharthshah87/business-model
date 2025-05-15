
import streamlit as st
import pandas as pd
import numpy as np

def run_financial_sim(years, hw_unit_cost, hw_install_cost, hw_sale_price,
                      hw_units_year1, hw_unit_growth, arr_per_site,
                      loads_per_site, kwh_shift, spread, share,
                      mw_year1, mw_growth, order_fee, gross_margin_target,
                      core_ebitda_margin, dev_cost_total, dev_amort_years,
                      mult_ebitda, mult_rev):
    hw_units = hw_units_year1
    mw = mw_year1
    amort = dev_cost_total / dev_amort_years if dev_amort_years else 0
    rows = []
    for yr in range(1, years + 1):
        hw_rev = hw_units * hw_sale_price
        sites = mw * 250
        saas_rev = sites * arr_per_site
        arb_rev = sites * loads_per_site * kwh_shift * 365 * spread * share
        tot_rev = hw_rev + saas_rev + arb_rev
        tot_kwh = sites * loads_per_site * kwh_shift * 365
        core_ebitda = tot_rev * core_ebitda_margin
        rpt_ebitda = core_ebitda - amort
        ev_e = rpt_ebitda * mult_ebitda if mult_ebitda else 0
        ev_r = tot_rev * mult_rev if mult_rev else 0
        ev = ev_r if mult_rev else ev_e
        rows.append(dict(Year=f"Year {yr}", HW_Units=hw_units,
                         Total_Revenue=tot_rev, Reported_EBITDA=rpt_ebitda,
                         EV_EBITDA=ev_e, EV_Revenue=ev_r,
                         Enterprise_Value=ev))
        hw_units = int(hw_units * (1 + hw_unit_growth))
        mw *= (1 + mw_growth)
    return pd.DataFrame(rows).set_index("Year")

st.set_page_config(page_title="Collar+Sub‑panel Model v3", layout="wide")
s = st.sidebar
s.title("Inputs (hover for help)")

years = s.slider("Projection years", 3, 10, 5)

s.subheader("Hardware economics")
hw_unit_cost = s.number_input("BOM + landing cost ($)", 400.0, step=50.0, help="Cost to build and ship ONE collar + smart sub‑panel kit (before any profit).")
hw_install_cost = s.number_input("Installer payment ($)", 250.0, step=25.0, help="What we pay the electrician / channel partner per install.")
hw_sale_price = s.number_input("Sale price to customer ($)", 1500.0, step=50.0, help="Sticker price the homeowner pays for the hardware (kit only).")
hw_units_year1 = s.number_input("Units shipped in Year 1", 1000, step=100, help="How many kits we expect to ship in Year 1 of the projection.")
hw_unit_growth = s.slider("Annual unit growth rate", 0.0, 1.0, 0.4, help="Annual growth rate of hardware shipments. 0.6 = +60 % YoY.")

s.subheader("Development & certification (OpEx)")
dev_cost_total = s.number_input("Total dev + UL cost ($)", 2000000, step=100000, help="Total R&D + UL/FCC + app‑dev money spent upfront before selling units.")
dev_amort_years = s.slider("Amortization horizon (years)", 1, years, 5, help="Over how many years we spread that dev cost in OpEx.")

s.subheader("DER / SaaS")
arr_per_site = s.number_input("ARR per site ($/yr)", 120.0, step=10.0, help="Annual recurring revenue we charge each home for the software/HEMS service.")
loads_per_site = s.number_input("Controllable loads per site", 4, step=1, help="Average number of big controllable loads per house (EV, heat pump, etc.).")
kwh_shift = s.number_input("kWh shifted per load per day", 3.0, step=0.5, help="How many kWh per load we can shift out of peak each day.")
spread = s.number_input("Wholesale-retail spread ($/kWh)", 0.05, step=0.01, help="Average price difference between peak and off‑peak electricity ($/kWh).")
share = s.slider("Platform share of savings", 0.0, 1.0, 0.4, help="Our cut of the savings (0.4 = 40 %).")

s.subheader("Order 2222 aggregation")
mw_year1 = s.number_input("MW under management, Year 1", 4.0, step=0.5, help="Flexible load capacity (MW) enrolled in aggregations in Year 1.")
mw_growth = s.slider("Annual MW growth rate", 0.0, 1.0, 0.6, help="Growth rate of enrolled MW each year.")
order_fee = s.number_input("Market fees ($/MWh)", 1.0, step=0.5, help="All‑in Order 2222 market & settlement fees ($ per MWh dispatched).")

s.subheader("Financial assumptions")
gross_margin_target = s.slider("Blended gross‑margin", 0.0, 0.9, 0.35, help="Blended gross margin after COGS and 2222 fees.")
core_ebitda_margin = s.slider("Core EBITDA margin", 0.0, 0.5, 0.15, help="EBITDA margin BEFORE dev‑cost amortization.")
mult_ebitda = s.number_input("EV / EBITDA multiple", 8.0, step=0.5, help="Multiple of EBITDA investors might pay (set 0 to ignore).")
mult_rev = s.number_input("EV / Revenue multiple", 0.0, 50.0, 0.0, help="Multiple of Revenue investors might pay (set 0 to ignore).")

df = run_financial_sim(years, hw_unit_cost, hw_install_cost, hw_sale_price,
                       hw_units_year1, hw_unit_growth, arr_per_site,
                       loads_per_site, kwh_shift, spread, share,
                       mw_year1, mw_growth, order_fee, gross_margin_target,
                       core_ebitda_margin, dev_cost_total, dev_amort_years,
                       mult_ebitda, mult_rev)

st.header("Financial Projection")
st.dataframe(df.style.format("${:,.0f}"))
st.bar_chart(df["Total_Revenue"])
st.line_chart(df["Enterprise_Value"])
