"""
艺人画像 (Star Profiler) 服务

提供艺人多维度画像数据，用于雷达图可视化：

指标维度：
1. song_count - 歌曲数量
2. notable_count - 代表作数量
3. notable_rate - 代表作比例
4. active_years - 活跃年数
5. unique_collaborators - 独立合作者数
6. genre_entropy - 流派多样性（信息熵）
7. degree - 图度数（连接数）
8. pagerank - PageRank  centrality
9. song_cowrite_count - 合唱/合著歌曲数
10. style_influence_count - 风格影响力（被 IN_STYLE_OF 引用次数）
"""

from typing import List, Optional, Dict, Any
import math
from ..core.database import get_neo4j_connection
from ..schemas.models import (
    PersonProfile, PersonMetrics, PersonProfileData, MetaInfo
)
import hashlib
import json


class StarProfilerService:
    """艺人画像服务"""
    
    def __init__(self):
        self.db = get_neo4j_connection()
    
    def _generate_evidence_id(self, params: Dict[str, Any]) -> str:
        """生成可追溯的证据 ID"""
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()[:12]
    
    def _calculate_entropy(self, distribution: List[int]) -> float:
        """
        计算信息熵
        
        熵越高表示分布越均匀（流派多样性越高）
        H = -Σ p_i * log(p_i)
        """
        total = sum(distribution)
        if total == 0:
            return 0.0
        
        entropy = 0.0
        for count in distribution:
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        
        return round(entropy, 3)
    
    def get_person_profile(
        self,
        person_id: str,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> PersonProfile:
        """
        获取单个艺人画像
        
        Args:
            person_id: 艺人原始 ID
            start_year: 起始年份（可选）
            end_year: 结束年份（可选）
        """
        
        with self.db.session() as session:
            # 构建时间过滤条件（release_date 是字符串，需要 toInteger 转换）
            time_filter = ""
            params = {"person_id": person_id}
            
            if start_year:
                time_filter += " AND toInteger(s.release_date) >= $start_year"
                params["start_year"] = start_year
            if end_year:
                time_filter += " AND toInteger(s.release_date) <= $end_year"
                params["end_year"] = end_year
            
            # 1. 获取艺人基本信息
            person_query = """
            MATCH (p:Person {original_id: toInteger($person_id)})
            RETURN p.name as name, p.stage_name as stage_name
            """
            person_result = session.run(person_query, person_id=person_id)
            person_record = person_result.single()
            
            if not person_record:
                return PersonProfile(
                    person_id=person_id,
                    name="Unknown",
                    metrics=PersonMetrics()
                )
            
            name = person_record["stage_name"] or person_record["name"]
            
            # 2. 获取歌曲统计
            song_stats_query = f"""
            MATCH (p:Person {{original_id: toInteger($person_id)}})-[:PERFORMER_OF]->(s:Song)
            WHERE 1=1 {time_filter}
            RETURN 
                count(s) as song_count,
                sum(CASE WHEN s.notable THEN 1 ELSE 0 END) as notable_count,
                collect(DISTINCT s.genre) as genres,
                collect(DISTINCT s.release_date) as release_years
            """
            song_result = session.run(song_stats_query, **params)
            song_record = song_result.single()
            
            song_count = song_record["song_count"] if song_record else 0
            notable_count = song_record["notable_count"] if song_record else 0
            genres = [g for g in song_record["genres"] if g] if song_record and song_record["genres"] else []
            release_years = [y for y in song_record["release_years"] if y] if song_record and song_record["release_years"] else []
            
            # 计算代表作比例
            notable_rate = notable_count / song_count if song_count > 0 else 0.0
            
            # 计算活跃年数（release_date 是字符串，需要转换）
            try:
                valid_years = [int(float(y)) for y in release_years if y]
                valid_years = [y for y in valid_years if 1900 < y < 2100]  # 过滤无效年份
                active_years = max(valid_years) - min(valid_years) + 1 if len(valid_years) > 1 else (1 if valid_years else 0)
            except:
                active_years = 0
            
            # 3. 获取独立合作者数
            collab_query = f"""
            MATCH (p:Person {{original_id: toInteger($person_id)}})-[:PERFORMER_OF]->(s:Song)<-[:PERFORMER_OF]-(collab:Person)
            WHERE p <> collab {time_filter}
            RETURN count(DISTINCT collab) as collaborator_count
            """
            collab_result = session.run(collab_query, **params)
            collab_record = collab_result.single()
            unique_collaborators = collab_record["collaborator_count"] if collab_record else 0
            
            # 4. 计算流派熵
            genre_counts_query = f"""
            MATCH (p:Person {{original_id: toInteger($person_id)}})-[:PERFORMER_OF]->(s:Song)
            WHERE s.genre IS NOT NULL {time_filter}
            RETURN s.genre as genre, count(*) as count
            """
            genre_result = session.run(genre_counts_query, **params)
            genre_counts = [r["count"] for r in genre_result]
            genre_entropy = self._calculate_entropy(genre_counts)
            
            # 5. 获取图度数
            degree_query = """
            MATCH (p:Person {original_id: toInteger($person_id)})-[r]->(other)
            RETURN count(r) as degree
            """
            degree_result = session.run(degree_query, person_id=person_id)
            degree_record = degree_result.single()
            degree = degree_record["degree"] if degree_record else 0
            
            # 6. 获取风格影响力（有多少歌曲/专辑以该艺人为风格来源）
            # 根据 PDF: InStyleOf: source (Song/Album) → target (Song/Album/Person/MusicalGroup)
            # 即 Song/Album 的风格受 Person 影响
            influence_query = """
            MATCH (influencer:Person {original_id: toInteger($person_id)})<-[:IN_STYLE_OF]-(influenced)
            WHERE influenced:Song OR influenced:Album
            RETURN count(influenced) as influence_count
            """
            influence_result = session.run(influence_query, person_id=person_id)
            influence_record = influence_result.single()
            style_influence_count = influence_record["influence_count"] if influence_record else 0
            
            # 7. 获取合唱/合著歌曲数
            cowrite_query = f"""
            MATCH (p:Person {{original_id: toInteger($person_id)}})-[:PERFORMER_OF|COMPOSER_OF|PRODUCER_OF]->(s:Song)<-[:PERFORMER_OF|COMPOSER_OF|PRODUCER_OF]-(other:Person)
            WHERE p <> other {time_filter}
            RETURN count(DISTINCT s) as cowrite_count
            """
            cowrite_result = session.run(cowrite_query, **params)
            cowrite_record = cowrite_result.single()
            song_cowrite_count = cowrite_record["cowrite_count"] if cowrite_record else 0
            
            # 8. 计算 PageRank（简化版：使用 Neo4j GDS 或近似计算）
            # 注意：完整的 PageRank 需要使用 GDS 库，这里使用简化的度数中心性
            pagerank = degree / 1000.0  # 简化为归一化的度数
            
            # 构建指标对象
            metrics = PersonMetrics(
                song_count=song_count,
                notable_count=notable_count,
                notable_rate=round(notable_rate, 3),
                active_years=active_years,
                unique_collaborators=unique_collaborators,
                genre_entropy=genre_entropy,
                degree=degree,
                pagerank=round(pagerank, 4),
                song_cowrite_count=song_cowrite_count,
                style_influence_count=style_influence_count
            )
            
            return PersonProfile(
                person_id=person_id,
                name=name,
                metrics=metrics,
                top_genres=genres[:5] if genres else None,  # 最多5个流派
                top_collaborators=None  # 可扩展：添加主要合作者信息
            )
    
    def get_person_profiles(
        self,
        person_ids: List[str],
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> PersonProfileData:
        """
        批量获取多个艺人画像
        
        Args:
            person_ids: 艺人 ID 列表
            start_year: 起始年份（可选）
            end_year: 结束年份（可选）
        """
        
        params = {
            "person_ids": person_ids,
            "start_year": start_year if start_year else None,
            "end_year": end_year if end_year else None
        }
        evidence_id = self._generate_evidence_id(params)
        
        profiles = []
        for person_id in person_ids:
            profile = self.get_person_profile(person_id, start_year, end_year)
            profiles.append(profile)
        
        dimensions = [
            "song_count", "notable_rate", "active_years",
            "unique_collaborators", "genre_entropy", "degree", "pagerank"
        ]
        
        return PersonProfileData(
            profiles=profiles,
            dimensions=dimensions
        )
    
    def get_normalized_profiles(
        self,
        person_ids: List[str],
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取归一化后的艺人画像（便于前端雷达图直接使用）
        
        对各指标进行 min-max 归一化到 [0, 1] 范围
        """
        
        # 先获取原始数据
        profile_data = self.get_person_profiles(person_ids, start_year, end_year)
        
        if not profile_data.profiles:
            return {"profiles": [], "dimensions": profile_data.dimensions}
        
        # 计算每个维度的 min 和 max
        metrics_names = profile_data.dimensions
        min_vals = {}
        max_vals = {}
        
        for metric_name in metrics_names:
            values = [
                getattr(p.metrics, metric_name, 0) 
                for p in profile_data.profiles
            ]
            min_vals[metric_name] = min(values) if values else 0
            max_vals[metric_name] = max(values) if values else 1
        
        # 归一化
        normalized_profiles = []
        for profile in profile_data.profiles:
            normalized_metrics = {}
            for metric_name in metrics_names:
                raw_value = getattr(profile.metrics, metric_name, 0)
                min_val = min_vals[metric_name]
                max_val = max_vals[metric_name]
                
                if max_val > min_val:
                    normalized_metrics[metric_name] = round(
                        (raw_value - min_val) / (max_val - min_val), 3
                    )
                else:
                    normalized_metrics[metric_name] = 0.0
            
            normalized_profiles.append({
                "person_id": profile.person_id,
                "name": profile.name,
                "metrics": normalized_metrics,
                "raw_metrics": {
                    metric_name: getattr(profile.metrics, metric_name, 0)
                    for metric_name in metrics_names
                }
            })
        
        return {
            "profiles": normalized_profiles,
            "dimensions": metrics_names,
            "normalization": {
                "type": "min-max",
                "ranges": {m: {"min": min_vals[m], "max": max_vals[m]} for m in metrics_names}
            }
        }


# 全局服务实例
star_profiler_service = StarProfilerService()
