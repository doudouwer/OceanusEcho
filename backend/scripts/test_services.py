"""
快速测试脚本 - 验证服务配置是否正确

用法:
    python -m scripts.test_services
"""

import sys
from pathlib import Path

# 添加 backend 目录到 path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


def test_imports():
    """测试模块导入"""
    print("测试模块导入...")
    
    try:
        from app.core.config import get_settings
        from app.core.database import Neo4jConnection
        from app.schemas.models import GenreFlowRequest, PersonProfileRequest
        from app.services.genre_flow_service import GenreFlowService
        from app.services.star_profiler_service import StarProfilerService
        print("✓ 所有模块导入成功")
        return True
    except Exception as e:
        print(f"✗ 模块导入失败: {e}")
        return False


def test_config():
    """测试配置"""
    print("\n测试配置...")
    
    try:
        from app.core.config import get_settings
        settings = get_settings()
        print(f"✓ 配置加载成功")
        print(f"  - Neo4j URI: {settings.neo4j_uri}")
        print(f"  - API 前缀: {settings.api_prefix}")
        return True
    except Exception as e:
        print(f"✗ 配置加载失败: {e}")
        return False


def test_schemas():
    """测试 Pydantic 模型"""
    print("\n测试 Pydantic 模型...")
    
    try:
        from app.schemas.models import (
            GenreFlowRequest, PersonProfileRequest,
            GenreFlowData, PersonProfileData
        )
        
        # 测试 GenreFlowRequest
        req = GenreFlowRequest(start_year=2020, end_year=2025)
        assert req.start_year == 2020
        assert req.end_year == 2025
        print(f"✓ GenreFlowRequest 验证通过")
        
        # 测试 PersonProfileRequest
        profile_req = PersonProfileRequest(person_ids=["1", "2", "3"])
        assert len(profile_req.person_ids) == 3
        print(f"✓ PersonProfileRequest 验证通过")
        
        return True
    except Exception as e:
        print(f"✗ Pydantic 模型测试失败: {e}")
        return False


def test_api_structure():
    """测试 API 结构"""
    print("\n测试 API 结构...")

    try:
        from app.main import app

        # 获取所有路由
        routes = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                routes.append(f"{list(route.methods)[0] if route.methods else 'GET'} {route.path}")

        print(f"✓ 找到 {len(routes)} 个 API 路由:")
        for r in sorted(routes):
            print(f"    {r}")

        return True
    except Exception as e:
        print(f"✗ API 结构测试失败: {e}")
        return False


def test_genre_flow_query():
    """直接测试流派演变 Cypher 查询"""
    print("\n测试流派演变 Cypher 查询...")

    try:
        from app.core.database import get_neo4j_connection

        db = get_neo4j_connection()

        with db.session() as session:
            # 测试查询 1: 检查 IN_STYLE_OF 关系完整分布
            print("\n  1. 检查 IN_STYLE_OF 关系完整分布...")
            check_query = """
            MATCH (s)-[:IN_STYLE_OF]->(t)
            RETURN labels(s)[0] as source_type, count(*) as count
            ORDER BY count DESC
            """
            result = session.run(check_query)
            total = 0
            print("     Source 类型分布:")
            for r in result:
                print(f"       {r['source_type']}: {r['count']}")
                total += r['count']
            print(f"     总 IN_STYLE_OF 关系数: {total}")

            # 测试查询 2: 检查 release_date 数据类型
            print("\n  2. 检查 release_date 数据...")
            date_check = """
            MATCH (s:Song)
            WHERE s.release_date IS NOT NULL
            RETURN s.release_date as rd, head(collect([s.genre, s.original_id])) as sample
            ORDER BY s.release_date
            LIMIT 5
            """
            result = session.run(date_check)
            for r in result:
                print(f"     release_date={r['rd']} (type: {type(r['rd']).__name__}), sample: {r['sample']}")

            # 测试查询 3: 执行流派演变查询（包含所有 target 类型）
            print("\n  3. 执行流派演变查询...")
            flow_query = """
            MATCH (song:Song)-[:IN_STYLE_OF]->(style_source)
            WHERE toInteger(song.release_date) >= 2017
              AND toInteger(song.release_date) <= 2025
              AND song.genre IS NOT NULL
              AND (
                (style_source:Song AND style_source.genre IS NOT NULL)
                OR (style_source:Album AND style_source.genre IS NOT NULL)
                OR (style_source:Person AND style_source.inferred_genre IS NOT NULL)
                OR (style_source:MusicalGroup AND style_source.inferred_genre IS NOT NULL)
              )
              AND song.genre <> coalesce(style_source.genre, style_source.inferred_genre)

            WITH song.genre as source_genre, 
                 coalesce(style_source.genre, style_source.inferred_genre) as target_genre, 
                 count(*) as flow_count
            RETURN source_genre, target_genre, flow_count
            ORDER BY flow_count DESC
            LIMIT 10
            """
            result = session.run(flow_query)
            records = list(result)
            print(f"     找到 {len(records)} 条流派流动")
            for r in records[:5]:
                print(f"     {r['source_genre']} -> {r['target_genre']}: {r['flow_count']}")

            # 检查 inferred_genre 是否存在
            print("\n  4. 检查 inferred_genre 属性...")
            check_inferred = """
            MATCH (p:Person) WHERE p.inferred_genre IS NOT NULL RETURN count(p) as count, head(collect([p.name, p.inferred_genre])) as sample LIMIT 1
            """
            result = session.run(check_inferred)
            record = result.single()
            print(f"     Person 有 inferred_genre: {record['count'] if record else 0}")
            if record and record['count'] > 0:
                print(f"     示例: {record['sample']}")
            
            check_inferred_g = """
            MATCH (g:MusicalGroup) WHERE g.inferred_genre IS NOT NULL RETURN count(g) as count, head(collect([g.name, g.inferred_genre])) as sample LIMIT 1
            """
            result = session.run(check_inferred_g)
            record = result.single()
            print(f"     MusicalGroup 有 inferred_genre: {record['count'] if record else 0}")
            if record and record['count'] > 0:
                print(f"     示例: {record['sample']}")
            
            # 检查 IN_STYLE_OF target 的类型分布
            print("\n  5. 检查 IN_STYLE_OF Target 类型分布...")
            target_dist = """
            MATCH (s)-[:IN_STYLE_OF]->(t)
            RETURN labels(t)[0] as target_type, count(*) as count
            ORDER BY count DESC
            """
            result = session.run(target_dist)
            print("     Target 类型分布:")
            for r in result:
                print(f"       {r['target_type']}: {r['count']}")
            
            # 检查 Person/MusicalGroup 作为 target 的情况
            print("\n  6. 检查 Person/MusicalGroup 作为 IN_STYLE_OF target...")
            check_targets = """
            MATCH (s)-[:IN_STYLE_OF]->(target)
            WHERE 'Person' IN labels(target) OR 'MusicalGroup' IN labels(target)
            RETURN labels(target)[0] as target_type, target.name as name, 
                   target.inferred_genre as inferred_genre
            LIMIT 5
            """
            result = session.run(check_targets)
            print("     Person/MusicalGroup 作为 target 的示例:")
            for r in result:
                print(f"       {r['name']} ({r['target_type']}): inferred_genre = {r['inferred_genre']}")

            print("✓ 数据检查完成")
            return True

    except Exception as e:
        print(f"✗ 查询测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 50)
    print("OceanusEcho 后端服务测试")
    print("=" * 50)

    results = []
    results.append(("模块导入", test_imports()))
    results.append(("配置加载", test_config()))
    results.append(("模型验证", test_schemas()))
    results.append(("API 结构", test_api_structure()))
    results.append(("流派查询", test_genre_flow_query()))

    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n所有测试通过！可以启动服务了。")
        return 0
    else:
        print("\n部分测试失败，请检查配置。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
