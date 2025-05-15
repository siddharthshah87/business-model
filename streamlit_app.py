
import streamlit as st
import pandas as pd
import numpy as np

# ---------------- Financial simulator ----------------
def run_financial_sim(years,
                      hw_unit_cost, hw_install_cost, hw_sale_price,
                      hw_units_year1, hw_unit_growth,
                      arr_per_site, attach_rate,
                      loads_per_site, kwh_shift, spread, share,
                      mw_year1, mw_growth,
                      order_fee, gross_margin_target, core_ebitda_margin,
                      dev_total, dev_years,
                      mult_ebitda, mult_rev):
    hw_units = hw_units_year1
    mw = mw_year1
    amort = dev_total / dev_years if dev_years else 0
    rows = []
    for yr in range(1, years + 1):
        hw_rev = hw_units * hw_sale_price

        # SaaS + arbitrage only for attached sites
        sites = mw * 250
        attached_sites = sites * attach_rate
        saas_rev = attached_sites * arr_per_site
        arb_rev = attached_sites * loads_per_site * kwh_shift * 365 * spread * share

        tot_rev = hw_rev + saas_rev + arb_rev
        core_ebitda = tot_rev * core_ebitda_margin
        rpt_ebitda = core_ebitda - amort

        ev_e = rpt_ebitda * mult_ebitda if mult_ebitda else 0
        ev_r = tot_rev * mult_rev if mult_rev else 0
        ev = ev_r if mult_rev else ev_e

        rows.append(dict(Year=f"Year {{yr}}",
                         HW_Units=hw_units,
                         Total_Revenue=tot_rev,
                         Reported_EBITDA=rpt_ebitda,
                         Enterprise_Value=ev))
        hw_units = int(hw_units * (1 + hw_unit_growth))
        mw *= (1 + mw_growth)
    return pd.DataFrame(rows).set_index("Year")

# -------------- Market sizing --------------
@st.cache_data(show_spinner=False)
def load_state_market():
    return pd.DataFrame({
        "state": ["CA","TX","FL","NY","IL"],
        "housing_units":[14000000,11000000,9600000,8300000,5200000]
    })

def calc_market(df_states, targets, panel_pct, ev_pct,
                start_pen, end_pen, years, delay):
    df = df_states[df_states.state.isin(targets)].copy()
    df["TAM"] = df.housing_units * panel_pct
    df["SAM"] = df.TAM * ev_pct
    # Staggered activation: each additional state joins linearly over 'delay' years
    active_states_curve = np.minimum(1.0,
        np.arange(years)+1 / max(1, delay))
    som_curve = np.linspace(start_pen, end_pen, years)
    som_units_year = []
    for yr in range(years):
        active_fraction = active_states_curve[yr]
        som_units_year.append(df["SAM"].sum()*som_curve[yr]*active_fraction)
    return df, som_units_year

# -------------- UI --------------
st.set_page_config(page_title="Collar+Sub‑panel Model v4", layout="wide")
s = st.sidebar
s.title("Inputs (hover for help)")

years = s.slider("Projection years",3,10,5)

# Hardware
s.subheader("Hardware")
hw_unit_cost = s.number_input("BOM + landing cost ($)",400.0,step=50.0,help="Cost to build and ship ONE collar + smart sub‑panel kit (before any profit).")
hw_install_cost = s.number_input("Installer payment ($)",250.0,step=25.0,help="What we pay the electrician / channel partner per install.")
hw_sale_price = s.number_input("Sale price to customer ($)",1500.0,step=50.0,help="Sticker price the homeowner pays for the hardware (kit only).")
hw_units_year1 = s.number_input("Units shipped in Year 1",1000,step=100,help="How many kits we expect to ship in Year 1 of the projection.")
hw_unit_growth = s.slider("Annual unit growth",0.0,1.0,0.4,help="Annual growth rate of hardware shipments. 0.6 = +60 % YoY.")

# Dev
s.subheader("Dev & Cert")
dev_total = s.number_input("Total dev cost ($)",2000000,step=100000,help="Total R&D + UL/FCC + app‑dev money spent upfront before selling units.")
dev_years = s.slider("Amortization years",1,years,5,help="Over how many years we spread that dev cost in OpEx.")

# SaaS
s.subheader("SaaS / DER")
arr_per_site = s.number_input("ARR per site ($/yr)",120.0,step=10.0,help="Annual recurring revenue we charge each home for the software/HEMS service.")
attach_rate = s.slider("SaaS attach rate",0.0,1.0,1.0,help="What fraction of installed panels actually subscribe to our SaaS/DER program.")
loads_per_site = s.number_input("Loads per site",4,step=1,help="Average number of big controllable loads per house (EV, heat pump, etc.).")
kwh_shift = s.number_input("kWh shift per load/day",3.0,step=0.5,help="How many kWh per load we can shift out of peak each day.")
spread = s.number_input("Price spread ($/kWh)",0.05,step=0.01,help="Average price difference between peak and off‑peak electricity ($/kWh).")
share = s.slider("Platform share",0.0,1.0,0.4,help="Our cut of the savings (0.4 = 40 %).")

# Order 2222
s.subheader("Aggregation")
mw_year1 = s.number_input("MW Year 1",4.0,step=0.5,help="Flexible load capacity (MW) enrolled in aggregations in Year 1.")
mw_growth = s.slider("MW growth",0.0,1.0,0.6,help="Growth rate of enrolled MW each year.")
order_fee = s.number_input("Market fee ($/MWh)",1.0,step=0.5,help="All‑in Order 2222 market & settlement fees ($ per MWh dispatched).")

# Finance
s.subheader("Finance")
gm = s.slider("Blended GM",0.0,0.9,0.35,help="Blended gross margin after COGS and 2222 fees.")
ebitda_margin = s.slider("Core EBITDA margin",0.0,0.5,0.15,help="EBITDA margin BEFORE dev‑cost amortization.")
mult_e = s.number_input("EV / EBITDA multiple",8.0,step=0.5,help="Multiple of EBITDA investors might pay (set 0 to ignore).")
mult_r = s.number_input("EV / Revenue multiple",0.0,50.0,0.0,help="Multiple of Revenue investors might pay (set 0 to ignore).")

# GTM tab
tab_fin, tab_gtm = st.tabs(["Financial","GTM & Market"])

with tab_gtm:
    df_states = load_state_market()
    targets = st.multiselect("Target states",df_states.state.tolist(),default=df_states.state.tolist()[:3])
    panel_pct = st.slider("% homes ≤100A",0.0,1.0,0.4)
    ev_pct = st.slider("% EV-ready",0.0,1.0,0.5)
    start_pen = st.number_input("Year1 SAM penetration %",0.0,100.0,0.5)/100
    end_pen = st.number_input(f"Year{years} SAM penetration %",0.0,100.0,5.0)/100
    region_delay = st.slider("Years for all regions to activate",1,years,3,help="Extra years before each additional target state opens up TOU incentives (linear ramp).")

    df_market,som_units_year = calc_market(df_states,targets,panel_pct,ev_pct,
                                           start_pen,end_pen,years,region_delay)
    st.dataframe(df_market.set_index("state").style.format("{:,.0f}"))
    st.bar_chart(pd.DataFrame({"SOM_units":som_units_year}))

with tab_fin:
    df = run_financial_sim(years,
                           hw_unit_cost,hw_install_cost,hw_sale_price,
                           hw_units_year1,hw_unit_growth,
                           arr_per_site,attach_rate,
                           loads_per_site,kwh_shift,spread,share,
                           mw_year1,mw_growth,order_fee,
                           gm,ebitda_margin,
                           dev_total,dev_years,
                           mult_e,mult_r)
    st.dataframe(df.style.format("${:,.0f}"))
    st.bar_chart(df["Total_Revenue"])
    st.line_chart(df["Enterprise_Value"])
