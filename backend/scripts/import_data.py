"""
数据导入脚本：将 MC1_graph.json 导入 Neo4j

用法:
    python -m scripts.import_data --path ../MC1_release/MC1_graph.json
"""

import json
import argparse
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

# 节点类型映射
NODE_TYPE_MAPPING = {
    "Person": "Person",
    "Song": "Song",
    "RecordLabel": "RecordLabel",
    "Album": "Album",
    "MusicalGroup": "MusicalGroup"
}

# 边类型映射（JSON Edge Type -> Neo4j Relationship Type）
EDGE_TYPE_MAPPING = {
    "PerformerOf": "PERFORMER_OF",
    "RecordedBy": "RECORDED_BY",
    "ComposerOf": "COMPOSER_OF",
    "ProducerOf": "PRODUCER_OF",
    "DistributedBy": "DISTRIBUTED_BY",
    "LyricistOf": "LYRICIST_OF",
    "InStyleOf": "IN_STYLE_OF",
    "InterpolatesFrom": "INTERPOLATES_FROM",
    "LyricalReferenceTo": "LYRICAL_REFERENCE_TO",
    "CoverOf": "COVER_OF",
    "DirectlySamples": "DIRECTLY_SAMPLES",
    "MemberOf": "MEMBER_OF"
}

# Neo4j 属性名映射
SONG_PROPS = ["name", "single", "release_date", "genre", "notable"]
PERSON_PROPS = ["name", "stage_name"]
LABEL_PROPS = ["name"]
ALBUM_PROPS = ["name"]
GROUP_PROPS = ["name"]


def get_node_props(node_type: str, node_data: dict) -> dict:
    """提取节点属性"""
    props = {}
    
    if node_type == "Song":
        for prop in SONG_PROPS:
            if prop in node_data:
                val = node_data[prop]
                # 转换布尔值
                if prop == "single" or prop == "notable":
                    val = bool(val)
                props[prop] = val
        # 添加原 ID
        props["original_id"] = node_data.get("id")
        
    elif node_type == "Person":
        for prop in PERSON_PROPS:
            if prop in node_data:
                props[prop] = node_data[prop]
        props["original_id"] = node_data.get("id")
        
    elif node_type == "RecordLabel":
        for prop in LABEL_PROPS:
            if prop in node_data:
                props[prop] = node_data[prop]
        props["original_id"] = node_data.get("id")
        
    elif node_type == "Album":
        for prop in ALBUM_PROPS:
            if prop in node_data:
                props[prop] = node_data[prop]
        props["original_id"] = node_data.get("id")
        
    elif node_type == "MusicalGroup":
        for prop in GROUP_PROPS:
            if prop in node_data:
                props[prop] = node_data[prop]
        props["original_id"] = node_data.get("id")
    
    return props


def import_to_neo4j(json_path: str, batch_size: int = 1000):
    """将 JSON 数据导入 Neo4j"""
    
    # 连接数据库
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    try:
        with driver.session() as session:
            # 先清空现有数据
            print("清空现有数据...")
            session.run("MATCH (n) DETACH DELETE n")
            
            # 创建约束和索引
            print("创建约束和索引...")
            session.run("""
                CREATE CONSTRAINT person_id IF NOT EXISTS
                FOR (p:Person) REQUIRE p.original_id IS UNIQUE
            """)
            session.run("""
                CREATE CONSTRAINT song_id IF NOT EXISTS
                FOR (s:Song) REQUIRE s.original_id IS UNIQUE
            """)
            session.run("""
                CREATE INDEX song_release_date IF NOT EXISTS
                FOR (s:Song) ON (s.release_date)
            """)
            session.run("""
                CREATE INDEX song_genre IF NOT EXISTS
                FOR (s:Song) ON (s.genre)
            """)
            session.run("""
                CREATE INDEX person_name IF NOT EXISTS
                FOR (p:Person) ON (p.name)
            """)
            session.run("""
                CREATE FULLTEXT INDEX person_name_search IF NOT EXISTS
                FOR (p:Person) ON EACH [p.name]
            """)
            session.run("""
                CREATE FULLTEXT INDEX song_name_search IF NOT EXISTS
                FOR (s:Song) ON EACH [s.name]
            """)
            
            # 读取 JSON 文件
            print(f"读取数据文件: {json_path}")
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            nodes = data.get("nodes", [])
            links = data.get("links", [])
            
            print(f"共有 {len(nodes)} 个节点, {len(links)} 条边")
            
            # 创建节点映射: original_id -> Neo4j internal id
            id_mapping = {}
            
            # 批量导入节点
            print("导入节点...")
            node_count = {k: 0 for k in NODE_TYPE_MAPPING.keys()}
            
            for i in range(0, len(nodes), batch_size):
                batch = nodes[i:i+batch_size]
                
                for node in batch:
                    node_type = node.get("Node Type")
                    if node_type not in NODE_TYPE_MAPPING:
                        continue
                    
                    neo4j_label = NODE_TYPE_MAPPING[node_type]
                    props = get_node_props(node_type, node)
                    original_id = node.get("id")
                    
                    # 构建 Cypher 查询
                    props_keys = list(props.keys())
                    props_values = list(props.values())
                    
                    query = f"""
                        CREATE (n:{neo4j_label} {{{', '.join([f'{k}: ${k}' for k in props_keys])}}})
                        RETURN id(n) as internal_id, n.original_id as original_id
                    """
                    
                    result = session.run(query, props)
                    record = result.single()
                    
                    if record:
                        internal_id = record["internal_id"]
                        orig_id = record["original_id"]
                        id_mapping[orig_id] = internal_id
                        node_count[node_type] += 1
                
                if (i + batch_size) % 5000 == 0:
                    print(f"  已处理 {min(i + batch_size, len(nodes))}/{len(nodes)} 个节点")
            
            print(f"节点导入完成: {dict(node_count)}")
            
            # 导入边
            print("导入边...")
            edge_count = {k: 0 for k in EDGE_TYPE_MAPPING.keys()}
            
            for link in links:
                edge_type = link.get("Edge Type")
                if edge_type not in EDGE_TYPE_MAPPING:
                    continue
                
                neo4j_rel = EDGE_TYPE_MAPPING[edge_type]
                source_id = link.get("source")
                target_id = link.get("target")
                
                # 检查 ID 是否存在于映射中
                if source_id not in id_mapping or target_id not in id_mapping:
                    continue
                
                query = f"""
                    MATCH (a), (b)
                    WHERE id(a) = $source_id AND id(b) = $target_id
                    CREATE (a)-[r:{neo4j_rel}]->(b)
                """
                
                session.run(query, source_id=id_mapping[source_id], target_id=id_mapping[target_id])
                edge_count[edge_type] += 1
            
            print(f"边导入完成: {dict(edge_count)}")
            
            # 创建流派索引（用于 Genre Flow 查询优化）
            print("创建流派索引...")
            session.run("""
                MATCH (s:Song)
                WHERE s.genre IS NOT NULL
                WITH s.genre as genre, count(*) as cnt
                RETURN genre, cnt ORDER BY cnt DESC
            """).consume()
            
            print("\n数据导入完成!")
            print(f"总节点数: {sum(node_count.values())}")
            print(f"总边数: {sum(edge_count.values())}")
            
    finally:
        driver.close()


def main():
    parser = argparse.ArgumentParser(description="将 MC1_graph.json 导入 Neo4j")
    parser.add_argument("--path", type=str, default="../MC1_release/MC1_graph.json",
                        help="JSON 数据文件路径")
    parser.add_argument("--batch-size", type=int, default=1000,
                        help="批量导入大小")
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    json_path = Path(args.path)
    if not json_path.exists():
        # 尝试相对路径
        json_path = Path(__file__).parent.parent.parent / args.path
        if not json_path.exists():
            print(f"错误: 文件不存在 {args.path}")
            return
    
    import_to_neo4j(str(json_path), args.batch_size)


if __name__ == "__main__":
    main()
