import json
import os
import networkx as nx
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from osint_agent import run_osint


def create_graph(data: dict, query: str, output_path: str) -> str:
    G = nx.Graph()
    G.add_node(query, label=query, node_type="center")

    category_nodes = {
        "Web": [],
        "2GIS": [],
        "Yandex Maps": [],
        "Socials": [],
    }

    web_results = data.get("web", []) or []
    for r in web_results[:6]:
        title = r.get("title", "") or ""
        short = title[:40] if title else "?"
        G.add_node(short, label=short, node_type="web")
        G.add_edge("Web", short)
        category_nodes["Web"].append(short)

    gis = data.get("2gis", {}) or {}
    if gis:
        items = []
        if gis.get("name"):
            items.append(f"2GIS: {gis['name']}")
        if gis.get("address"):
            items.append(f"Addr: {gis['address']}")
        for item in items:
            G.add_node(item, label=item, node_type="gis")
            G.add_edge("2GIS", item)
            category_nodes["2GIS"].append(item)

    yandex = data.get("yandex", {}) or {}
    if yandex:
        items = []
        if yandex.get("name"):
            items.append(f"YM: {yandex['name']}")
        if yandex.get("address"):
            items.append(f"Addr: {yandex['address']}")
        for item in items:
            G.add_node(item, label=item, node_type="yandex")
            G.add_edge("Yandex Maps", item)
            category_nodes["Yandex Maps"].append(item)

    webpage = data.get("webpage", {}) or {}
    phones = webpage.get("phones", []) or []
    for p in phones[:3]:
        G.add_node(p, label=p, node_type="phone")
        G.add_edge(query, p)

    emails = webpage.get("emails", []) or []
    for e in emails[:3]:
        G.add_node(e, label=e, node_type="email")
        G.add_edge(query, e)

    socials = data.get("socials", {}) or {}
    if isinstance(socials, dict):
        for name, url in list(socials.items())[:5]:
            label = f"{name}"
            G.add_node(label, label=label, node_type="social")
            G.add_edge("Socials", label)
            category_nodes["Socials"].append(label)

    web_socials = webpage.get("socials", {}) or {}
    if isinstance(web_socials, dict):
        for name in web_socials:
            if name not in category_nodes["Socials"]:
                G.add_node(name, label=name, node_type="social")
                G.add_edge("Socials", name)
                category_nodes["Socials"].append(name)

    for cat in category_nodes:
        G.add_node(cat, label=cat, node_type="category")
        G.add_edge(query, cat)

    plt.figure(figsize=(12, 8))

    pos = nx.spring_layout(G, k=1.5, iterations=50, seed=42)

    center_nodes = [query]
    category_list = list(category_nodes.keys())
    leaf_nodes = [n for n in G.nodes() if n not in center_nodes and n not in category_list]

    nx.draw_networkx_nodes(G, pos, nodelist=center_nodes, node_color="#e74c3c", node_size=2000, node_shape="o")
    nx.draw_networkx_nodes(G, pos, nodelist=category_list, node_color="#3498db", node_size=1500, node_shape="s")
    nx.draw_networkx_nodes(G, pos, nodelist=leaf_nodes, node_color="#2ecc71", node_size=800, node_shape="o")

    nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.5, edge_color="#888888")

    nx.draw_networkx_labels(G, pos, font_size=8, font_family="sans-serif")

    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=100, bbox_inches="tight")
    plt.close()

    return output_path


def graph_from_query(query: str, output_path: str) -> str:
    filepath = run_osint(query)
    json_path = filepath.replace(".md", "_raw.json")
    data = {}
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    return create_graph(data, query, output_path)
