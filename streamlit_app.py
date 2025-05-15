
import streamlit as st
import pandas as pd
import numpy as np

# ---------------------------
# Utility: Financial simulator
# ---------------------------
def run_financial_sim(
    years,
    hw_unit_cost,
    hw_install_cost,
    hw_sale_price,
    hw_units_year1,
    hw_unit_growth,
    arr_per_site,
    loads_per_site,
    kwh_shift,
    spread,
    share,
    mw_year1,
    mw_growth,
    order2222_fee,
    gross_margin_target,
    core_ebitda_margin,
    dev_cost_total,
    dev_amort_years,
    valuation_multiple,
):
    shipments = []
    rows = []
    hw_units = hw_units_year1
    mw = mw_year1
    dev_amort_per_year = dev_cost_total / dev_amort_years if dev_amort_years else 0

    for yr in range(1, years + 1):
        # hardware economics
        hw_revenue = hw_units * hw_sale_price
        cogs = hw_units * (hw_unit_cost + hw_install_cost)

        # SaaS revenue
        sites = mw * 250  # sites per MW (fixed for now, adjustable in GTM tab)
        saas_revenue = sites * arr_per_site

        # Arbitrage revenue
        arb_revenue = (
            sites * loads_per_site * kwh_shift * 365 * spread * share
        )

        der_revenue = saas_revenue + arb_revenue

        # Order 2222 fees (assume all shifted kWh settle)
        total_kwh_shifted = sites * loads_per_site * kwh_shift * 365
        order_fee = (total_kwh_shifted / 1000) * order2222_fee  # $/MWh

        total_revenue = hw_revenue + der_revenue
        gross_profit = total_revenue * gross_margin_target - order_fee
        core_ebitda = total_revenue * core_ebitda_margin
        reported_ebitda = core_ebitda - dev_amort_per_year
        enterprise_value = reported_ebitda * valuation_multiple

        rows.append(
            dict(
                Year=f"Year {yr}",
                HW_Units=hw_units,
                HW_Revenue=hw_revenue,
                DER_Revenue=der_revenue,
                Total_Revenue=total_revenue,
                Gross_Profit=gross_profit,
                Reported_EBITDA=reported_ebitda,
                Enterprise_Value=enterprise_value,
            )
        )

        shipments.append(hw_units)

        # grow for next period
        hw_units = int(hw_units * (1 + hw_unit_growth))
        mw = mw * (1 + mw_growth)

    df = pd.DataFrame(rows).set_index("Year")
    return df, shipments

# ---------------------------------------
# Utility: Market model for TAM/SAM/SOM
# ---------------------------------------
@st.cache_data(show_spinner=False)
def load_state_market():
    # Minimal placeholder dataset. Replace with full census & EV data for production.
    data = {
        "state": ["CA", "TX", "FL", "NY", "IL"],
        "housing_units": [14000000, 11000000, 9600000, 8300000, 5200000],
        "ev_registrations": [1400000, 290000, 250000, 215000, 95000],
    }
    return pd.DataFrame(data)

def run_market_sizing(
    df_states,
    target_states,
    panel_limited_pct,
    ev_focus_pct,
    launch_penetration,
    horizon_penetration,
    projection_years,
):
    df = df_states[df_states["state"].isin(target_states)].copy()
    # TAM
    df["TAM_units"] = df["housing_units"] * panel_limited_pct
    # SAM
    df["SAM_units"] = df["TAM_units"] * ev_focus_pct
    # Build SOM curve (linear ramp for now)
    som_curve = np.linspace(launch_penetration, horizon_penetration, projection_years)
    som_units_year = []
    for i in range(projection_years):
        share = som_curve[i]
        som = df["SAM_units"] * share
        som_units_year.append(som.sum())
    return df, som_units_year

# ============ Streamlit UI ============

st.set_page_config(page_title="Collar + Smart Sub‑Panel Business Model", layout="wide")

# Shared sidebar
st.sidebar.title("Global Parameters")

projection_years = st.sidebar.slider("Projection horizon (years)", 3, 10, 5)

st.sidebar.subheader("Hardware economics")
hw_unit_cost = st.sidebar.number_input("BOM + landing cost ($)", 400.0, step=50.0)
hw_install_cost = st.sidebar.number_input("Installer payment ($)", 250.0, step=25.0)
hw_sale_price = st.sidebar.number_input("Sale price to customer ($)", 1500.0, step=50.0)
hw_units_year1 = st.sidebar.number_input("Units shipped in Year 1", 1000, step=100)
hw_unit_growth = st.sidebar.slider("Annual unit growth rate", 0.0, 1.0, 0.4)

st.sidebar.subheader("Development & certification (OpEx)")
dev_cost_total = st.sidebar.number_input("Total dev + UL cost ($)", 2_000_000, step=100_000)
dev_amort_years = st.sidebar.slider("Amortization horizon (years)", 1, projection_years, 5)

st.sidebar.subheader("DER / SaaS")
arr_per_site = st.sidebar.number_input("ARR per site ($/yr)", 120.0, step=10.0)
loads_per_site = st.sidebar.number_input("Controllable loads per site", 4, step=1)
kwh_shift = st.sidebar.number_input("kWh shifted per load per day", 3.0, step=0.5)
spread = st.sidebar.number_input("Wholesale-retail spread ($/kWh)", 0.05, step=0.01)
share = st.sidebar.slider("Platform share of savings (%)", 0.0, 1.0, 0.4)

st.sidebar.subheader("Order 2222 aggregation")
mw_year1 = st.sidebar.number_input("MW under management, Year 1", 4.0, step=0.5)
mw_growth = st.sidebar.slider("Annual MW growth rate", 0.0, 1.0, 0.6)
order2222_fee = st.sidebar.number_input("Market fees ($/MWh)", 1.0, step=0.5)

st.sidebar.subheader("Financial assumptions")
gross_margin_target = st.sidebar.slider("Blended gross-margin (%)", 0.0, 0.9, 0.35)
core_ebitda_margin = st.sidebar.slider("Core EBITDA margin (%)", 0.0, 0.5, 0.15)
valuation_multiple = st.sidebar.number_input("EV / EBITDA multiple", 8.0, step=0.5)

# Tabs
tab_fin, tab_gtm = st.tabs(["📈 Financial Model", "🗺️ GTM & Market Sizing"])

with tab_gtm:
    st.header("Go‑to‑Market Assumptions")
    df_states = load_state_market()
    all_states = df_states["state"].tolist()
    target_states = st.multiselect("Target launch states", all_states, default=all_states[:3])

    st.subheader("TAM → SAM filters")
    panel_limited_pct = st.slider("% homes with ≤100 A service", 0.0, 1.0, 0.4)
    ev_focus_pct = st.slider("% of TAM in EV‑ready areas", 0.0, 1.0, 0.5)

    st.subheader("SOM penetration")
    launch_penetration = st.number_input("Year‑1 penetration of SAM (%)", 0.0, 100.0, 0.5) / 100
    horizon_penetration = st.number_input(f"Target SAM share in Year {projection_years} (%)", 0.0, 100.0, 5.0) / 100

    # Market sizing calc
    df_market, som_units_year = run_market_sizing(
        df_states,
        target_states,
        panel_limited_pct,
        ev_focus_pct,
        launch_penetration,
        horizon_penetration,
        projection_years,
    )

    st.markdown("#### TAM / SAM snapshot")
    st.dataframe(
        df_market[["state", "housing_units", "TAM_units", "SAM_units"]]
        .set_index("state")
        .style.format("{:,.0f}")
    )

    st.markdown("#### SOM curve vs shipment plan")
    st.bar_chart(pd.DataFrame({"SOM_units": som_units_year}))

    som_csv = pd.DataFrame({"Year": [f"Year {i+1}" for i in range(projection_years)], "SOM_units": som_units_year}).to_csv(
        index=False
    )
    st.download_button("Download SOM CSV", som_csv, file_name="som_curve.csv", mime="text/csv")

with tab_fin:
    st.header("Financial Projection")

    # Financial simulation
    df_fin, shipments = run_financial_sim(
        projection_years,
        hw_unit_cost,
        hw_install_cost,
        hw_sale_price,
        hw_units_year1,
        hw_unit_growth,
        arr_per_site,
        loads_per_site,
        kwh_shift,
        spread,
        share,
        mw_year1,
        mw_growth,
        order2222_fee,
        gross_margin_target,
        core_ebitda_margin,
        dev_cost_total,
        dev_amort_years,
        valuation_multiple,
    )

    st.subheader("P&L (annual)")
    st.dataframe(df_fin.style.format("${:,.0f}"))

    # Charts
    col1, col2 = st.columns(2)
    with col1:
        st.bar_chart(df_fin["Total_Revenue"])
    with col2:
        st.line_chart(df_fin["Enterprise_Value"])

    # Check demand vs units
    if "som_units_year" in locals():
        demand_flag = any(s > som for s, som in zip(shipments, som_units_year))
        if demand_flag:
            st.error(
                "⚠️ Shipments exceed obtainable SOM in at least one forecast year. "
                "Adjust GTM assumptions or reduce hardware growth."
            )

    csv_fin = df_fin.to_csv().encode("utf-8")
    st.download_button(
        "Download financials CSV",
        csv_fin,
        file_name="financial_projection.csv",
        mime="text/csv",
    )

st.caption("Version 0.1 • Adjust inputs in the sidebar and GTM tab, results update instantly.")
