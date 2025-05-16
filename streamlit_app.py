
import streamlit as st
import pandas as pd
import numpy as np

# ---------- Base datasets ----------
@st.cache_data(show_spinner=False)
def load_state_market():
    # Placeholder dataset; replace with census + EV-ready stats
    return pd.DataFrame({
        "state":["CA","TX","FL","NY","IL"],
        "housing_units":[14000000,11000000,9600000,8300000,5200000]
    })

# ---------- Market sizing ----------
def build_state_params(selected_states, years):
    "Return dict state -> parameter dict with defaults"
    params = {}
    for s in selected_states:
        params[s] = dict(
            activation_delay=0,
            ev_ready_pct=0.5,
            attach_start=0.6,
            attach_end=0.9
        )
    return params

def calc_som_curve(df_states, state_params, panel_pct, start_pen, end_pen, years):
    som_by_year = np.zeros(years)
    pen_curve = np.linspace(start_pen, end_pen, years)
    for state,row in df_states.set_index("state").loc[state_params.keys()].iterrows():
        p = state_params[state]
        tam = row["housing_units"] * panel_pct
        sam = tam * p["ev_ready_pct"]
        attach_curve = np.linspace(p["attach_start"], p["attach_end"], years)
        for yr in range(years):
            if yr < p["activation_delay"]:
                continue
            active_year = yr - p["activation_delay"]
            som_by_year[yr] += sam * pen_curve[active_year] * attach_curve[active_year]
    return som_by_year

# ---------- Financial simulator ----------
def run_financial_sim(years, hw_unit_cost, hw_install_cost, hw_sale_price,
                      hw_units_year1, hw_unit_growth,
                      arr_per_site, loads_per_site, kwh_shift, spread, share,
                      mw_year1, mw_growth,
                      order_fee, gross_margin_target, core_ebitda_margin,
                      dev_total, dev_years,
                      mult_ebitda, mult_rev,
                      attach_rate_years):
    hw_units = hw_units_year1
    mw = mw_year1
    amort = dev_total / dev_years if dev_years else 0
    rows = []
    for yr in range(years):
        hw_rev = hw_units * hw_sale_price
        sites = mw * 250
        attached_sites = sites * attach_rate_years[yr]
        saas_rev = attached_sites * arr_per_site
        arb_rev = attached_sites * loads_per_site * kwh_shift * 365 * spread * share

        tot_rev = hw_rev + saas_rev + arb_rev
        core_ebitda = tot_rev * core_ebitda_margin
        rpt_ebitda = core_ebitda - amort

        ev_e = rpt_ebitda * mult_ebitda if mult_ebitda else 0
        ev_r = tot_rev * mult_rev if mult_rev else 0
        ev = ev_r if mult_rev else ev_e

        rows.append(dict(
            Year=f"Year {yr+1}",
            HW_Units=hw_units,
            Total_Revenue=tot_rev,
            Attach_Rate=attach_rate_years[yr],
            Reported_EBITDA=rpt_ebitda,
            Enterprise_Value=ev
        ))

        hw_units = int(hw_units * (1 + hw_unit_growth))
        mw *= (1 + mw_growth)
    return pd.DataFrame(rows).set_index("Year")

# ---------- UI ----------
st.set_page_config(page_title="Collar+Sub‑panel Model v5", layout="wide")
sidebar = st.sidebar
sidebar.title("Inputs")

years = sidebar.slider("Projection years",3,10,5)

# Hardware
sidebar.subheader("Hardware")
hw_unit_cost = sidebar.number_input("BOM + landing cost ($, help="ELI5: Cost to build and ship ONE collar and smart subpanel kit (before any profit).")")
hw_install_cost = sidebar.number_input("Installer payment ($, help="ELI5: Cash we hand the electrician or channel partner per installation.")")
hw_sale_price = sidebar.number_input("Sale price to customer ($, help="ELI5: Sticker price the homeowner pays for the hardware kit.")")
hw_units_year1 = sidebar.number_input("Units shipped in Year1",1000,step=100, help="ELI5: How many kits we expect to ship in the very first forecast year.")
hw_unit_growth = sidebar.slider("Annual unit growth",0.0,1.0,0.4, help="ELI5: Annual percentage growth of shipments. 0.6 means +60 % every year.")

# Dev
sidebar.subheader("Dev & Cert")
dev_total = sidebar.number_input("Total dev cost ($, help="ELI5: Total R&D, UL/FCC certification and appdevelopment spend before selling units.")")
dev_years = sidebar.slider("Amortization years",1,years,5, help="ELI5: Over how many years we ‘expense’ that big dev cost.")

# SaaS constants
sidebar.subheader("SaaS constants")
arr_per_site = sidebar.number_input("ARR per site ($/yr, help="ELI5: Yearly subscription fee each house pays for our software/VPP service.")")
loads_per_site = sidebar.number_input("Loads per site",4,step=1, help="ELI5: Big appliances per house we can control (EV, heat‑pump, water‑heater, dryer…).")
kwh_shift = sidebar.number_input("kWh shift per load/day",3.0,step=0.5, help="ELI5: Energy (kWh) we can move off‑peak for each load every day.")
spread = sidebar.number_input("Price spread ($/kWh, help="ELI5: Average $ difference between cheap offpeak and pricey peak electricity.")")
share = sidebar.slider("Platform share",0.0,1.0,0.4, help="ELI5: Our cut of the savings. 0.4 = we keep 40 %, homeowner keeps 60 %.")

# Aggregation
sidebar.subheader("Aggregation")
mw_year1 = sidebar.number_input("MW Year1",4.0,step=0.5, help="ELI5: Flexible‑load capacity (in MW) we aggregate in the first year.")
mw_growth = sidebar.slider("MW growth",0.0,1.0,0.6, help="ELI5: Annual growth rate of that MW portfolio.")
order_fee = sidebar.number_input("Market fee ($/MWh, help="ELI5: All in cost we pay the ISO/utility for each MWh we bid into markets.")

# Finance
sidebar.subheader("Finance")
gm = sidebar.slider("Blended GM",0.0,0.9,0.35, help="ELI5: % of revenue left after paying hardware COGS and 2222 fees.")
ebitda_margin = sidebar.slider("Core EBITDA margin",0.0,0.5,0.15, help="ELI5: % of revenue left after ALL OpEx except amortized dev cost.")
mult_e = sidebar.number_input("EV / EBITDA multiple",8.0,step=0.5, help="ELI5: How many times EBITDA investors might pay for the business.")
mult_r = sidebar.number_input("EV / Revenue multiple",0.0,50.0,0.0, help="ELI5: How many times Revenue investors might pay (set to 0 to ignore).")

# Tabs
tab_fin, tab_gtm = st.tabs(["Financial","GTM & Region Detail"])

with tab_gtm:
    df_states = load_state_market()
    all_states = df_states.state.tolist()
    selected = st.multiselect("Target states",all_states,default=all_states[:3])
    st.markdown("### Per‑state settings")
    state_params = {}
    for st_name in selected:
        with st.expander(st_name):
            delay = st.slider(f"Activation delay (years) – {st_name}",0,years-1,0,key=f"delay_{st_name}")
            ev_pct = st.slider(f"EV‑ready % – {st_name}",0.0,1.0,0.5,key=f"ev_{st_name}")
            attach_start = st.slider(f"Attach rate Year1 – {st_name}",0.0,1.0,0.6,key=f"as_{st_name}")
            attach_end = st.slider(f"Attach rate Year{years} – {st_name}",0.0,1.0,0.9,key=f"ae_{st_name}")
            state_params[st_name] = dict(
                activation_delay=delay,
                ev_ready_pct=ev_pct,
                attach_start=attach_start,
                attach_end=attach_end
            )
    panel_pct = st.slider("% homes ≤100A",0.0,1.0,0.4)
    start_pen = st.number_input("SAM penetration Year1 (%)",0.0,100.0,0.5)/100
    end_pen = st.number_input(f"SAM penetration Year{years} (%)",0.0,100.0,5.0)/100

    som_curve = calc_som_curve(df_states,state_params,panel_pct,start_pen,end_pen,years)
    st.bar_chart(pd.DataFrame({"SOM_units":som_curve}))

with tab_fin:
    # derive attach rate each year (weighted avg)
    total_sites_year = [mw_year1*(1+mw_growth)**yr*250 for yr in range(years)]
    attach_sites_year = []
    # compute global attach rate curve using SOM and total sites
    attach_rate_curve = []
    for yr in range(years):
        active_sites = total_sites_year[yr]*share  # placeholder, will adjust later
    # For simplicity: use average of state attach rates each year
    attach_rate_years = []
    for yr in range(years):
        att=0
        for st_name,p in state_params.items():
            if yr < p["activation_delay"]:
                continue
            ys = np.linspace(p["attach_start"],p["attach_end"],years)
            att += ys[yr]
        attach_rate_years.append(att/len(state_params) if state_params else 0)

    df_fin = run_financial_sim(years,
                               hw_unit_cost,hw_install_cost,hw_sale_price,
                               hw_units_year1,hw_unit_growth,
                               arr_per_site,loads_per_site,kwh_shift,spread,share,
                               mw_year1,mw_growth,order_fee,
                               gm,ebitda_margin,
                               dev_total,dev_years,
                               mult_e,mult_r,
                               attach_rate_years)

    st.dataframe(df_fin.style.format("${:,.0f}"))
    st.bar_chart(df_fin["Total_Revenue"])
    st.line_chart(df_fin["Enterprise_Value"])
