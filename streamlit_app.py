
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from math import pow

st.set_page_config(page_title="HEMS → VPP Investor Story", layout="wide")
st.title("🏠→⚡ Hardware-to-Grid Revenue Simulator")

HELP = {"units_y1":"ELI5: Kits shipped year 1.","installer":"ELI5: Cash to electrician per install."}

ISO_CAP = {"CAISO":55,"ISO‑NE":40,"NYISO":36,"PJM":100,"MISO":35}
ISO_EVT = {"CAISO":150,"ISO‑NE":125,"NYISO":100,"PJM":150,"MISO":100}
PHASE = {"Pilot":dict(asp=1500,g=0.6,b=1.0),
         "Scale":dict(asp=1200,g=0.4,b=1.1),
         "Mature":dict(asp=900 ,g=0.15,b=1.25)}

def sim(Y,asp0,g,cap,evt,hrs,mw0,mw_g,unit0,loads,installer,market,gp,disc):
    rows=[]; units=unit0; mw=mw0
    for y in range(Y):
        hw = units*asp0
        vpp= mw*1000*cap + mw*hrs*evt
        total=hw+vpp
        cac=installer+market
        ltv=sum((vpp/units)/pow(1+disc,t) for t in range(1,8))
        rows.append(dict(Year=f"Y{y+1}",Hardware=hw,VPP=vpp,Revenue=total,CAC=cac,LTV=ltv,Units=units))
        units=int(units*(1+g)); mw*=1+mw_g
    return pd.DataFrame(rows).set_index("Year")

side=st.sidebar
phase=side.selectbox("Phase",list(PHASE))
iso=side.selectbox("ISO",list(ISO_CAP))
yrs=side.slider("Horizon (yrs)",5,10,7)
unit0=side.number_input("Units Year 1",1000,step=100,help=HELP["units_y1"])
mw0=side.number_input("MW Year 1",1.0,step=0.5)
mw_g=side.slider("MW CAGR",0.0,1.0,0.6)
hrs=side.number_input("Event hours/yr",10)
loads=side.number_input("Loads/home",3)
installer=side.number_input("Installer fee",300,help=HELP["installer"])
market=side.number_input("Mktg $",200)
gp=side.slider("HW gross margin",0.0,1.0,0.35)
disc=side.slider("Discount rate",0.05,0.2,0.1)

cfg=PHASE[phase]
df=sim(yrs,cfg["asp"],cfg["g"],ISO_CAP[iso]*cfg["b"],ISO_EVT[iso],hrs,
       mw0,mw_g,unit0,loads,installer,market,gp,disc)

st.area_chart(df[["Hardware","VPP"]])

mix=df.iloc[-1][["Hardware","VPP"]].reset_index().rename(columns={"index":"src",0:"val"})
st.altair_chart(alt.Chart(mix).mark_arc(innerRadius=30).encode(theta="val:Q",color="src:N"),use_container_width=True)

st.dataframe(df.style.format("${:,.0f}"))

