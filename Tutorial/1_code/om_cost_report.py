import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib import cm
from adjustText import adjust_text
from oemof.solph import views


def _multiply_flow_price(flow_series: pd.Series, price, dt: float = 1.0) -> float:
    """Multiply flow series by price (scalar or Series) with index alignment."""
    flow = flow_series.dropna()

    # Scalar
    if np.isscalar(price):
        return float((flow.to_numpy() * dt * float(price)).sum())

    # Series with datetime index -> align
    if isinstance(price, pd.Series):
        common = flow.index.intersection(price.index)
        if len(common) > 0:
            return float((flow.loc[common].to_numpy() * dt * price.loc[common].to_numpy()).sum())

        # fallback: trim
        n = min(len(flow), len(price))
        return float((flow.to_numpy()[:n] * dt * price.to_numpy()[:n]).sum())

    # array-like -> trim
    p = np.asarray(price).ravel()
    n = min(len(flow), len(p))
    return float((flow.to_numpy()[:n] * dt * p[:n]).sum())


def build_cost_df_and_plot_pie(
    results,
    data: pd.DataFrame,
    *,
    # capacities
    capacity_gas_heat: float,
    capacity_biomass_chp: float,
    capacity_wte_chp: float,
    max_heat_hp: float,
    # VOM rates
    vom_el_wte: float,
    vom_th_wte: float,
    vom_heat: float,
    vom_el_bio: float,
    vom_th_bio: float,
    vom_hp_th: float,
    vom_solar_th: float,
    # revenue (already computed outside, pass in)
    el_revenue: float,
    dt: float = 1.0,
    # outputs
    save_csv=None,
    save_fig=None,
    show_plot: bool = True,
    figsize=(9, 8),
    title="Total System Cost Breakdown (excluding electricity revenue)",
):
    """
    Build O&M / fuel / startup cost breakdown and plot pie chart.
    Returns:
        cost_df (pd.Series), cost_df_pie (pd.Series)
    """

    # -------------------------
    # BUS VIEWS
    # -------------------------
    waste_bus_view = views.node(results, "waste_bus")["sequences"].copy()
    gas_bus_view   = views.node(results, "gas_bus")["sequences"].copy()
    bio_bus_view   = views.node(results, "biomass_bus")["sequences"].copy()
    el_bus_view    = views.node(results, "electrical_bus")["sequences"].copy()
    th_bus_view    = views.node(results, "thermal_bus")["sequences"].copy()

    # -------------------------
    # FUEL COSTS
    # -------------------------
    fuel_costs = {}

    fuel_costs["Waste fuel"] = _multiply_flow_price(
        waste_bus_view[(("waste_bus", "waste_to_energy"), "flow")],
        data["waste_Euro_Per_MWh"],
        dt=dt
    )

    fuel_costs["Gas fuel"] = _multiply_flow_price(
        gas_bus_view[(("gas_bus", "heat_gas"), "flow")],
        data["gas_price_Euro_Per_MWh"],
        dt=dt
    )

    fuel_costs["Biomass fuel"] = _multiply_flow_price(
        bio_bus_view[(("biomass_bus", "chp_biomass"), "flow")],
        data["biomass_Euro_Per_MWh"],
        dt=dt
    )

    fuel_costs["Electricity for heat pump"] = _multiply_flow_price(
        el_bus_view[(("electrical_bus", "heat_pump"), "flow")],
        data["electricity_price_Euro_Per_MWh"],
        dt=dt
    )

    # -------------------------
    # VOM COSTS
    # -------------------------
    vom_costs = {}

    vom_costs["WtE CHP O&M"] = float(
        (el_bus_view[(("waste_to_energy", "electrical_bus"), "flow")].dropna().to_numpy() * dt * vom_el_wte).sum()
        + (th_bus_view[(("waste_to_energy", "thermal_bus"), "flow")].dropna().to_numpy() * dt * vom_th_wte).sum()
    )

    vom_costs["Gas boiler O&M"] = float(
        (th_bus_view[(("heat_gas", "thermal_bus"), "flow")].dropna().to_numpy() * dt * vom_heat).sum()
    )

    vom_costs["Biomass CHP O&M"] = float(
        (el_bus_view[(("chp_biomass", "electrical_bus"), "flow")].dropna().to_numpy() * dt * vom_el_bio).sum()
        + (th_bus_view[(("chp_biomass", "thermal_bus"), "flow")].dropna().to_numpy() * dt * vom_th_bio).sum()
    )

    vom_costs["Heat Pump O&M"] = float(
        (th_bus_view[(("heat_pump", "thermal_bus"), "flow")].dropna().to_numpy() * dt * vom_hp_th).sum()
    )

    vom_costs["Solar Collector O&M"] = float(
        (th_bus_view[(("solar_thermal", "thermal_bus"), "flow")].dropna().to_numpy() * dt * vom_solar_th).sum()
    )

    # -------------------------
    # STARTUP COSTS (use 'startup' column directly)
    # Startup is 1 at the hour of a start, 0 otherwise.
    # We weight by the fuel/energy price at that hour and multiply by installed capacity.
    # -------------------------
    startup_costs = {}

    # Gas boiler startup on thermal output edge
    startup_costs["Gas boiler startup"] = float(
        (
            th_bus_view[(("heat_gas", "thermal_bus"), "startup")].dropna().to_numpy()
            * data["gas_price_Euro_Per_MWh"].to_numpy()[:len(th_bus_view[(("heat_gas", "thermal_bus"), "startup")].dropna())]
        ).sum()
        * capacity_gas_heat
    )

    # Biomass CHP startup on biomass input edge
    startup_costs["Biomass CHP startup"] = float(
        (
            bio_bus_view[(("biomass_bus", "chp_biomass"), "startup")].dropna().to_numpy()
            * data["biomass_Euro_Per_MWh"].to_numpy()[:len(bio_bus_view[(("biomass_bus", "chp_biomass"), "startup")].dropna())]
        ).sum()
        * capacity_biomass_chp
    )

    # WtE CHP startup on waste input edge
    startup_costs["WtE CHP startup"] = float(
        (
            waste_bus_view[(("waste_bus", "waste_to_energy"), "startup")].dropna().to_numpy()
            * data["waste_Euro_Per_MWh"].to_numpy()[:len(waste_bus_view[(("waste_bus", "waste_to_energy"), "startup")].dropna())]
        ).sum()
        * capacity_wte_chp
    )

    # Heat pump startup on thermal output edge
    startup_costs["Heat Pump startup"] = float(
        (
            th_bus_view[(("heat_pump", "thermal_bus"), "startup")].dropna().to_numpy()
            * data["electricity_price_Euro_Per_MWh"].to_numpy()[:len(th_bus_view[(("heat_pump", "thermal_bus"), "startup")].dropna())]
        ).sum()
        * max_heat_hp
    )

    # -------------------------
    # COMBINE COSTS
    # -------------------------
    cost_items = {
        **fuel_costs,
        **vom_costs,
        **startup_costs,
        "Electricity revenue": -float(el_revenue),
    }

    cost_df = pd.Series(cost_items, dtype="float64").sort_values(ascending=False)

    # -------------------------
    # PIE DATA (exclude revenue)
    # -------------------------
    cost_df_pie = cost_df.drop(labels=["Electricity revenue"], errors="ignore")
    cost_df_pie = cost_df_pie.replace([np.inf, -np.inf], np.nan).dropna()
    cost_df_pie = cost_df_pie[cost_df_pie > 0].sort_values(ascending=False)

    if cost_df_pie.empty:
        raise ValueError("Pie chart has no positive cost components to plot (cost_df_pie is empty).")

    # -------------------------
    # PLOT PIE
    # -------------------------
    n = len(cost_df_pie)
    colors = cm.Oranges(np.linspace(0.35, 0.85, n))

    fig = plt.figure(figsize=figsize)
    wedges, texts, autotexts = plt.pie(
        cost_df_pie.values,
        colors=colors,
        autopct=lambda p: f"{p:.2f}%",
        startangle=90,
        pctdistance=0.75,
    )

    for t in autotexts:
        t.set_path_effects([pe.withStroke(linewidth=5, foreground="white")])

    plt.legend(
        wedges,
        cost_df_pie.index,
        title="Cost components",
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=False,
    )

    adjust_text(
        autotexts,
        only_move={"text": "y"},
        autoalign="y",
        force_text=0.6,
    )

    plt.title(title)
    plt.tight_layout()

    if save_fig is not None:
        plt.savefig(save_fig, dpi=300, bbox_inches="tight")

    if show_plot:
        plt.show()
    else:
        plt.close(fig)

    # -------------------------
    # SAVE CSV
    # -------------------------
    if save_csv is not None:
        out = cost_df.reset_index()
        out.columns = ["Cost component", "Annual cost [€]"]
        out.to_csv(save_csv, index=False)

    return cost_df, cost_df_pie
