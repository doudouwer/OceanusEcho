"""
流派演变 (Genre Flow) 服务

提供两种可视化模式的数据：
1. 桑基图 (Sankey): 展示流派之间的流动关系
2. 河流图 (Streamgraph): 展示流派随时间的数量变化

主要查询逻辑：
- 桑基图：通过 IN_STYLE_OF 关系追踪流派影响流向
- 河流图：按年份统计各流派的歌曲数量
"""

from typing import List, Optional, Dict, Any
from ..core.database import get_neo4j_connection
from ..schemas.models import (
    GenreFlowData, GenreFlowNode, GenreFlowLink,
    GenreFlowSeries, GenreFlowSeriesPoint, MetaInfo
)
import hashlib
import json


class GenreFlowService:
    """流派演变服务"""
    
    def __init__(self):
        self.db = get_neo4j_connection()
    
    def _generate_evidence_id(self, params: Dict[str, Any]) -> str:
        """生成可追溯的证据 ID"""
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()[:12]
    
    def get_sankey_data(
        self,
        start_year: int,
        end_year: int,
        source_genre: Optional[str] = None,
        limit: int = 100
    ) -> GenreFlowData:
        """
        获取桑基图数据
        
        桑基图展示流派之间的影响流动：
        - 源节点：影响力来源的流派（如 Oceanus Folk）
        - 目标节点：受影响的目标流派（如 Indie Pop）
        - 边的权重：IN_STYLE_OF 关系的数量
        
        查询逻辑：
        1. 找到所有在时间范围内的歌曲
        2. 通过 PERFORMER_OF 找到演唱者
        3. 通过 IN_STYLE_OF 找到风格影响
        4. 统计流派之间的流动数量
        """
        
        params = {
            "start_year": start_year,
            "end_year": end_year,
            "source_genre": source_genre,
            "limit": limit
        }
        evidence_id = self._generate_evidence_id(params)
        
        with self.db.session() as session:
            # 构建查询
            genre_filter_clause = ""
            if source_genre:
                genre_filter_clause = "AND song.genre = $source_genre"
            
            # Cypher 查询：追踪流派之间的风格影响流动
            # 模式：Song -[:IN_STYLE_OF]-> StyleSource (Song/Album/Person/MusicalGroup)
            # 统计 source_genre -> target_genre 的流动量
            # 根据 PDF: InStyleOf 的 source 是 Song/Album，target 可以是 Song/Album/Person/MusicalGroup
            # Song/Album 直接有 genre 属性，Person/MusicalGroup 使用 inferred_genre
            # 注意：release_date 在数据库中是字符串类型，需要用 toInteger() 转换
            query = f"""
            MATCH (song:Song)-[:IN_STYLE_OF]->(style_source)
            WHERE toInteger(song.release_date) >= $start_year
              AND toInteger(song.release_date) <= $end_year
              AND song.genre IS NOT NULL
              AND (
                (style_source:Song AND style_source.genre IS NOT NULL)
                OR (style_source:Album AND style_source.genre IS NOT NULL)
                OR (style_source:Person AND style_source.inferred_genre IS NOT NULL)
                OR (style_source:MusicalGroup AND style_source.inferred_genre IS NOT NULL)
              )
              AND song.genre <> coalesce(style_source.genre, style_source.inferred_genre)
              {genre_filter_clause}
            
            WITH song.genre as source_genre, 
                 coalesce(style_source.genre, style_source.inferred_genre) as target_genre, 
                 count(*) as flow_count
            RETURN source_genre, target_genre, flow_count
            ORDER BY flow_count DESC
            LIMIT $limit
            """
            
            result = session.run(
                query,
                start_year=start_year,
                end_year=end_year,
                source_genre=source_genre,
                limit=limit
            )
            
            # 构建节点和边
            nodes_set = set()
            links_list = []
            
            for record in result:
                source = record["source_genre"]
                target = record["target_genre"]
                value = record["flow_count"]
                
                nodes_set.add(source)
                nodes_set.add(target)
                links_list.append(GenreFlowLink(source=source, target=target, value=value))
            
            # 创建节点列表
            nodes = [GenreFlowNode(id=name, name=name) for name in sorted(nodes_set)]
            
            return GenreFlowData(
                nodes=nodes,
                links=links_list,
                series=None
            )
    
    def get_streamgraph_data(
        self,
        start_year: int,
        end_year: int,
        limit: int = 50
    ) -> GenreFlowData:
        """
        获取河流图数据
        
        河流图展示流派随时间的数量变化：
        - 每个流派是一条"河流"
        - 河流的宽度表示该年份该流派的活动量（歌曲数量）
        """
        
        params = {
            "start_year": start_year,
            "end_year": end_year,
            "limit": limit
        }
        evidence_id = self._generate_evidence_id(params)
        
        with self.db.session() as session:
            # 查询每个流派每年的歌曲数量
            query = """
            MATCH (s:Song)
            WHERE toInteger(s.release_date) >= $start_year
              AND toInteger(s.release_date) <= $end_year
              AND s.genre IS NOT NULL
            RETURN s.genre as genre, s.release_date as year, count(*) as song_count
            ORDER BY genre, year
            """
            
            result = session.run(
                query,
                start_year=start_year,
                end_year=end_year
            )
            
            # 按流派聚合数据
            genre_data: Dict[str, List[GenreFlowSeriesPoint]] = {}
            
            for record in result:
                genre = record["genre"]
                year_str = record["year"]
                count = record["song_count"]
                
                try:
                    year = int(year_str)
                except (ValueError, TypeError):
                    continue
                
                if genre not in genre_data:
                    genre_data[genre] = []
                genre_data[genre].append(GenreFlowSeriesPoint(year=year, value=count))
            
            # 创建系列列表
            series = [
                GenreFlowSeries(genre=genre, points=sorted(points, key=lambda x: x.year))
                for genre, points in genre_data.items()
            ]
            
            # 按流派名称排序
            series.sort(key=lambda x: x.genre)
            
            return GenreFlowData(
                nodes=None,
                links=None,
                series=series
            )
    
    def get_genre_stats(
        self,
        start_year: int,
        end_year: int
    ) -> Dict[str, Any]:
        """
        获取流派统计信息
        
        返回：
        - 所有流派的列表
        - 每个流派的歌曲总数
        - 时间范围
        """
        
        with self.db.session() as session:
            query = """
            MATCH (s:Song)
            WHERE toInteger(s.release_date) >= $start_year
              AND toInteger(s.release_date) <= $end_year
              AND s.genre IS NOT NULL
            RETURN s.genre as genre, count(*) as song_count
            ORDER BY song_count DESC
            """
            
            result = session.run(
                query,
                start_year=start_year,
                end_year=end_year
            )
            
            stats = []
            for record in result:
                stats.append({
                    "genre": record["genre"],
                    "song_count": record["song_count"]
                })
            
            return {
                "genres": stats,
                "start_year": start_year,
                "end_year": end_year
            }


# 全局服务实例
genre_flow_service = GenreFlowService()
