from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from app.core.database import get_neo4j_connection
from app.schemas.models import PersonMetrics, PersonProfile, PersonProfileData
from app.services.local_graph import load_local_graph
from app.services.neo4j_serialize import node_public_id


LOCAL_GRAPH = load_local_graph()


class StarProfilerService:
    def __init__(self) -> None:
        self.db = get_neo4j_connection()

    def _generate_evidence_id(self, params: dict[str, Any]) -> str:
        return hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12]

    def _calculate_entropy(self, distribution: list[int]) -> float:
        total = sum(distribution)
        if total == 0:
            return 0.0
        entropy = 0.0
        for count in distribution:
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        return round(entropy, 3)

    def _from_local_payload(self, payload: dict[str, Any]) -> PersonProfile:
        metrics = payload["metrics"]
        return PersonProfile(
            person_id=payload["person_id"],
            name=payload["name"],
            metrics=PersonMetrics(**metrics),
            top_genres=None,
            top_collaborators=None,
        )

    def get_person_profile(
        self,
        person_id: str,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> PersonProfile:
        params = {"person_id": person_id, "start_year": start_year, "end_year": end_year}
        _ = self._generate_evidence_id(params)

        with self.db.session() as session:
            if session is None:
                payload = LOCAL_GRAPH.person_profile(person_id, start_year or 1900, end_year or 2200)
                if payload is None:
                    return PersonProfile(person_id=person_id, name="Unknown", metrics=PersonMetrics())
                return self._from_local_payload(payload)

            time_filter = ""
            query_params = {"person_id": person_id}
            if start_year is not None:
                time_filter += " AND toInteger(s.release_date) >= $start_year"
                query_params["start_year"] = start_year
            if end_year is not None:
                time_filter += " AND toInteger(s.release_date) <= $end_year"
                query_params["end_year"] = end_year

            person_query = """
            MATCH (p:Person)
            WHERE toString(p.original_id) = $person_id OR toString(p.id) = $person_id OR p.name = $person_id
            RETURN p.name as name, p.stage_name as stage_name
            """
            person_record = session.run(person_query, person_id=person_id).single()
            if not person_record:
                return PersonProfile(person_id=person_id, name="Unknown", metrics=PersonMetrics())

            name = person_record["stage_name"] or person_record["name"]

            song_query = f"""
            MATCH (p:Person)
            WHERE toString(p.original_id) = $person_id OR toString(p.id) = $person_id OR p.name = $person_id
            MATCH (p)-[:PERFORMER_OF]->(s:Song)
            WHERE 1=1 {time_filter}
            RETURN
                count(s) as song_count,
                sum(CASE WHEN s.notable THEN 1 ELSE 0 END) as notable_count,
                collect(DISTINCT s.genre) as genres,
                collect(DISTINCT s.release_date) as release_years
            """
            song_record = session.run(song_query, **query_params).single()
            song_count = int(song_record["song_count"]) if song_record else 0
            notable_count = int(song_record["notable_count"]) if song_record and song_record["notable_count"] is not None else 0
            genres = [g for g in (song_record["genres"] if song_record else []) if g]
            release_years = [y for y in (song_record["release_years"] if song_record else []) if y]
            notable_rate = notable_count / song_count if song_count else 0.0

            valid_years = []
            for year in release_years:
                try:
                    y = int(str(year)[:4])
                except (TypeError, ValueError):
                    continue
                if 1900 < y < 2100:
                    valid_years.append(y)
            active_years = max(valid_years) - min(valid_years) + 1 if len(valid_years) > 1 else (1 if valid_years else 0)

            collab_query = f"""
            MATCH (p:Person)
            WHERE toString(p.original_id) = $person_id OR toString(p.id) = $person_id OR p.name = $person_id
            MATCH (p)-[:PERFORMER_OF]->(s:Song)<-[:PERFORMER_OF]-(collab:Person)
            WHERE p <> collab {time_filter}
            RETURN count(DISTINCT collab) as collaborator_count
            """
            collaborator_count = session.run(collab_query, **query_params).single()
            unique_collaborators = int(collaborator_count["collaborator_count"]) if collaborator_count else 0

            genre_counts_query = f"""
            MATCH (p:Person)
            WHERE toString(p.original_id) = $person_id OR toString(p.id) = $person_id OR p.name = $person_id
            MATCH (p)-[:PERFORMER_OF]->(s:Song)
            WHERE s.genre IS NOT NULL {time_filter}
            RETURN s.genre as genre, count(*) as count
            """
            genre_result = session.run(genre_counts_query, **query_params)
            genre_counts = [int(record["count"]) for record in genre_result]
            genre_entropy = self._calculate_entropy(genre_counts)

            degree_query = """
            MATCH (p:Person)
            WHERE toString(p.original_id) = $person_id OR toString(p.id) = $person_id OR p.name = $person_id
            MATCH (p)-[r]->(other)
            RETURN count(r) as degree
            """
            degree_record = session.run(degree_query, person_id=person_id).single()
            degree = int(degree_record["degree"]) if degree_record else 0

            influence_query = """
            MATCH (influencer:Person)
            WHERE toString(influencer.original_id) = $person_id OR toString(influencer.id) = $person_id OR influencer.name = $person_id
            MATCH (influencer)<-[:IN_STYLE_OF]-(influenced)
            WHERE influenced:Song OR influenced:Album
            RETURN count(influenced) as influence_count
            """
            influence_record = session.run(influence_query, person_id=person_id).single()
            style_influence_count = int(influence_record["influence_count"]) if influence_record else 0

            cowrite_query = f"""
            MATCH (p:Person)
            WHERE toString(p.original_id) = $person_id OR toString(p.id) = $person_id OR p.name = $person_id
            MATCH (p)-[:PERFORMER_OF|COMPOSER_OF|PRODUCER_OF]->(s:Song)<-[:PERFORMER_OF|COMPOSER_OF|PRODUCER_OF]-(other:Person)
            WHERE p <> other {time_filter}
            RETURN count(DISTINCT s) as cowrite_count
            """
            cowrite_record = session.run(cowrite_query, **query_params).single()
            song_cowrite_count = int(cowrite_record["cowrite_count"]) if cowrite_record else 0

            metrics = PersonMetrics(
                song_count=song_count,
                notable_count=notable_count,
                notable_rate=round(notable_rate, 3),
                active_years=active_years,
                unique_collaborators=unique_collaborators,
                genre_entropy=genre_entropy,
                degree=degree,
                pagerank=round(degree / 1000.0, 4),
                song_cowrite_count=song_cowrite_count,
                style_influence_count=style_influence_count,
            )
            return PersonProfile(
                person_id=person_id,
                name=name,
                metrics=metrics,
                top_genres=genres[:5] if genres else None,
                top_collaborators=None,
            )

    def get_person_profiles(
        self,
        person_ids: list[str],
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> PersonProfileData:
        _ = self._generate_evidence_id({"person_ids": person_ids, "start_year": start_year, "end_year": end_year})
        profiles = [self.get_person_profile(person_id, start_year, end_year) for person_id in person_ids]
        return PersonProfileData(profiles=profiles)

    def get_normalized_profiles(
        self,
        person_ids: list[str],
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> dict[str, Any]:
        profile_data = self.get_person_profiles(person_ids, start_year, end_year)
        if not profile_data.profiles:
            return {"profiles": [], "dimensions": profile_data.dimensions}

        metrics_names = profile_data.dimensions
        min_vals: dict[str, float] = {}
        max_vals: dict[str, float] = {}
        for metric_name in metrics_names:
            values = [float(getattr(profile.metrics, metric_name, 0)) for profile in profile_data.profiles]
            min_vals[metric_name] = min(values) if values else 0
            max_vals[metric_name] = max(values) if values else 1

        normalized_profiles = []
        for profile in profile_data.profiles:
            normalized_metrics = {}
            for metric_name in metrics_names:
                raw_value = float(getattr(profile.metrics, metric_name, 0))
                min_val = min_vals[metric_name]
                max_val = max_vals[metric_name]
                normalized_metrics[metric_name] = round((raw_value - min_val) / (max_val - min_val), 3) if max_val > min_val else 0.0
            normalized_profiles.append(
                {
                    "person_id": profile.person_id,
                    "name": profile.name,
                    "metrics": normalized_metrics,
                    "raw_metrics": {metric_name: getattr(profile.metrics, metric_name, 0) for metric_name in metrics_names},
                }
            )

        return {
            "profiles": normalized_profiles,
            "dimensions": metrics_names,
            "normalization": {
                "type": "min-max",
                "ranges": {m: {"min": min_vals[m], "max": max_vals[m]} for m in metrics_names},
            },
        }


star_profiler_service = StarProfilerService()
