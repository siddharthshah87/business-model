
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="HEMS → VPP Investor Story Simulator", layout="wide")
st.title("🏠→⚡  Hardware‑to‑Grid Revenue Simulator")

HELP={"asp":"ELI5: Sticker price the homeowner pays today.","installer":"ELI5: Cash we pay the electrician per install.",
"units_y1":"ELI5: Kits shipped year 1.","unit_cagr":"ELI5: Annual growth.",
"price_kwyr":"ELI5: Capacity dollars per kW-year.","event":"ELI5: Event payout $/MWh ...",}

ISO_CAP_PRICE={"CAISO":55,"ISO‑NE":40,"NYISO":36,"PJM":100,"MISO":35}
ISO_EVENT_PRICE={"CAISO":150,"ISO‑NE":125,"NYISO":100,"PJM":150,"MISO":100}
PHASES={"Pilot → HW‑led":dict(asp=1500,unit_cagr=0.6,iso_bump=1.0),
"Scale‑up → Mixed":dict(asp=1200,unit_cagr=0.4,iso_bump=1.1),
"Mature → Grid‑led":dict(asp=900,unit_cagr=0.15,iso_bump=1.25)}

def simulate(years,asp0,unit_cagr,price_kwyr,price_event,hours_ev,loads_site,
             mw_y1,mw_cagr,installer_fee,marketing,gross_margin,disc_rate,units_y1):
    rows=[]; units=units_y1; mw=mw_y1
    for yr in range(years):
        hw_rev=units*asp0
        vpp_cap=mw*1000*price_kwyr
        vpp_evt=mw*hours_ev*price_event
        vpp_rev=vpp_cap+vpp_evt
        total=hw_rev+vpp_rev
        cac=installer_fee+marketing
        ltv=sum((vpp_rev/units)/pow(1+disc_rate,t) for t in range(1,8))
        rows.append(dict(Year=f"Y{yr+1}",Units=units,Hardware=hw_rev,VPP=vpp_rev,
                         Revenue=total,CAC=cac,LTV=ltv))
        units=int(units*(1+unit_cagr)); mw*=1+mw_cagr
    return pd.DataFrame(rows).set_index("Year")

side=st.sidebar
phase=side.selectbox("Business Phase",list(PHASES))
iso=side.selectbox("ISO Region",list(ISO_CAP_PRICE))
years=side.slider("Projection years",5,10,7)
units_y1=side.number_input("Units shipped Year 1",1000,step=100,help=HELP["units_y1"])

asp0=side.number_input("Retail ASP ($)",PHASES[phase]["asp"])
unit_cagr=side.slider("Unit CAGR",0.0,1.0,PHASES[phase]["unit_cagr"])
price_kwyr=ISO_CAP_PRICE[iso]*PHASES[phase]["iso_bump"]
price_event=ISO_EVENT_PRICE[iso]
hours_ev=side.number_input("Event hours/year",10)
mw_y1=side.number_input("MW Year 1",1.0)
mw_cagr=side.slider("MW CAGR",0.0,1.0,0.6)
loads_site=side.number_input("Loads/home",3)
installer_fee=side.number_input("Installer fee",300)
marketing=side.number_input("Marketing/ sale",200)
gross_margin=side.slider("Hardware GM",0.0,1.0,0.35)
disc_rate=side.slider("Discount rate",0.05,0.20,0.1)

df=simulate(years,asp0,unit_cagr,price_kwyr,price_event,hours_ev,loads_site,
            mw_y1,mw_cagr,installer_fee,marketing,gross_margin,disc_rate,units_y1)

st.subheader(f"ISO {iso}  capacity = ${price_kwyr}/kW·yr")
st.area_chart(df[["Hardware","VPP"]])

mix=df.iloc[-1][["Hardware","VPP"]]
fig=px.pie(names=mix.index, values=mix.values, title=f"Revenue mix Year {years}")
st.plotly_chart(fig,use_container_width=True)

st.dataframe(df.style.format("${:,.0f}"))
csv=df.to_csv().encode("utf-8")
st.download_button("Download CSV",csv,"sim.csv","text/csv")
