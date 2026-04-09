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
            # 测试查询 1: 检查 IN_STYLE_OF 关系是否存在
            print("\n  1. 检查 IN_STYLE_OF 关系...")
            check_query = """
            MATCH (s:Song)-[r:IN_STYLE_OF]->(target)
            RETURN count(r) as total_in_style_of,
                   head(collect([s.genre, type(r), target.genre])) as sample
            LIMIT 1
            """
            result = session.run(check_query)
            record = result.single()
            print(f"     总 IN_STYLE_OF 关系数: {record['total_in_style_of']}")
            print(f"     示例: {record['sample']}")

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

            # 测试查询 3: 执行流派演变查询
            print("\n  3. 执行流派演变查询...")
            flow_query = """
            MATCH (song:Song)-[:IN_STYLE_OF]->(style_source)
            WHERE toInteger(song.release_date) >= 2017
              AND toInteger(song.release_date) <= 2025
              AND song.genre IS NOT NULL
              AND (style_source:Song OR style_source:Album)
              AND style_source.genre IS NOT NULL
              AND song.genre <> style_source.genre

            WITH song.genre as source_genre, style_source.genre as target_genre, count(*) as flow_count
            RETURN source_genre, target_genre, flow_count
            ORDER BY flow_count DESC
            LIMIT 10
            """
            result = session.run(flow_query)
            records = list(result)
            print(f"     找到 {len(records)} 条流派流动")
            for r in records[:5]:
                print(f"     {r['source_genre']} -> {r['target_genre']}: {r['flow_count']}")

            print("✓ 流派演变查询测试完成")
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
