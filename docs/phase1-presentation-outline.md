# Phase 1 Presentation Outline

This outline is tailored to the two data-layer modules in OceanusEcho:

- **A. Career Arc**
- **B. Influence Galaxy**

Use it as the slide script for the Phase 1 PPT.

---

## Slide 1. Title

- Project name: `OceanusEcho`
- Challenge context: VAST Challenge 2025 MC1
- Team members and date

## Slide 2. The Data

- Source: `MC1_release/MC1_graph.json`
- Scale:
  - 17,412 nodes
  - 37,857 links
  - 18 connected components
- Node types:
  - Person, Song, RecordLabel, Album, MusicalGroup
- Edge types:
  - PerformerOf, InStyleOf, MemberOf, RecordedBy, DistributedBy, etc.
- Key attributes used:
  - Song / Album: `release_date`, `genre`, `notable`, `notoriety_date`
  - Person: `name`, `stage_name`

## Slide 3. The Tasks

- **Career Arc**
  - What is Sailor Shift’s career timeline?
  - When did notable work begin?
  - How are releases distributed over time?
- **Influence Galaxy**
  - Who influenced Sailor Shift?
  - Who collaborated with or was influenced by her?
  - How does influence spread in the Oceanus Folk community?

## Slide 4. Initial Design

- Career Arc:
  - stacked annual counts of works
  - highlight notable works
  - show milestone years
- Influence Galaxy:
  - force-directed subgraph
  - seed on Sailor Shift
  - filter by year, genre, and relation type
- Visual encoding ideas:
  - node color by type
  - node size by degree / role
  - edge style by relation type

## Slide 5. Data Layer Plan

- Build a reusable local graph index from `MC1_graph.json`
- For Career Arc:
  - person lookup
  - yearly aggregation
  - summary milestones:
    - first release year
    - first notable year
    - fame gap
    - peak year
- For Influence Galaxy:
  - seed-based subgraph extraction
  - relation filtering
  - node/edge serialization for the force graph
  - simple community summary for the slide narrative

## Slide 6. Implementation Plan

- Backend:
  - FastAPI analysis endpoints
  - Neo4j online mode (single source of truth)
  - no offline fallback in production path
- Frontend:
  - React + TanStack Query
  - ECharts for Career Arc
  - react-force-graph for Influence Galaxy
- Tools:
  - Python
  - FastAPI
  - Pydantic
  - React
  - ECharts
  - D3 / force layout helpers if needed

## Slide 7. Initial Results

- Career Arc:
  - can already return annual work counts and notable counts
  - milestone summary is available for Sailor Shift
- Influence Galaxy:
  - can already return a focused subgraph around Sailor Shift
  - can expand neighbors by relation type
  - can produce a basic cluster summary and bridge-node ranking

## Slide 8. Next Steps

- Connect the frontend panels to the backend endpoints
- Add brushing and node-click interactions
- Tune subgraph size and cluster summaries
- Prepare final narrative and export to the answer sheet
