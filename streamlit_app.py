
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="HEMS + VPP Simulator (Pre‑loaded ISO Prices)", layout="wide")
st.title("📊 HEMS + VPP Business Model Simulator")

############################################################
# Helper texts (ELI5 tool‑tips)
############################################################
HELP = {
    "bom": "ELI5: Cost to build & ship ONE retrofit kit (before profit).",
    "install": "ELI5: Cash we pay the electrician/channel partner for each install.",
    "asp": "ELI5: Sticker price the homeowner pays for the hardware kit.",
    "units_y1": "ELI5: Kits we expect to ship in the first forecast year.",
    "unit_cagr": "ELI5: Annual shipment growth. 0.6 means +60 % per year.",
    "dev_total": "ELI5: Up‑front R&D + UL/FCC/app costs before selling units.",
    "dev_years": "ELI5: Years over which we amortize that dev spend.",
    "loads": "ELI5: Big controllable loads per house (EV, heat‑pump, dryer, etc.).",
    "kwh": "ELI5: kWh per load we can shift off‑peak each day.",
    "spread": "ELI5: Average $ difference between off‑peak and peak electricity.",
    "share": "ELI5: Our share of the savings from shifting load (0.4 ⇒ we keep 40 %).",
    "mw_y1": "ELI5: Flexible‑load capacity (MW) we aggregate in year 1.",
    "mw_cagr": "ELI5: Annual growth of that MW portfolio.",
    "gm": "ELI5: % of revenue left after hardware COGS.",
    "ebitda": "ELI5: EBITDA margin *before* dev‑cost amortization.",
    "ev_mult": "ELI5: How many × Revenue investors might pay.",
}

############################################################
# Pre‑loaded ISO capacity price ($ per kW‑year)
############################################################
ISO_CAP_PRICE = {
    "CAISO": 55,     # mid‑case Resource Adequacy implied
    "ISO‑NE": 40,    # FCA18 strip
    "NYISO": 36,     # SCR avg
    "PJM": 100,      # 2025/26 BRA RTO
    "MISO": 35       # historical DR capacity equivalent
}

ISO_EVENT_PRICE = {
    "CAISO": 150, "ISO‑NE": 125, "NYISO": 100, "PJM": 150, "MISO": 100
}  # $/MWh actually curtailed (rare events)

############################################################
# Financial simulator
############################################################
def run_financial(years, asp, units_y1, unit_cagr,
                  loads_site, kwh_shift, share_savings,
                  mw_y1, mw_cagr,
                  iso_price_kwyr, iso_event_price,
                  peak_hours, gross_margin, ebitda_margin,
                  dev_total, dev_years, ev_mult):

    amort = dev_total / dev_years if dev_years else 0
    results = []
    units = units_y1
    mw = mw_y1
    for yr in range(years):
        hw_rev = units * asp

        # capacity revenue
        vpp_cap = mw * 1000 * iso_price_kwyr  # kW * $/kW‑yr
        # event revenue (energy)
        event_mwh = mw * peak_hours
        vpp_evt = event_mwh * iso_event_price
        vpp_rev = vpp_cap + vpp_evt

        total_rev = hw_rev + vpp_rev
        gp = total_rev * gross_margin
        ebitda = total_rev * ebitda_margin - amort
        ev = total_rev * ev_mult

        results.append({
            "Year": f"Year {yr+1}",
            "Units": units,
            "Hardware Revenue": hw_rev,
            "VPP Revenue": vpp_rev,
            "Total Revenue": total_rev,
            "EBITDA": ebitda,
            "Enterprise Value": ev
        })

        units = int(units * (1 + unit_cagr))
        mw *= (1 + mw_cagr)

    return pd.DataFrame(results).set_index("Year")

############################################################
# Sidebar UI
############################################################
side = st.sidebar
years = side.slider("Projection years", 3, 10, 5)
iso_choice = side.selectbox("ISO Region", list(ISO_CAP_PRICE.keys()))

side.subheader("Hardware")
asp = side.number_input("Sale price to customer ($)", 1500.0, step=50.0, help=HELP["asp"])
units_y1 = side.number_input("Units shipped in Year 1", 1000, step=100, help=HELP["units_y1"])
unit_cagr = side.slider("Annual unit growth rate", 0.0, 1.0, 0.4, help=HELP["unit_cagr"])

side.subheader("VPP / DCR Assumptions")
loads_site = side.number_input("Controllable loads per site", 3, step=1, help=HELP["loads"])
kwh_shift = side.number_input("kWh shifted per load/day", 3.0, step=0.5, help=HELP["kwh"])
share_savings = side.slider("Your share of savings", 0.0, 1.0, 0.4, help=HELP["share"])
peak_hours = side.number_input("Event hours/year", 10, step=5)

mw_y1 = side.number_input("MW under management – Year 1", 1.0, step=0.5, help=HELP["mw_y1"])
mw_cagr = side.slider("Annual MW growth", 0.0, 1.0, 0.6, help=HELP["mw_cagr"])

side.subheader("Financial")
dev_total = side.number_input("Total dev cost ($)", 2_000_000, step=100_000, help=HELP["dev_total"])
dev_years = side.slider("Amortization years", 1, years, 5, help=HELP["dev_years"])
gross_margin = side.slider("Blended gross‑margin", 0.0, 0.9, 0.35, help=HELP["gm"])
ebitda_margin = side.slider("EBITDA margin", 0.0, 0.5, 0.15, help=HELP["ebitda"])
ev_mult = side.number_input("EV / Revenue multiple", 3.0, step=0.5, help=HELP["ev_mult"])

# Run simulation
df = run_financial(
    years, asp, units_y1, unit_cagr,
    loads_site, kwh_shift, share_savings,
    mw_y1, mw_cagr,
    ISO_CAP_PRICE[iso_choice], ISO_EVENT_PRICE[iso_choice],
    peak_hours, gross_margin, ebitda_margin,
    dev_total, dev_years, ev_mult
)

############################################################
# Outputs
############################################################
st.header(f"ISO region: {iso_choice}  —  Capacity price = ${ISO_CAP_PRICE[iso_choice]:.0f}/kW·yr")
st.dataframe(df.style.format("${:,.0f}"))
st.bar_chart(df[["Hardware Revenue", "VPP Revenue"]])
st.line_chart(df["Enterprise Value"])

# Download link
csv = df.to_csv(index=True).encode("utf-8")
st.download_button("💾 Download results (CSV)", csv, file_name="hems_vpp_simulation.csv", mime="text/csv")
