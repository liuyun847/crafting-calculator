"""
测试配方管理API端点
"""
import requests
import json

BASE_URL = "http://127.0.0.1:5000"


def test_get_recipes():
    """测试获取配方列表"""
    print("\n=== 测试 GET /api/recipes ===")

    # 测试基本查询
    resp = requests.get(f"{BASE_URL}/api/recipes")
    print(f"基本查询: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"  总数: {data.get('total')}")
        print(f"  当前页: {data.get('page')}")
        print(f"  每页数量: {data.get('per_page')}")
        print(f"  配方数: {len(data.get('recipes', []))}")

    # 测试分页
    resp = requests.get(f"{BASE_URL}/api/recipes?page=1&per_page=5")
    print(f"分页查询 (第1页, 每页5条): {resp.status_code}")

    # 测试搜索
    resp = requests.get(f"{BASE_URL}/api/recipes?search=铁矿")
    print(f"搜索 '铁矿': {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"  搜索结果数: {data.get('total')}")


def test_get_single_recipe():
    """测试获取单个配方"""
    print("\n=== 测试 GET /api/recipes/<recipe_name> ===")

    # 获取存在的配方
    resp = requests.get(f"{BASE_URL}/api/recipes/铁矿冶炼")
    print(f"获取存在的配方 '铁矿冶炼': {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"  名称: {data.get('name')}")
        print(f"  设备: {data.get('device')}")
        print(f"  输入: {list(data.get('inputs', {}).keys())}")
        print(f"  输出: {list(data.get('outputs', {}).keys())}")

    # 获取不存在的配方
    resp = requests.get(f"{BASE_URL}/api/recipes/不存在的配方")
    print(f"获取不存在的配方: {resp.status_code}")
    if resp.status_code == 404:
        data = resp.json()
        print(f"  错误信息: {data.get('error')}")


def test_create_recipe():
    """测试创建配方"""
    print("\n=== 测试 POST /api/recipes ===")

    # 创建新配方
    new_recipe = {
        "name": "测试配方_123",
        "device": "测试设备",
        "inputs": {
            "原料A": {"amount": 10.0, "expression": "10"},
            "原料B": {"amount": 5.0, "expression": "5"}
        },
        "outputs": {
            "产品X": {"amount": 3.0, "expression": "3"}
        }
    }

    resp = requests.post(
        f"{BASE_URL}/api/recipes",
        json=new_recipe,
        headers={"Content-Type": "application/json"}
    )
    print(f"创建新配方: {resp.status_code}")
    if resp.status_code == 201:
        data = resp.json()
        print(f"  成功: {data.get('message')}")
        print(f"  配方: {data.get('recipe', {}).get('name')}")

    # 尝试创建重复配方
    resp = requests.post(
        f"{BASE_URL}/api/recipes",
        json=new_recipe,
        headers={"Content-Type": "application/json"}
    )
    print(f"创建重复配方: {resp.status_code}")
    if resp.status_code == 409:
        data = resp.json()
        print(f"  错误: {data.get('error')}")

    # 尝试创建缺少字段的配方
    invalid_recipe = {
        "name": "不完整配方",
        "device": "设备"
        # 缺少 inputs 和 outputs
    }
    resp = requests.post(
        f"{BASE_URL}/api/recipes",
        json=invalid_recipe,
        headers={"Content-Type": "application/json"}
    )
    print(f"创建缺少字段的配方: {resp.status_code}")
    if resp.status_code == 400:
        data = resp.json()
        print(f"  错误: {data.get('error')}")


def test_update_recipe():
    """测试更新配方"""
    print("\n=== 测试 PUT /api/recipes/<recipe_name> ===")

    # 更新现有配方（部分更新）
    update_data = {
        "device": "更新的测试设备",
        "outputs": {
            "产品Y": {"amount": 5.0, "expression": "5"}
        }
    }

    resp = requests.put(
        f"{BASE_URL}/api/recipes/测试配方_123",
        json=update_data,
        headers={"Content-Type": "application/json"}
    )
    print(f"更新配方: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"  成功: {data.get('message')}")
        print(f"  设备: {data.get('recipe', {}).get('device')}")

    # 更新不存在的配方
    resp = requests.put(
        f"{BASE_URL}/api/recipes/不存在的配方",
        json={"device": "新设备"},
        headers={"Content-Type": "application/json"}
    )
    print(f"更新不存在的配方: {resp.status_code}")
    if resp.status_code == 404:
        data = resp.json()
        print(f"  错误: {data.get('error')}")


def test_delete_recipe():
    """测试删除配方"""
    print("\n=== 测试 DELETE /api/recipes/<recipe_name> ===")

    # 删除现有配方
    resp = requests.delete(f"{BASE_URL}/api/recipes/测试配方_123")
    print(f"删除配方: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"  成功: {data.get('message')}")

    # 删除不存在的配方
    resp = requests.delete(f"{BASE_URL}/api/recipes/不存在的配方")
    print(f"删除不存在的配方: {resp.status_code}")
    if resp.status_code == 404:
        data = resp.json()
        print(f"  错误: {data.get('error')}")

    # 再次删除已删除的配方
    resp = requests.delete(f"{BASE_URL}/api/recipes/测试配方_123")
    print(f"再次删除已删除的配方: {resp.status_code}")
    if resp.status_code == 404:
        data = resp.json()
        print(f"  错误: {data.get('error')}")


def main():
    """主函数"""
    print("=" * 60)
    print("配方管理API测试")
    print("=" * 60)

    # 首先选择配方文件
    print("\n请先确保Web服务器已启动并选择了配方文件")
    input("按Enter键开始测试...")

    try:
        test_get_recipes()
        test_get_single_recipe()
        test_create_recipe()
        test_update_recipe()
        test_delete_recipe()

        print("\n" + "=" * 60)
        print("所有测试完成!")
        print("=" * 60)
    except requests.exceptions.ConnectionError:
        print(f"\n错误: 无法连接到服务器 {BASE_URL}")
        print("请确保Web服务器已启动")
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
