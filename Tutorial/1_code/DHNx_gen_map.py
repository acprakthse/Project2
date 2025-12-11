import matplotlib.pyplot as plt
import dhnx
import pandas as pd
import seaborn as sns
import contextily as ctx
import matplotlib.patheffects as pe
from matplotlib.collections import LineCollection
from adjustText import adjust_text


def plot_dhn_map(network,
                 results_edges=None,      # optimization results per pipe
                 offset=0.00025,
                 figsize=(20, 20),
                 dpi=50,
                 add_basemap=True,
                 debug=False):

    # --------------------------------------------------------------
    # Helper: get node coordinates from components using ID
    # --------------------------------------------------------------
    def get_node_coords(net, node_name):

        if not isinstance(node_name, str) or "-" not in node_name:
            return None, None

        comp_name, id_str = node_name.split("-", 1)
        comp = getattr(net.components, comp_name, None)
        if comp is None:
            if debug:
                print(f"[get_node_coords] No component table '{comp_name}'")
            return None, None

        if "id" not in comp.columns or "lon" not in comp.columns or "lat" not in comp.columns:
            if debug:
                print(f"[get_node_coords] Component '{comp_name}' has no id/lon/lat columns")
            return None, None

        try:
            node_id = int(id_str)
        except ValueError:
            if debug:
                print(f"[get_node_coords] Cannot parse id from '{node_name}'")
            return None, None

        row = comp.loc[comp["id"] == node_id]
        if row.empty:
            if debug:
                print(f"[get_node_coords] No row in '{comp_name}' with id={node_id}")
            return None, None

        row = row.iloc[0]
        return float(row["lon"]), float(row["lat"])

    # ------------------------------------------------------------------
    # Base map from DHNx
    # ------------------------------------------------------------------
    sns.set_theme(style="white", context="talk")
    static_map = dhnx.plotting.StaticMap(network)
    fig, ax = static_map.draw(background_map=False)

    text_objs = []   # all text for adjustText
    text_pe = [pe.withStroke(linewidth=4, foreground="white")]

    # ------------------------------------------------------------------
    # Style the network pipes & collect their segments
    # ------------------------------------------------------------------
    pipe_segments = []
    for coll in ax.collections:
        try:
            if isinstance(coll, LineCollection):
                segs = coll.get_segments()
                pipe_segments.extend(segs)

            coll.set_linewidth(10)
            coll.set_color("#F36B26")
            coll.set_alpha(0.9)
        except Exception:
            pass

    if debug:
        print(f"Found {len(pipe_segments)} pipe segments in the plot")

    # ------------------------------------------------------------------
    # Labels: Consumers
    # ------------------------------------------------------------------
    for idx, row in network.components.consumers.iterrows():
        label = "C" + str(row.get("name", idx)) + "-" + str(row["P_heat_max"]) + " kW"
        t = ax.text(
            row["lon"],
            row["lat"] + offset,
            label,
            fontsize=26,
            fontweight="bold",
            ha="center",
            va="bottom",
            color="#0177FF",
            path_effects=text_pe,
        )
        text_objs.append(t)

    # ------------------------------------------------------------------
    # Labels: Producers
    # ------------------------------------------------------------------
    for idx, row in network.components.producers.iterrows():
        label = "P" + str(row.get("name", idx))
        t = ax.text(
            row["lon"],
            row["lat"] + offset,
            label,
            fontsize=26,
            fontweight="bold",
            ha="center",
            va="bottom",
            color="#FF0000",
            path_effects=text_pe,
        )
        text_objs.append(t)

    # ------------------------------------------------------------------
    # Labels: Forks
    # ------------------------------------------------------------------
    for idx, row in network.components.forks.iterrows():
        label = "F" + str(row.get("name", idx))
        t = ax.text(
            row["lon"],
            row["lat"] + offset,
            label,
            fontsize=18,
            fontweight="bold",
            ha="center",
            va="bottom",
            color="#404B6B",
            path_effects=text_pe,
        )
        text_objs.append(t)

    # ------------------------------------------------------------------
    # Figure resolution and map extents
    # ------------------------------------------------------------------
    fig.set_size_inches(*figsize)
    fig.set_dpi(dpi)

    lon = pd.concat([
        network.components.consumers["lon"],
        network.components.producers["lon"],
        network.components.forks["lon"],
    ])
    lat = pd.concat([
        network.components.consumers["lat"],
        network.components.producers["lat"],
        network.components.forks["lat"],
    ])
    expand = 0.25
    ax.set_xlim(
        lon.min() - expand * (lon.max() - lon.min()),
        lon.max() + expand * (lon.max() - lon.min())
    )
    ax.set_ylim(
        lat.min() - expand * (lat.max() - lat.min()),
        lat.max() + expand * (lat.max() - lat.min())
    )

    # ------------------------------------------------------------------
    # Basemap
    # ------------------------------------------------------------------
    if add_basemap:
        ctx.add_basemap(ax, crs="EPSG:4326", source=ctx.providers.Esri.WorldStreetMap)

    # ------------------------------------------------------------------
    # Node scatter
    # ------------------------------------------------------------------
    ax.scatter(
        network.components.consumers["lon"],
        network.components.consumers["lat"],
        color="#0177FF",
        label="Consumers",
        zorder=6,
        s=800,
        edgecolor="k",
    )
    ax.scatter(
        network.components.producers["lon"],
        network.components.producers["lat"],
        color="#FF0000",
        label="Producers",
        zorder=6,
        s=800,
        edgecolor="k",
    )
    ax.scatter(
        network.components.forks["lon"],
        network.components.forks["lat"],
        color="#404B6B",
        label="Forks",
        zorder=6,
        s=300,
        edgecolor="k",
    )

    # ------------------------------------------------------------------
    # --- PIPE LABELS: match segments by from_node / to_node
    # ------------------------------------------------------------------
    if results_edges is not None and not results_edges.empty:
        df_pipes = results_edges.copy()

        # Only built pipes (optional)
        if 'capacity' in df_pipes.columns:
            df_pipes['capacity'] = pd.to_numeric(
                df_pipes['capacity'], errors='coerce'
            ).fillna(0.0)
            df_pipes = df_pipes[df_pipes['capacity'] > 0.001]

        # Make sure from_node / to_node are strings
        df_pipes['from_node'] = df_pipes['from_node'].astype(str)
        df_pipes['to_node']   = df_pipes['to_node'].astype(str)

        # Pipes from the network in the order they were drawn
        pipes_net = network.components.pipes[['from_node', 'to_node']].copy()
        pipes_net['from_node'] = pipes_net['from_node'].astype(str)
        pipes_net['to_node']   = pipes_net['to_node'].astype(str)
        pipes_net = pipes_net.reset_index(drop=True)

        if debug:
            print("pipes_net (from_node, to_node):")
            print(pipes_net.head())
            print("df_pipes (from_node, to_node):")
            print(df_pipes[['from_node', 'to_node']].head())

        # ---------------------------------------------------
        # BUILD NODE COORD TABLE WITH FULL NAMES:
        # 'consumers-0', 'forks-10', 'producers-3', ...
        # ---------------------------------------------------
        node_frames = []
        for comp_name in ['consumers', 'forks', 'producers']:
            comp = getattr(network.components, comp_name, None)
            if comp is None:
                continue
            if 'lon' not in comp.columns or 'lat' not in comp.columns:
                continue

            tmp = comp[['lon', 'lat']].copy()
            # build full node name: e.g. 'forks-10'
            tmp['full_name'] = [f"{comp_name}-{idx}" for idx in tmp.index]
            tmp = tmp.set_index('full_name')
            node_frames.append(tmp)

        if node_frames:
            node_coords = pd.concat(node_frames, axis=0)
        else:
            node_coords = pd.DataFrame(columns=['lon', 'lat'])

        if debug:
            print("node_coords (combined with full names):")
            print(node_coords.head())

        # ---------------------------------------------------
        # LOOP OVER PIPES AND PLACE LABELS AT FROM_NODE COORDS
        # ---------------------------------------------------
        for _, row in df_pipes.iterrows():
            fn = row['from_node']
            tn = row['to_node']

            # Find the segment index whose from/to match this pipe
            mask = (pipes_net['from_node'] == fn) & (pipes_net['to_node'] == tn)
            if not mask.any():
                if debug:
                    print(f"No segment match for pipe {fn}-{tn}")
                continue

            seg_idx = mask[mask].index[0]  # first match
            if seg_idx >= len(pipe_segments):
                if debug:
                    print(f"Segment index {seg_idx} out of range for {fn}-{tn}")
                continue

            # ---- get coordinates of FROM_NODE from node_coords ----
            if fn not in node_coords.index:
                if debug:
                    print(f"from_node {fn} not found in node_coords, skipping label")
                continue

            from_lon = float(node_coords.loc[fn, 'lon'])
            from_lat = float(node_coords.loc[fn, 'lat'])

            # place label slightly *under* the from-node
            label_lon = from_lon
            label_lat = from_lat - offset

            cap  = row.get('capacity', None)
            loss = row.get('losses', row.get('heat_loss[kW]', None))
            hp   = row.get('hp_type', '')

            # First line: from_node - to_node
            line1 = f"{fn}-{tn}"

            # Second line: hp, capacity, losses
            parts = []
            if hp not in (None, "", float("nan")):
                parts.append(str(hp))
            if cap is not None and not pd.isna(cap):
                parts.append(f"{cap:.0f} kW")
            if loss is not None and not pd.isna(loss):
                parts.append(f"losses {loss:.2f} kW")

            if not parts:
                continue

            line2 = " | ".join(parts)
            label_text = f"{line1}\n{line2}"

            label_pe = [
                pe.withStroke(linewidth=5, foreground="white")
            ]

            t = ax.text(
                label_lon,
                label_lat,
                label_text,
                fontsize=15,
                fontweight="bold",
                ha="center",
                va="top",
                color="black",
                path_effects=label_pe,
                zorder=15,
            )
            text_objs.append(t)
    elif debug:
        print("results_edges is None or empty – no pipe labels added")



    # ------------------------------------------------------------------
    # Final cosmetics
    # ------------------------------------------------------------------
    ax.grid(False)
    ax.set_xlabel("Longitude", fontsize=18)
    ax.set_ylabel("Latitude", fontsize=18)
    ax.legend(loc="lower center", ncol=3, frameon=True, fontsize=30)
    sns.despine(left=False, bottom=False)

    # Automatically adjust labels to avoid overlap
    adjust_text(
        text_objs,
        ax=ax,
        arrowprops=dict(arrowstyle="-", lw=1.5, color="gray", alpha=1),
        only_move={"text": "xy"},
    )

    plt.tight_layout()
    return fig, ax
