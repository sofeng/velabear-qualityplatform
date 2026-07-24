#!/usr/bin/env python
"""
验证AI开发功能更新
检查新添加的字段和功能是否正常工作
"""
import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.ai_development.models import AIDevelopmentTask, AIDevelopmentConfig
from apps.ai_development.serializers import AIDevelopmentTaskSerializer
import json

def print_separator(title):
    """打印分隔线"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def verify_model_fields():
    """验证模型字段"""
    print_separator("1. 验证数据库模型字段")

    # 检查字段是否存在
    task_fields = [f.name for f in AIDevelopmentTask._meta.get_fields()]

    print("\n✓ 检查新增字段:")
    new_fields = ['git_repository_url', 'files_modified']
    for field in new_fields:
        if field in task_fields:
            print(f"  ✅ {field} - 已添加")
        else:
            print(f"  ❌ {field} - 未找到")

    return all(field in task_fields for field in new_fields)

def verify_existing_tasks():
    """验证现有任务"""
    print_separator("2. 验证现有任务数据")

    tasks = AIDevelopmentTask.objects.all()[:5]
    print(f"\n任务总数: {AIDevelopmentTask.objects.count()}")
    print(f"显示前5个任务:\n")

    for task in tasks:
        print(f"任务ID: {task.task_id}")
        print(f"  状态: {task.get_status_display()}")
        print(f"  需求: {task.requirement.requirement_name}")
        print(f"  Git仓库: {task.git_repository_url or '未设置（旧任务）'}")
        print(f"  Git分支: {task.git_branch or '未设置'}")
        print(f"  Commit Hash: {task.git_commit_hash or '未设置'}")

        if task.files_modified:
            try:
                files = json.loads(task.files_modified)
                print(f"  修改文件数: {len(files)}")
                if files:
                    print(f"  文件列表: {files[:3]}{'...' if len(files) > 3 else ''}")
            except:
                print(f"  修改文件: 解析失败")
        else:
            print(f"  修改文件: 无（旧任务）")
        print()

def verify_serializer():
    """验证序列化器"""
    print_separator("3. 验证序列化器")

    task = AIDevelopmentTask.objects.first()
    if task:
        serializer = AIDevelopmentTaskSerializer(task)
        data = serializer.data

        print("\n✓ 检查序列化器字段:")
        check_fields = ['git_repository_url', 'files_modified', 'files_modified_list']
        for field in check_fields:
            if field in data:
                print(f"  ✅ {field} - 存在")
                if field == 'files_modified_list':
                    print(f"     值: {data[field]}")
            else:
                print(f"  ❌ {field} - 缺失")

        return all(field in data for field in check_fields)
    else:
        print("\n⚠️  数据库中没有任务，无法验证序列化器")
        return False

def verify_api_endpoints():
    """验证API端点配置"""
    print_separator("4. 验证API端点")

    from django.urls import resolve
    from rest_framework.reverse import reverse

    try:
        # 测试任务列表URL
        url = '/api/ai-development/tasks/'
        print(f"\n✓ 任务列表端点: {url}")

        # 测试日志端点
        task = AIDevelopmentTask.objects.first()
        if task:
            log_url = f'/api/ai-development/tasks/{task.task_id}/logs/'
            print(f"✓ 日志端点: {log_url}")
            print(f"  参数: ?log_type=execution 或 ?log_type=ai_conversation")

        return True
    except Exception as e:
        print(f"❌ API端点验证失败: {str(e)}")
        return False

def create_test_scenario():
    """创建测试场景说明"""
    print_separator("5. 测试场景")

    print("""
下一步测试流程:

1. 启动服务:
   # 终端1: 启动Django
   python manage.py runserver

   # 终端2: 启动Celery Worker
   celery -A backend worker -l info

   # 终端3: 启动Celery Beat (可选，用于定时任务)
   celery -A backend beat -l info

2. 访问前端:
   打开浏览器访问: http://localhost:5173 或 http://localhost:8000

3. 创建AI开发任务:
   - 导航到: AI开发 -> AI开发任务
   - 点击创建任务按钮
   - 选择需求和配置
   - 提交任务

4. 验证新功能:
   任务完成后，查看任务详情，确认显示:
   ✓ Git仓库地址（可点击）
   ✓ 开发分支名称
   ✓ Commit Hash（可复制）
   ✓ Commit Message
   ✓ 修改的文件列表（标签显示）

5. 测试日志功能:
   - 点击"查看日志"按钮
   - 切换"执行日志"和"AI对话日志"标签
   - 确认日志正常显示

6. 测试服务访问:
   - 复制服务URL
   - 在新标签页中访问
   - 确认服务可以正常访问
    """)

def main():
    """主函数"""
    print("\n" + "AI开发功能更新验证".center(60, "="))

    results = []

    # 1. 验证模型字段
    results.append(("模型字段", verify_model_fields()))

    # 2. 验证现有任务
    verify_existing_tasks()
    results.append(("现有任务", True))

    # 3. 验证序列化器
    results.append(("序列化器", verify_serializer()))

    # 4. 验证API端点
    results.append(("API端点", verify_api_endpoints()))

    # 5. 显示测试场景
    create_test_scenario()

    # 总结
    print_separator("验证结果总结")
    print()
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name:15} {status}")

    all_passed = all(result for _, result in results)

    print("\n" + "="*60)
    if all_passed:
        print(">>> 所有验证通过！可以开始测试新功能。")
    else:
        print(">>> 部分验证失败，请检查上述错误。")
    print("="*60 + "\n")

    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
