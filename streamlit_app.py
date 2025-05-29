
import streamlit as st
import pandas as pd
import numpy as np
from math import pow

st.set_page_config(page_title="HEMS → VPP Investor Story Simulator", layout="wide")
st.title("🏠→⚡  Hardware‑to‑Grid Revenue Simulator")

###############################################################################
# Helper tool‑tips (ELI5)
###############################################################################
HELP = {
    "asp": "ELI5: Sticker price the homeowner pays today.",
    "installer": "ELI5: Cash you hand the electrician per install (your CAC surrogate).",
    "units_y1": "ELI5: Kits shipped in first selling year.",
    "unit_cagr": "ELI5: Annual shipment growth (0.4 = +40 %).",
    "price_kwyr": "ELI5: ISO capacity dollars you earn for every kW you control, per year.",
    "event": "ELI5: Extra dollars when the ISO actually calls an event (rarer).",
    "mw_y1": "ELI5: MW of controllable load you aggregate in year 1.",
    "mw_cagr": "ELI5: Annual MW growth as you add homes.",
}

###############################################################################
# Pre‑loaded ISO capacity & energy prices ($2024)
###############################################################################
ISO_CAP_PRICE = {"CAISO":55,"ISO‑NE":40,"NYISO":36,"PJM":100,"MISO":35}
ISO_EVENT_PRICE = {"CAISO":150,"ISO‑NE":125,"NYISO":100,"PJM":150,"MISO":100}

###############################################################################
# Phase presets (ASP drops, ISO mix improves)
###############################################################################
PHASES = {
    "Pilot → HW‑led":  dict(asp=1500, unit_cagr=0.60, iso_bump=1.0),
    "Scale‑up → Mixed":dict(asp=1200, unit_cagr=0.40, iso_bump=1.1),
    "Mature → Grid‑led":dict(asp=900 , unit_cagr=0.15, iso_bump=1.25),
}

###############################################################################
# Financial engine
###############################################################################
def simulate(years, asp0, unit_cagr,
             price_kwyr, price_event, hours_ev,
             loads_site, mw_y1, mw_cagr,
             installer_fee, marketing, gross_margin,
             disc_rate):
    rows=[]; units=units_y1; mw=mw_y1
    for yr in range(years):
        asp = asp0                                    # ASP fixed per phase
        hw_rev = units*asp
        hw_gp  = hw_rev*gross_margin
        # Grid $
        vpp_cap = mw*1000*price_kwyr
        vpp_evt = mw*hours_ev*price_event
        vpp_rev = vpp_cap+vpp_evt
        total = hw_rev+vpp_rev
        # CAC & LTV (for Year 1 cohort only, simple)
        cac = installer_fee+marketing
        ltv = sum((vpp_rev/units)/pow(1+disc_rate,t) for t in range(1,8))
        rows.append(dict(
            Year=f"Y{yr+1}",Units=units,Hardware=hw_rev,VPP=vpp_rev,
            Revenue=total,CAC=cac,LTV=ltv,GP=hw_gp
        ))
        units=int(units*(1+unit_cagr)); mw*=1+mw_cagr
    return pd.DataFrame(rows).set_index("Year")

###############################################################################
# Sidebar – high‑level knobs
###############################################################################
side=st.sidebar
phase = side.selectbox("Business Phase", list(PHASES))
iso  = side.selectbox("ISO Region", list(ISO_CAP_PRICE))
years=side.slider("Projection horizon",5,10,7)

units_y1 = side.number_input("Units shipped Year 1", 1_000, step=100, help="ELI5: first-year kits")  # <—

# auto‑fill from phase preset but still editable
asp0=side.number_input("Retail ASP ($)", value=PHASES[phase]["asp"],help=HELP["asp"])
unit_cagr=side.slider("Unit CAGR",0.0,1.0,PHASES[phase]["unit_cagr"])
price_kwyr = ISO_CAP_PRICE[iso]*PHASES[phase]["iso_bump"]
price_event= ISO_EVENT_PRICE[iso]
side.markdown(f"*Capacity price loaded: **${price_kwyr}/kW‑yr***")
loader=side.number_input("Event hours / year",10)
mw_y1=side.number_input("MW Year‑1",1.0,help=HELP["mw_y1"])
mw_cagr=side.slider("MW CAGR",0.0,1.0,0.6)
loads_site=side.number_input("Loads per home",3)
installer_fee=side.number_input("Installer fee ($)",300,help=HELP["installer"])
marketing=side.number_input("Marketing $ / sale",200)
gross_margin=side.slider("Hardware Gross margin",0.0,1.0,0.35)
disc_rate=side.slider("Discount rate",0.05,0.20,0.1)

###############################################################################
# Run simulation
###############################################################################
df=simulate(years,asp0,unit_cagr,price_kwyr,price_event,loader,
            loads_site,mw_y1,mw_cagr,installer_fee,marketing,
            gross_margin,disc_rate)

###############################################################################
# Outputs & Story widgets
###############################################################################
col1,col2=st.columns(2)
with col1:
    st.header("Stacked revenue evolution")
    st.area_chart(df[["Hardware","VPP"]])
with col2:
    st.header(f"Revenue mix in Year {years}")
    mix=df.iloc[-1][["Hardware","VPP"]]
    st.plotly_chart(mix.plot.pie(subplots=True,autopct='%1.0f%%',ylabel="").figure,use_container_width=True)

st.subheader("Detailed table")
st.dataframe(df.style.format("${:,.0f}"))

st.subheader("CAC vs LTV (Year‑1 cohort)")
st.metric("CAC / home",f"${df['CAC'][0]:,.0f}")
st.metric("NPV(LTV 7 yr) / home",f"${df['LTV'][0]:,.0f}")

st.subheader("Milestone Ladder")
milestones=pd.DataFrame({
    "Date":["Q4‑25","Q2‑26","2027","2029"],
    "Milestone":["UL 67 + arc‑fault","CAISO 50‑home DERA","PJM entry (UL 916)","100 MW fleet"],
    "Cap‑ex ($M)":[1.2,0.3,0.45,0.0]
})
st.table(milestones)

# download
st.download_button("⬇ CSV",df.to_csv().encode("utf‑8"),file_name="sim.csv")
