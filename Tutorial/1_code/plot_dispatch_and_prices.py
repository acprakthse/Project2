import matplotlib.pyplot as plt
from oemof.solph import views


def plot_dispatch_and_prices(
    results,
    data,
    start,
    end,
    figsize=(16, 11),
):
    """
    Plot combined dispatch and price figure:
      1) Thermal supply + demand
      2) Energy prices
      3) Electricity production (excluding grid)

    Parameters
    ----------
    results : dict
        oemof-solph results dictionary
    data : pd.DataFrame
        Time series with energy prices
    start, end : str or pd.Timestamp
        Time window for plotting
    figsize : tuple
        Figure size
    """

    # ---------------------------
    # THERMAL BUS
    # ---------------------------
    thermal_bus_view = views.node(results, "thermal_bus")
    seq_th = thermal_bus_view["sequences"].iloc[:-1].loc[start:end]

    col_wte      = (("waste_to_energy", "thermal_bus"), "flow")
    col_biomass  = (("chp_biomass", "thermal_bus"), "flow")
    col_gas      = (("heat_gas", "thermal_bus"), "flow")
    col_hp       = (("heat_pump", "thermal_bus"), "flow")
    col_solar_th = (("solar_thermal", "thermal_bus"), "flow")

    components = {
        "wte":      {"series": seq_th.get(col_wte),      "label": "Waste-to-Energy", "color": "#008DDF"},
        "biomass":  {"series": seq_th.get(col_biomass),  "label": "Biomass CHP",     "color": "#8AB020"},
        "hp":       {"series": seq_th.get(col_hp),       "label": "Heat Pump",       "color": "#F01000"},
        "gas":      {"series": seq_th.get(col_gas),      "label": "Gas Heat Unit",   "color": "#C87E00"},
        "solar":    {"series": seq_th.get(col_solar_th), "label": "Solar Thermal",   "color": "#C500C8"},
    }

    stack_order = ["wte", "biomass", "hp", "gas", "solar"]

    th_series, th_labels, th_colors = [], [], []
    for k in stack_order:
        s = components[k]["series"]
        if s is not None:
            th_series.append(s)
            th_labels.append(components[k]["label"])
            th_colors.append(components[k]["color"])

    # ---------------------------
    # ELECTRICITY BUS
    # ---------------------------
    el_bus_view = views.node(results, "electrical_bus")
    seq_el = el_bus_view["sequences"].iloc[:-1].loc[start:end]

    exclude_nodes = {"electricity_grid", "grid", "grid_import", "grid_export"}

    prod_cols = [
        c for c in seq_el.columns
        if isinstance(c, tuple)
        and isinstance(c[0], tuple)
        and c[0][1] == "electrical_bus"
        and c[1] == "flow"
        and c[0][0] not in exclude_nodes
    ]

    color_map = {
        "chp_biomass": "#8AB020",
        "waste_to_energy": "#008DDF",
    }

    el_series, el_labels, el_colors = [], [], []
    for c in prod_cols:
        unit = c[0][0]
        el_series.append(seq_el[c])
        el_labels.append(unit)
        el_colors.append(color_map.get(unit, "#999999"))

    # ---------------------------
    # PRICE DATA
    # ---------------------------
    prices = data.loc[start:end, [
        "electricity_price_Euro_Per_MWh",
        "gas_price_Euro_Per_MWh",
        "biomass_Euro_Per_MWh",
        "waste_Euro_Per_MWh",
    ]]

    # ---------------------------
    # COMBINED PLOT (3 ROWS)
    # ---------------------------
    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1, figsize=figsize, sharex=True,
        gridspec_kw={"height_ratios": [2.3, 1.0, 1.5]}
    )

    # --- (1) Thermal supply + demand
    ax1.stackplot(
        seq_th.index,
        *th_series,
        labels=th_labels,
        colors=th_colors,
        alpha=0.7,
    )

    ax1.plot(
        seq_th.index,
        seq_th[(("thermal_bus", "thermal_demand"), "flow")],
        label="Thermal Demand",
        color="#262630",
        linestyle="--",
        linewidth=1.0,
    )

    ax1.set_ylabel("Heat Power [MW]")
    ax1.set_title("Thermal Supply, Electricity Prices, and Power Production")
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="lower left", ncol=2)

    # --- (2) Energy prices
    ax2.plot(prices.index, prices["electricity_price_Euro_Per_MWh"],
             label="Electricity", color="#F01000", linewidth=2.0)

    ax2.plot(prices.index, prices["gas_price_Euro_Per_MWh"],
             label="Gas", color="#C87E00", linewidth=2.0)

    ax2.plot(prices.index, prices["biomass_Euro_Per_MWh"],
             label="Biomass", color="#8AB020", linewidth=2.0)

    ax2.plot(prices.index, prices["waste_Euro_Per_MWh"],
             label="Waste", color="#008DDF", linewidth=2.0)

    ax2.set_ylabel("Price [€/MWh]")
    ax2.set_ylim(0, 100)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="upper left", ncol=2)

    # --- (3) Electricity production
    ax3.stackplot(
        seq_el.index,
        *el_series,
        labels=el_labels,
        colors=el_colors,
        alpha=0.75,
    )

    ax3.set_ylabel("Electric Power [MW]")
    ax3.set_xlabel("Time")
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc="upper left")

    plt.tight_layout()
    plt.show()

    # Debug info
    print("Electricity producers plotted:", el_labels)
