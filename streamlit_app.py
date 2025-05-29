
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from math import pow

st.set_page_config(page_title="HEMS → Grid Investor Model", layout="wide")
st.title("🏠→⚡  Hardware‑to‑Grid Revenue Simulator v4")

HELP = {"kw_home":"Average curtailable kW per installed home (EV + HPWH + dryer).",
        "churn":"Homes that drop out each year (move, uninstall, opt-out).",
        "bom_drop":"Learning curve: BOM cost falls this % every year.",
        "rebate":"Share of rebate we keep as extra revenue."}

ISO_CAP = {"CAISO":(40,55,75),"ISO‑NE":(30,40,55),"NYISO":(28,36,48),"PJM":(60,100,150),"MISO":(25,35,50)}
ISO_EVT = {"CAISO":150,"ISO‑NE":125,"NYISO":100,"PJM":150,"MISO":100}
SCEN = {"Base":dict(asp=1200,unit_g=0.40,tier=1),
        "Bull":dict(asp=1000,unit_g=0.50,tier=2),
        "Bear":dict(asp=1500,unit_g=0.25,tier=0)}

def capacity_price(iso,tier): return ISO_CAP[iso][tier]

def simulate(Y,asp0,unit_g,bom_drop,rebate_share,
             kw_home,price_kw,evt_price,evt_prob,hours_evt,
             units0,churn,installer,marketing,gp,disc):

    rows=[]; units=units0; cum_units=0
    bom=asp0*(1-gp)
    for y in range(Y):
        cur_bom = bom*pow(1-bom_drop,y)
        hw_gp   = (asp0-cur_bom)*units
        rebate  = rebate_share*500*units
        hw_rev  = asp0*units + rebate

        cum_units += units
        active_units = int(cum_units*pow(1-churn,y))
        mw = active_units*kw_home/1000

        vpp_cap = mw*1000*price_kw
        vpp_evt = mw*hours_evt*evt_price*evt_prob
        vpp_rev = vpp_cap+vpp_evt
        total   = hw_rev+vpp_rev
        ltv = sum(((vpp_rev/active_units)/pow(1+disc,t)) for t in range(1,8))

        rows.append(dict(Year=f"Y{y+1}",Units=units,CumUnits=cum_units,
                         MW=round(mw,2),Hardware=hw_rev,VPP=vpp_rev,
                         Revenue=total,LTV=ltv))
        units=int(units*(1+unit_g))
    return pd.DataFrame(rows).set_index("Year")

side=st.sidebar
scenario=side.radio("Scenario",list(SCEN))
iso=side.selectbox("ISO",list(ISO_CAP))
Y=side.slider("Years",5,10,7)
units0=side.number_input("Units Year 1",1000,step=100)
kw_home=side.number_input("kW per home",3.0,help=HELP["kw_home"])
asp0=side.number_input("ASP $",SCEN[scenario]["asp"])
unit_g=side.slider("Unit CAGR",0.0,1.0,SCEN[scenario]["unit_g"])
bom_drop=side.slider("BOM learning %/yr",0.0,0.2,0.05,step=0.01,help=HELP["bom_drop"])
rebate_share=side.slider("Rebate share",0.0,1.0,0.25,help=HELP["rebate"])

tier=SCEN[scenario]["tier"]
price_kw=capacity_price(iso,tier)
side.caption(f"Capacity price = ${price_kw}/kW‑yr  (tier {['P10','P50','P90'][tier]})")
evt_price=ISO_EVT[iso]
hours_evt=side.number_input("Event hours/yr",10)
evt_prob=side.slider("Event probability",0.0,1.0,0.3)
churn=side.slider("Churn %/yr",0.0,0.20,0.03,step=0.01,help=HELP["churn"])
installer=side.number_input("Installer fee $",300)
marketing=side.number_input("Marketing $",200)
gp=side.slider("Initial HW GM",0.0,1.0,0.35)
disc=side.slider("Discount rate",0.05,0.20,0.1)

df=simulate(Y,asp0,unit_g,bom_drop,rebate_share,
            kw_home,price_kw,evt_price,evt_prob,hours_evt,
            units0,churn,installer,marketing,gp,disc)

st.area_chart(df[["Hardware","VPP"]])

mix=df.iloc[-1][["Hardware","VPP"]].reset_index().rename(columns={"index":"src",0:"val"})
st.altair_chart(
    alt.Chart(mix).mark_arc(innerRadius=30).encode(
        theta=alt.Theta("val:Q"), color="src:N", tooltip=mix.columns.tolist()
    ), use_container_width=True
)

st.dataframe(df.style.format("${:,.0f}"))
