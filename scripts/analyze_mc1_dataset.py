#!/usr/bin/env python3
"""
Zero-dependency dataset profiler for VAST Challenge 2025 MC1.

It reads MC1_graph.json, computes a compact summary, and exports simple SVG
charts that are easy to reuse in slides or docs.

Usage:
    python scripts/analyze_mc1_dataset.py
    python scripts/analyze_mc1_dataset.py --input ../MC1_release/MC1_graph.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict, deque
from pathlib import Path
from statistics import mean
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "MC1_release" / "MC1_graph.json"
DEFAULT_OUTPUT = ROOT / "docs" / "phase1-assets"
PALETTE = {
    "bg": "#f4efe6",
    "card": "#fffaf3",
    "ink": "#1e2a33",
    "muted": "#6a7c89",
    "grid": "#d9e1e7",
    "line": "#b8c4ce",
    "teal": "#1f7a8c",
    "sea": "#3ba7a0",
    "coral": "#d97b4d",
    "gold": "#d9a441",
    "slate": "#5c6b73",
}


def load_graph(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def year_from_date(value: str | None) -> int | None:
    if not value:
        return None
    text = str(value).strip()
    if len(text) < 4 or not text[:4].isdigit():
        return None
    return int(text[:4])


def build_adjacency(links: list[dict]) -> dict[int, list[int]]:
    adj: dict[int, list[int]] = defaultdict(list)
    for link in links:
        source = link["source"]
        target = link["target"]
        adj[source].append(target)
        adj[target].append(source)
    return adj


def connected_components(node_ids: Iterable[int], adj: dict[int, list[int]]) -> list[int]:
    seen: set[int] = set()
    sizes: list[int] = []
    for node_id in node_ids:
        if node_id in seen:
            continue
        queue: deque[int] = deque([node_id])
        seen.add(node_id)
        size = 0
        while queue:
            current = queue.popleft()
            size += 1
            for neighbor in adj.get(current, []):
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def top_degree_nodes(nodes: list[dict], links: list[dict], limit: int = 10) -> list[dict]:
    degree = Counter()
    for link in links:
        degree[link["source"]] += 1
        degree[link["target"]] += 1
    node_by_id = {node["id"]: node for node in nodes}
    ranked = []
    for node_id, value in degree.most_common(limit):
        node = node_by_id[node_id]
        ranked.append(
            {
                "id": node_id,
                "degree": value,
                "type": node["Node Type"],
                "label": node.get("stage_name") or node.get("name"),
            }
        )
    return ranked


def summarize(data: dict) -> dict:
    nodes = data["nodes"]
    links = data["links"]

    node_types = Counter(node["Node Type"] for node in nodes)
    edge_types = Counter(link["Edge Type"] for link in links)
    node_ids = [node["id"] for node in nodes]
    adj = build_adjacency(links)
    component_sizes = connected_components(node_ids, adj)

    song_years = Counter()
    song_genres = Counter()
    oceanus_folk_years = Counter()
    oceanus_folk_genres = Counter()
    album_years = Counter()
    sailor_shift_relations = Counter()
    notoriety_gaps = []

    sailor_shift_id = None
    for node in nodes:
        if node["Node Type"] == "Person" and node.get("name") == "Sailor Shift":
            sailor_shift_id = node["id"]
            break

    for node in nodes:
        node_type = node["Node Type"]
        genre = node.get("genre")
        release_year = year_from_date(node.get("release_date"))
        notoriety_year = year_from_date(node.get("notoriety_date"))

        if release_year is not None and notoriety_year is not None:
            notoriety_gaps.append(notoriety_year - release_year)

        if node_type == "Song":
            if release_year is not None:
                song_years[release_year] += 1
            if genre:
                song_genres[genre] += 1
            if genre == "Oceanus Folk":
                oceanus_folk_genres[genre] += 1
                if release_year is not None:
                    oceanus_folk_years[release_year] += 1

        if node_type == "Album" and release_year is not None:
            album_years[release_year] += 1

    if sailor_shift_id is not None:
        for link in links:
            if link["source"] == sailor_shift_id or link["target"] == sailor_shift_id:
                sailor_shift_relations[link["Edge Type"]] += 1

    return {
        "node_count": len(nodes),
        "link_count": len(links),
        "node_type_distribution": dict(node_types.most_common()),
        "edge_type_distribution": dict(edge_types.most_common()),
        "connected_components": {
            "count": len(component_sizes),
            "largest_sizes": component_sizes[:10],
        },
        "top_degree_nodes": top_degree_nodes(nodes, links, limit=12),
        "song_release_years": dict(sorted(song_years.items())),
        "album_release_years": dict(sorted(album_years.items())),
        "top_song_genres": dict(song_genres.most_common(10)),
        "oceanus_folk_song_count": song_genres.get("Oceanus Folk", 0),
        "oceanus_folk_release_years": dict(sorted(oceanus_folk_years.items())),
        "sailor_shift_relation_profile": dict(sailor_shift_relations.most_common()),
        "metadata_highlights": {
            "persons_with_stage_name": sum(
                1
                for node in nodes
                if node["Node Type"] == "Person" and bool(node.get("stage_name"))
            ),
            "songs_with_notoriety_date": sum(
                1
                for node in nodes
                if node["Node Type"] == "Song" and bool(node.get("notoriety_date"))
            ),
            "albums_with_notoriety_date": sum(
                1
                for node in nodes
                if node["Node Type"] == "Album" and bool(node.get("notoriety_date"))
            ),
            "average_notoriety_gap_years": round(mean(notoriety_gaps), 2)
            if notoriety_gaps
            else None,
        },
    }


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def save_markdown(path: Path, summary: dict) -> None:
    lines = [
        "# MC1 Dataset Summary",
        "",
        "## Core Scale",
        f"- Nodes: {summary['node_count']}",
        f"- Links: {summary['link_count']}",
        f"- Connected components: {summary['connected_components']['count']}",
        f"- Largest component sizes: {summary['connected_components']['largest_sizes'][:5]}",
        "",
        "## Node Types",
    ]
    for key, value in summary["node_type_distribution"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Edge Types"])
    for key, value in list(summary["edge_type_distribution"].items())[:10]:
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Top Song Genres"])
    for key, value in summary["top_song_genres"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "## Metadata Highlights",
            f"- Persons with stage names: {summary['metadata_highlights']['persons_with_stage_name']}",
            f"- Songs with notoriety dates: {summary['metadata_highlights']['songs_with_notoriety_date']}",
            f"- Albums with notoriety dates: {summary['metadata_highlights']['albums_with_notoriety_date']}",
            f"- Average notoriety gap (years): {summary['metadata_highlights']['average_notoriety_gap_years']}",
            "",
            "## Sailor Shift Ego Profile",
        ]
    )
    for key, value in summary["sailor_shift_relation_profile"].items():
        lines.append(f"- {key}: {value}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _svg_text(x: float, y: float, text: str, size: int = 12, anchor: str = "start") -> str:
    safe = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    return (
        f'<text x="{x}" y="{y}" font-family="Avenir Next, Segoe UI, Arial, sans-serif" '
        f'font-size="{size}" fill="{PALETTE["ink"]}" text-anchor="{anchor}">{safe}</text>'
    )


def _svg_header(title: str, subtitle: str, width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<defs>",
        '<linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">',
        f'<stop offset="0%" stop-color="{PALETTE["bg"]}" />',
        f'<stop offset="100%" stop-color="#eef7f7" />',
        "</linearGradient>",
        '<filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">',
        '<feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#9db3b7" flood-opacity="0.18"/>',
        "</filter>",
        "</defs>",
        f'<rect width="{width}" height="{height}" fill="url(#bgGrad)"/>',
        f'<circle cx="{width - 80}" cy="70" r="120" fill="#e6f3f0" opacity="0.85"/>',
        f'<circle cx="70" cy="{height - 50}" r="110" fill="#f6e6d7" opacity="0.85"/>',
        _svg_text(28, 36, title, size=26),
        f'<text x="28" y="60" font-family="Avenir Next, Segoe UI, Arial, sans-serif" font-size="12" fill="{PALETTE["muted"]}">{subtitle}</text>',
    ]


def _card(x: float, y: float, width: float, height: float, title: str) -> list[str]:
    return [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="18" fill="{PALETTE["card"]}" filter="url(#shadow)"/>',
        f'<text x="{x + 18}" y="{y + 28}" font-family="Avenir Next, Segoe UI, Arial, sans-serif" font-size="15" font-weight="600" fill="{PALETTE["ink"]}">{title}</text>',
    ]


def write_horizontal_bar_chart(
    path: Path,
    title: str,
    items: list[tuple[str, int]],
    width: int = 960,
    row_height: int = 34,
    color: str = None,
    subtitle: str = "Top categories in the MC1 music graph",
) -> None:
    color = color or PALETTE["teal"]
    card_x = 20
    card_y = 78
    card_w = width - 40
    left = card_x + 170
    top = card_y + 54
    bar_area = card_w - 230
    height = card_y + len(items) * row_height + 70
    max_value = max((value for _, value in items), default=1)
    parts = _svg_header(title, subtitle, width, height)
    parts.extend(_card(card_x, card_y, card_w, height - card_y - 20, "Distribution"))
    for idx, (label, value) in enumerate(items):
        y = top + idx * row_height
        bar_width = 0 if max_value == 0 else (value / max_value) * bar_area
        parts.append(
            f'<line x1="{left}" y1="{y}" x2="{left + bar_area}" y2="{y}" stroke="{PALETTE["grid"]}" stroke-width="10" stroke-linecap="round"/>'
        )
        parts.append(
            f'<line x1="{left}" y1="{y}" x2="{left + bar_width:.1f}" y2="{y}" stroke="{color}" stroke-width="10" stroke-linecap="round"/>'
        )
        parts.append(_svg_text(left - 14, y + 4, label, size=12, anchor="end"))
        parts.append(
            f'<text x="{left + bar_width + 10:.1f}" y="{y + 4}" font-family="Avenir Next, Segoe UI, Arial, sans-serif" font-size="12" font-weight="600" fill="{PALETTE["slate"]}">{value}</text>'
        )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def write_year_bar_chart(
    path: Path,
    title: str,
    year_counts: dict[int, int],
    width: int = 1100,
    height: int = 420,
) -> None:
    left = 70
    right = 34
    top = 124
    bottom = 56
    plot_w = width - left - right
    plot_h = height - top - bottom
    years = sorted(year_counts)
    values = [year_counts[year] for year in years]
    max_value = max(values, default=1)
    bar_w = plot_w / max(len(years), 1)
    parts = _svg_header(title, "Temporal distribution of song releases", width, height)
    parts.extend(_card(20, 78, width - 40, height - 98, "Release Timeline"))
    parts.append(
        f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" stroke="{PALETTE["line"]}" />'
    )
    parts.append(
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" stroke="{PALETTE["line"]}" />'
    )

    for tick in range(5):
        value = round(max_value * tick / 4)
        y = top + plot_h - (0 if max_value == 0 else value / max_value * plot_h)
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" stroke="{PALETTE["grid"]}" />'
        )
        parts.append(_svg_text(left - 8, y + 4, str(value), size=11, anchor="end"))

    for index, year in enumerate(years):
        value = year_counts[year]
        x = left + index * bar_w + 1
        bar_height = 0 if max_value == 0 else value / max_value * plot_h
        y = top + plot_h - bar_height
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(bar_w - 2, 1):.1f}" height="{bar_height:.1f}" rx="2" fill="{PALETTE["coral"]}" />'
        )
        if index % max(len(years) // 12, 1) == 0:
            parts.append(
                _svg_text(x + bar_w / 2, height - bottom + 18, str(year), size=10, anchor="middle")
            )

    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _mini_bar_chart(
    items: list[tuple[str, int]],
    x: float,
    y: float,
    width: float,
    height: float,
    color: str,
) -> list[str]:
    parts = []
    max_value = max((value for _, value in items), default=1)
    label_w = width * 0.42
    bar_left = x + label_w
    bar_w = width - label_w - 16
    row_h = height / max(len(items), 1)
    for idx, (label, value) in enumerate(items):
        cy = y + idx * row_h + row_h * 0.62
        fill_w = 0 if max_value == 0 else bar_w * value / max_value
        parts.append(
            f'<line x1="{bar_left}" y1="{cy}" x2="{bar_left + bar_w}" y2="{cy}" stroke="{PALETTE["grid"]}" stroke-width="8" stroke-linecap="round"/>'
        )
        parts.append(
            f'<line x1="{bar_left}" y1="{cy}" x2="{bar_left + fill_w:.1f}" y2="{cy}" stroke="{color}" stroke-width="8" stroke-linecap="round"/>'
        )
        parts.append(_svg_text(bar_left - 10, cy + 4, label, size=11, anchor="end"))
        parts.append(
            f'<text x="{bar_left + fill_w + 8:.1f}" y="{cy + 4}" font-family="Avenir Next, Segoe UI, Arial, sans-serif" font-size="11" font-weight="600" fill="{PALETTE["slate"]}">{value}</text>'
        )
    return parts


def _mini_year_chart(
    year_counts: dict[int, int],
    x: float,
    y: float,
    width: float,
    height: float,
    color: str,
) -> list[str]:
    parts = []
    years = sorted(year_counts)
    values = [year_counts[year] for year in years]
    max_value = max(values, default=1)
    left = x + 8
    bottom = y + height - 18
    top = y + 12
    plot_h = bottom - top
    bar_w = (width - 16) / max(len(years), 1)
    parts.append(f'<line x1="{left}" y1="{bottom}" x2="{x + width - 8}" y2="{bottom}" stroke="{PALETTE["line"]}"/>')
    for idx, year in enumerate(years):
        value = year_counts[year]
        bx = left + idx * bar_w + 0.5
        bh = 0 if max_value == 0 else plot_h * value / max_value
        by = bottom - bh
        parts.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{max(bar_w - 1, 1):.1f}" height="{bh:.1f}" rx="1.5" fill="{color}"/>'
        )
        if idx % max(len(years) // 8, 1) == 0:
            parts.append(_svg_text(bx + bar_w / 2, bottom + 14, str(year), size=9, anchor="middle"))
    return parts


def write_dashboard(path: Path, summary: dict, width: int = 1500, height: int = 980) -> None:
    parts = _svg_header(
        "MC1 Dataset Overview",
        "Heterogeneous music graph for career analysis and influence tracing",
        width,
        height,
    )
    parts.extend(_card(28, 88, width - 56, height - 116, "Phase 1 data snapshot"))

    stats = [
        ("Nodes", f"{summary['node_count']:,}"),
        ("Links", f"{summary['link_count']:,}"),
        ("Node types", str(len(summary["node_type_distribution"]))),
        ("Edge types", str(len(summary["edge_type_distribution"]))),
        ("Components", str(summary["connected_components"]["count"])),
        ("Largest CC", f"{summary['connected_components']['largest_sizes'][0]:,}"),
    ]
    stat_x = 58
    stat_y = 128
    stat_w = 210
    stat_h = 92
    gap = 18
    stat_colors = [PALETTE["teal"], PALETTE["sea"], PALETTE["gold"], PALETTE["coral"], "#7c8aa5", "#2c6e63"]
    for idx, (label, value) in enumerate(stats):
        x = stat_x + idx * (stat_w + gap)
        parts.append(
            f'<rect x="{x}" y="{stat_y}" width="{stat_w}" height="{stat_h}" rx="16" fill="#fffdf9" stroke="#ecdfcf"/>'
        )
        parts.append(
            f'<circle cx="{x + 28}" cy="{stat_y + 28}" r="9" fill="{stat_colors[idx]}"/>'
        )
        parts.append(
            f'<text x="{x + 48}" y="{stat_y + 33}" font-family="Avenir Next, Segoe UI, Arial, sans-serif" font-size="13" fill="{PALETTE["muted"]}">{label}</text>'
        )
        parts.append(
            f'<text x="{x + 22}" y="{stat_y + 68}" font-family="Avenir Next, Segoe UI, Arial, sans-serif" font-size="28" font-weight="700" fill="{PALETTE["ink"]}">{value}</text>'
        )

    panels = [
        (58, 252, 430, 290, "Node Type Distribution"),
        (514, 252, 430, 290, "Top Edge Types"),
        (970, 252, 472, 290, "Top Song Genres"),
        (58, 572, 1384, 250, "Song Release Timeline"),
    ]
    for x, y, w, h, title in panels:
        parts.extend(_card(x, y, w, h, title))

    parts.extend(
        _mini_bar_chart(
            list(summary["node_type_distribution"].items()),
            78,
            300,
            390,
            220,
            PALETTE["teal"],
        )
    )
    parts.extend(
        _mini_bar_chart(
            list(summary["edge_type_distribution"].items())[:8],
            534,
            300,
            390,
            220,
            PALETTE["coral"],
        )
    )
    parts.extend(
        _mini_bar_chart(
            list(summary["top_song_genres"].items())[:8],
            990,
            300,
            430,
            220,
            PALETTE["gold"],
        )
    )
    trimmed_years = {int(k): v for k, v in summary["song_release_years"].items()}
    parts.extend(
        _mini_year_chart(trimmed_years, 80, 620, 1340, 170, PALETTE["sea"])
    )

    note = (
        f'Person nodes dominate the graph, but analytical tasks center on song-based relations. '
        f'Sailor Shift has {sum(summary["sailor_shift_relation_profile"].values())} direct ego-network links.'
    )
    parts.append(
        f'<text x="60" y="862" font-family="Avenir Next, Segoe UI, Arial, sans-serif" font-size="14" fill="{PALETTE["muted"]}">{note}</text>'
    )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def export_svgs(output_dir: Path, summary: dict) -> None:
    write_horizontal_bar_chart(
        output_dir / "node_type_distribution.svg",
        "MC1 Node Type Distribution",
        list(summary["node_type_distribution"].items()),
        color=PALETTE["teal"],
        subtitle="Five entity classes define the heterogeneous graph schema",
    )
    write_horizontal_bar_chart(
        output_dir / "edge_type_distribution_top10.svg",
        "MC1 Edge Type Distribution (Top 10)",
        list(summary["edge_type_distribution"].items())[:10],
        color=PALETTE["coral"],
        subtitle="Performance and production relations dominate the edge set",
    )
    write_horizontal_bar_chart(
        output_dir / "top_song_genres.svg",
        "Top Song Genres",
        list(summary["top_song_genres"].items()),
        color=PALETTE["gold"],
        subtitle="Genre diversity supports both overview and focused analysis",
    )
    write_horizontal_bar_chart(
        output_dir / "sailor_shift_relation_profile.svg",
        "Sailor Shift Relation Profile",
        list(summary["sailor_shift_relation_profile"].items()),
        color=PALETTE["sea"],
        subtitle="A compact ego-network snapshot around the central artist",
    )
    write_year_bar_chart(
        output_dir / "song_release_timeline.svg",
        "Song Releases by Year",
        {int(k): v for k, v in summary["song_release_years"].items()},
    )
    write_dashboard(output_dir / "dataset_overview_dashboard.svg", summary)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze the MC1 graph dataset.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Path to MC1_graph.json")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Directory for summary files and SVG charts",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    data = load_graph(args.input)
    summary = summarize(data)

    save_json(args.output_dir / "dataset_summary.json", summary)
    save_markdown(args.output_dir / "dataset_summary.md", summary)
    export_svgs(args.output_dir, summary)

    print(f"Summary written to: {args.output_dir}")
    print("Generated files:")
    for path in sorted(args.output_dir.iterdir()):
        print(f"- {path.name}")


if __name__ == "__main__":
    main()
