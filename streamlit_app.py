
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from math import pow

st.set_page_config(page_title="HEMS → VPP Investor Story", layout="wide")
st.title("🏠→⚡  Hardware‑to‑Grid Revenue Simulator  v3")

##############################
# Helper tool‑tips (ELI5)
##############################
HELP = dict(
   units_y1="ELI5: Kits we think we can ship in the very first year of sales.",
   unit_cagr="ELI5: Annual shipment growth. 0.4 means +40 % every year.",
   asp="ELI5: Price each customer pays for the retrofit kit.",
   bom_drop="ELI5: How much cheaper BOM gets each year as we scale.",
   rebate_share="ELI5: % of any government/utility rebate that flows to us (vs. homeowner).",
   installer="ELI5: Cash we hand to the electrician per install.",
   marketing="ELI5: Online ads, channel spiffs per sale.",
   mw_y1="ELI5: Total MW of flexible load under control in Year 1.",
   mw_cagr="ELI5: Annual growth of that MW fleet.",
   price_kw="ELI5: ISO pays this every year for each kW we promise to curtail.",
   evt_price="ELI5: Extra dollars ISO pays per MWh when an event is triggered.",
   evt_prob="ELI5: Chance the ISO actually calls an event in a given year.",
   churn="ELI5: Homes that leave each year (move‑out, opt‑out, failure).",
   ul_cost="ELI5: One‑off dollars we must spend on UL/FCC/DERA paperwork.",
   disc="ELI5: Discount rate investors use when valuing future cash."
)

##############################
# Static ISO price distributions
##############################
ISO_PRICE = {
    "CAISO":{"P10":40,"P50":55,"P90":75},
    "ISO‑NE":{"P10":30,"P50":40,"P90":55},
    "NYISO":{"P10":28,"P50":36,"P90":48},
    "PJM":{"P10":60,"P50":100,"P90":150},
    "MISO":{"P10":25,"P50":35,"P90":50}
}
ISO_EVT  = {"CAISO":150,"ISO‑NE":125,"NYISO":100,"PJM":150,"MISO":100}

##############################
# Scenario presets
##############################
SCEN = {
  "Base": dict(asp=1200,unit_cagr=0.40,cap="P50"),
  "Bull": dict(asp=1000,unit_cagr=0.50,cap="P90"),
  "Bear": dict(asp=1500,unit_cagr=0.25,cap="P10")
}

##############################
# Financial engine
##############################
def simulate(years,asp,unit_cagr,bom_drop,rebate_share,
             price_kw,evt_price,evt_prob,hours_evt,
             units0,mw0,mw_cagr,loads,
             installer,marketing,ul_spend,gp,
             churn,disc):

    rows=[]; units=units0; mw=mw0; bom=asp*(1-gp)  # derive starting BOM from GM
    cum_ul=ul_spend
    for y in range(years):
        # ASP and BOM fall w/ learning
        cur_asp = asp
        cur_bom = bom*pow(1-bom_drop,y)
        hw_gp   = (cur_asp-cur_bom)*units
        rebate  = rebate_share*500*units  # assume $500 rebate pool per unit
        hw_rev  = cur_asp*units + rebate

        # VPP dollars
        # adjust active fleet for churn
        active_mw = mw*(pow(1-churn,y))
        vpp_cap = active_mw*1000*price_kw
        vpp_evt = active_mw*hours_evt*evt_price*evt_prob
        vpp_rev = vpp_cap+vpp_evt

        total   = hw_rev+vpp_rev
        cac = installer+marketing
        ltv = sum(((vpp_rev/units) / pow(1+disc,t)) for t in range(1,8))
        rows.append(dict(
            Year=f"Y{y+1}",Units=units,Hardware=hw_rev,VPP=vpp_rev,
            Revenue=total,HW_GP=hw_gp,UL_CAPEX=cum_ul if y==0 else 0,
            CAC=cac,LTV=ltv
        ))
        units=int(units*(1+unit_cagr))
        mw   *=1+mw_cagr
    return pd.DataFrame(rows).set_index("Year")

##############################
# UI  – sidebar knobs
##############################
side=st.sidebar
scenario=side.radio("Scenario",list(SCEN.keys()))
iso=side.selectbox("ISO",list(ISO_PRICE.keys()))
years=side.slider("Projection horizon (yrs)",5,10,7)

# phase defaults
d=SCEN[scenario]
asp=side.number_input("ASP ($)",d["asp"],step=50,help=HELP["asp"])
unit_cagr=side.slider("Unit CAGR",0.0,1.0,d["unit_cagr"],help=HELP["unit_cagr"])
bom_drop=side.slider("BOM learning curve %/yr",0.0,0.20,0.05,step=0.01,help=HELP["bom_drop"])
rebate_share=side.slider("Rebate share we keep",0.0,1.0,0.25,help=HELP["rebate_share"])

cap_price=ISO_PRICE[iso][d["cap"]]
side.markdown(f"**Capacity price loaded: ${cap_price}/kW‑yr ({d['cap']})**")
evt_price=ISO_EVT[iso]

hours_evt=side.number_input("Event hours / yr",10,help=HELP["evt_price"])
evt_prob=side.slider("Event probability",0.0,1.0,0.3,help=HELP["evt_prob"])

units0=side.number_input("Units shipped Y1",1000,step=100,help=HELP["units_y1"])
mw0=side.number_input("MW under mgmt Y1",1.0,step=0.5,help=HELP["mw_y1"])
mw_cagr=side.slider("MW CAGR",0.0,1.0,0.6)

loads=side.number_input("Loads/home",3)

installer=side.number_input("Installer fee",300,help=HELP["installer"])
marketing=side.number_input("Marketing $",200,help=HELP["marketing"])
ul_spend=side.number_input("UL + FCC one‑off",1_000_000,step=100_000,help=HELP["ul_cost"])

gp=side.slider("Initial hardware gross margin",0.0,1.0,0.35)
churn=side.slider("Churn % / yr",0.0,0.20,0.03,step=0.01,help=HELP["churn"])
disc=side.slider("Discount rate",0.05,0.20,0.1,help=HELP["disc"])

##############################
# Run model
##############################
df=simulate(years,asp,unit_cagr,bom_drop,rebate_share,
            cap_price,evt_price,evt_prob,hours_evt,
            units0,mw0,mw_cagr,loads,
            installer,marketing,ul_spend,gp,
            churn,disc)

##############################
# Charts & tables
##############################
st.header("Revenue evolution")
st.area_chart(df[["Hardware","VPP"]])

st.header(f"Revenue mix Year {years}")
mix=df.iloc[-1][["Hardware","VPP"]].reset_index().rename(columns={"index":"src",0:"val"})
st.altair_chart(alt.Chart(mix).mark_arc(innerRadius=30).encode(
    theta="val:Q",color="src:N",tooltip=["src","val"]
),use_container_width=True)

st.subheader("Detail")
st.dataframe(df.style.format("${:,.0f}"))

# CAC vs LTV
st.subheader("Year‑1 unit economics")
st.metric("CAC / home",f"${df['CAC'][0]:,.0f}")
st.metric("NPV LTV (7 yr)",f"${df['LTV'][0]:,.0f}")

# Download
csv=df.to_csv().encode("utf-8")
st.download_button("⬇ Download CSV",csv,"hems_sim.csv","text/csv")
