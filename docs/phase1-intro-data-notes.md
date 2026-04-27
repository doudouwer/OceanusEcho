# Phase 1 Intro + Data Notes

## Slide A: Introduction

### One-sentence framing

OceanusEcho is a visual analytics system for exploring a heterogeneous music knowledge graph from VAST Challenge 2025 MC1, with a focus on understanding Sailor Shift's career evolution and the spread of Oceanus Folk influence.

### Suggested structure

- Background:
  The dataset is not a flat table. It is a music-industry graph that connects artists, songs, albums, labels, and groups through collaboration and influence relations.
- Problem:
  Traditional charts are good at showing trends, but weak at exposing cross-entity relationships such as influence chains, collaborations, and genre diffusion.
- Goal:
  Build an interactive visual system that supports both overview and detail-on-demand for two core questions:
  1. How did Sailor Shift's career develop over time?
  2. How did Oceanus Folk spread across artists and genres?
- Design direction:
  Combine temporal views and graph views so users can move between timeline patterns and relationship structures.

### What to show visually

- Left: a compact task statement or challenge context
- Right: a simple system concept figure with two modules:
  Career Arc + Influence Galaxy

## Slide B: Data

### Key message

The MC1 dataset is a heterogeneous, multi-relational graph with strong temporal and genre attributes, which makes it suitable for linked multi-view visualization.

### Core facts you can cite

- 17,412 nodes and 37,857 links
- 5 node types:
  Person, Song, RecordLabel, Album, MusicalGroup
- 12 edge types:
  such as PerformerOf, RecordedBy, ComposerOf, InStyleOf, CoverOf, MemberOf
- 16 connected components, with one dominant giant component of 17,277 nodes
- Song and album nodes contain rich analytical attributes:
  release_date, genre, notable, notoriety_date

### Recommended narrative

- Why this data is useful:
  It supports temporal analysis, influence tracing, collaboration discovery, and genre-level aggregation.
- Why this data is challenging:
  It is heterogeneous, relation-rich, and partially sparse for some metadata fields such as notoriety dates.
- Why the chosen views make sense:
  Timeline views fit release patterns and milestones, while graph views fit influence and collaboration paths.

### Suggested charts from the generated assets

- Node type distribution:
  `docs/phase1-assets/node_type_distribution.svg`
- Edge type distribution:
  `docs/phase1-assets/edge_type_distribution_top10.svg`
- Song release timeline:
  `docs/phase1-assets/song_release_timeline.svg`
- Top song genres:
  `docs/phase1-assets/top_song_genres.svg`

### Optional speaker note

Most entities are persons, but the analytical story is driven by song-centered relations. This means the data model is person-heavy, while the visual tasks are relation-heavy, so interaction design is important for reducing clutter and guiding exploration.
