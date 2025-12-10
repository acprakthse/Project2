import matplotlib.pyplot as plt
import dhnx
import pandas as pd
import seaborn as sns
import contextily as ctx

def plot_dhn_map(network,
                 offset=0.00025,
                 figsize=(20, 20),
                 dpi=50,
                 add_basemap=True):

    sns.set_theme(style="white", context="talk")
    static_map = dhnx.plotting.StaticMap(network)
    fig, ax = static_map.draw(background_map=False)

    # --- Network pipes
    for coll in ax.collections:
        try:
            coll.set_linewidth(10)
            coll.set_color("#F36B26")
            coll.set_alpha(0.9)
        except Exception:
            pass

    # --- Labels outside circles
    for idx, row in network.components.consumers.iterrows():
        label = "C" + str(row.get("name", idx))
        ax.text(row['lon'], row['lat'] + offset, label,
                fontsize=30, fontweight='bold',
                ha='center', va='bottom', color="#0177FF")

    for idx, row in network.components.producers.iterrows():
        label = "P" + str(row.get("name", idx))
        ax.text(row['lon'], row['lat'] + offset, label,
                fontsize=30, fontweight='bold',
                ha='center', va='bottom', color="#FF0000")

    for idx, row in network.components.forks.iterrows():
        label = "F" + str(row.get("name", idx))
        ax.text(row['lon'], row['lat'] + offset, label,
                fontsize=26, fontweight='bold',
                ha='center', va='bottom', color="#404B6B")

    # --- High resolution
    fig.set_size_inches(*figsize)
    fig.set_dpi(dpi)

    # --- Bounds
    lon = pd.concat([
        network.components.consumers['lon'],
        network.components.producers['lon'],
        network.components.forks['lon'],
    ])
    lat = pd.concat([
        network.components.consumers['lat'],
        network.components.producers['lat'],
        network.components.forks['lat'],
    ])
    expand = 0.25
    ax.set_xlim(lon.min() - expand*(lon.max()-lon.min()),
                lon.max() + expand*(lon.max()-lon.min()))
    ax.set_ylim(lat.min() - expand*(lat.max()-lat.min()),
                lat.max() + expand*(lat.max()-lat.min()))

    # --- Basemap
    if add_basemap:
        ctx.add_basemap(ax, crs="EPSG:4326", source=ctx.providers.Esri.WorldStreetMap)

    # --- Nodes
    ax.scatter(network.components.consumers['lon'], network.components.consumers['lat'],
               color="#0177FF", label='Consumers', zorder=6, s=800, edgecolor='k')
    ax.scatter(network.components.producers['lon'], network.components.producers['lat'],
               color="#FF0000", label='Producers', zorder=6, s=800, edgecolor='k')
    ax.scatter(network.components.forks['lon'], network.components.forks['lat'],
               color="#404B6B", label='Forks', zorder=6, s=800, edgecolor='k')

    ax.grid(False)
    ax.set_xlabel("Longitude", fontsize=18)
    ax.set_ylabel("Latitude", fontsize=18)
    ax.legend(loc='lower center', ncol=3, frameon=True, fontsize=30)
    sns.despine(left=False, bottom=False)

    plt.tight_layout()
    return fig, ax
