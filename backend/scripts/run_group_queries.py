#!/usr/bin/env python3
"""Run the 4 Neo4j group membership queries requested."""

from neo4j import GraphDatabase

URI = "bolt://127.0.0.1:7687"
AUTH = ("neo4j", "password")


def run_query(driver, label, cypher):
    print(f"\n{'=' * 80}")
    print(f"QUERY {label}")
    print(f"{'=' * 80}")
    try:
        with driver.session() as session:
            result = session.run(cypher)
            records = list(result)
            columns = result.keys()
            if not records:
                print("(No results returned)")
            else:
                header = " | ".join(f"{c:>35}" for c in columns)
                print(f" {header}")
                print(f" {'-' * len(header)}")
                for row in records:
                    values = []
                    for v in row.values():
                        if v is None:
                            values.append(f"{'NULL':>35}")
                        elif isinstance(v, (list, tuple, set)):
                            # Pretty-print lists with indentation on a new line
                            list_str = str(list(v))
                            if len(list_str) > 33:
                                list_str = list_str[:30] + "..."
                            values.append(f"{list_str:>35}")
                        elif isinstance(v, dict):
                            d_str = str(v)
                            if len(d_str) > 33:
                                d_str = d_str[:30] + "..."
                            values.append(f"{d_str:>35}")
                        else:
                            val_str = str(v)
                            if len(val_str) > 33:
                                val_str = val_str[:30] + "..."
                            values.append(f"{val_str:>35}")
                    print(f" {' | '.join(values)}")
            print(f"\n({len(records)} row(s) returned)")
    except Exception as e:
        print(f"ERROR: {e}")


def main():
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        queries = [
            (
                "1: Sailor Shift (17255) — groups",
                """
MATCH (p:Person {original_id: 17255})-[:MEMBER_OF]-(g:MusicalGroup)
RETURN p.name AS person, g.name AS group_name, g.original_id AS group_id
""",
            ),
            (
                "2: Ivy Echoes members — their groups",
                """
MATCH (p:Person)
WHERE toString(p.original_id) IN ['17256', '17257', '17258', '17259']
OPTIONAL MATCH (p)-[:MEMBER_OF]-(g:MusicalGroup)
RETURN p.name AS person, p.original_id AS id, g.name AS group_name, g.original_id AS group_id
ORDER BY p.name
""",
            ),
            (
                "3: Sailor Shift vs Ivy Echoes — shared group check",
                """
MATCH (p1:Person {original_id: 17255})
MATCH (p2:Person)
WHERE toString(p2.original_id) IN ['17256', '17257', '17258', '17259']
OPTIONAL MATCH (p1)-[:MEMBER_OF]-(g1:MusicalGroup)
OPTIONAL MATCH (p2)-[:MEMBER_OF]-(g2:MusicalGroup)
RETURN p1.name AS sailor_shift, g1.name AS sailor_group,
       p2.name AS bandmate, p2.original_id AS bandmate_id,
       g2.name AS bandmate_group
ORDER BY p2.name
""",
            ),
            (
                "4: All MusicalGroups — members list",
                """
MATCH (g:MusicalGroup)-[:MEMBER_OF]-(p:Person)
WITH g, collect(p.name) AS members, count(p) AS n
RETURN g.name AS group_name, g.original_id AS group_id, n AS member_count, members
ORDER BY n DESC
LIMIT 20
""",
            ),
        ]

        for label, cypher in queries:
            run_query(driver, label, cypher)

    finally:
        driver.close()


if __name__ == "__main__":
    main()
