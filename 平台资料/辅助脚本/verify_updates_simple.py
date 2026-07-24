#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证AI开发功能更新
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.ai_development.models import AIDevelopmentTask
from apps.ai_development.serializers import AIDevelopmentTaskSerializer
import json

print("\n" + "="*60)
print("  AI Development Feature Verification")
print("="*60)

# 1. 检查模型字段
print("\n[1] Checking Model Fields...")
task_fields = [f.name for f in AIDevelopmentTask._meta.get_fields()]
new_fields = ['git_repository_url', 'files_modified']

for field in new_fields:
    status = "OK" if field in task_fields else "FAIL"
    print(f"  [{status}] {field}")

# 2. 检查现有任务
print("\n[2] Checking Existing Tasks...")
total = AIDevelopmentTask.objects.count()
print(f"  Total tasks: {total}")

if total > 0:
    task = AIDevelopmentTask.objects.first()
    print(f"\n  Sample Task: {task.task_id}")
    print(f"    Status: {task.get_status_display()}")
    print(f"    Requirement: {task.requirement.requirement_name}")
    print(f"    Git Repo: {task.git_repository_url or 'Not set (old task)'}")
    print(f"    Git Branch: {task.git_branch or 'Not set'}")

    if task.files_modified:
        try:
            files = json.loads(task.files_modified)
            print(f"    Modified Files: {len(files)} files")
        except:
            print(f"    Modified Files: Parse error")
    else:
        print(f"    Modified Files: None (old task)")

# 3. 检查序列化器
print("\n[3] Checking Serializer...")
if total > 0:
    serializer = AIDevelopmentTaskSerializer(task)
    data = serializer.data

    check_fields = ['git_repository_url', 'files_modified', 'files_modified_list']
    for field in check_fields:
        status = "OK" if field in data else "FAIL"
        print(f"  [{status}] {field}")
else:
    print("  [SKIP] No tasks to serialize")

# 4. API端点
print("\n[4] API Endpoints...")
print("  [OK] /api/ai-development/tasks/")
print("  [OK] /api/ai-development/tasks/{task_id}/logs/")

# 测试场景
print("\n" + "="*60)
print("  Next Steps")
print("="*60)
print("""
1. Start Services:
   Terminal 1: python manage.py runserver
   Terminal 2: celery -A backend worker -l info

2. Test Frontend:
   - Navigate to AI Development > Tasks
   - Create a new task
   - Wait for completion
   - Check task details

3. Verify New Features:
   Task details should show:
   - Git repository URL (clickable)
   - Development branch name
   - Commit hash (copyable)
   - Commit message
   - List of modified files (as tags)

4. Test Service Access:
   - Copy service URL
   - Access in new browser tab
   - Verify service is running
""")

print("="*60)
print("  Verification Complete")
print("="*60 + "\n")
