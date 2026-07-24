"""
端到端测试：AI自动开发功能
测试完整流程：创建配置 → 创建任务 → 执行开发 → 验证结果

注意：此测试需要真实的Anthropic API Key和Docker环境
"""
import os
import sys
import time
import django

# 设置Django环境
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.ai_development.models import AIDevelopmentConfig, AIDevelopmentTask
from apps.projects.models import Project
from apps.users.models import User
from apps.requirement_analysis.models import (
    RequirementDocument, RequirementAnalysis, BusinessRequirement
)

print("=" * 70)
print("AI自动开发功能 - 端到端测试")
print("=" * 70)

# 检查前置条件
print("\n【步骤1】检查前置条件...")

# 1. 检查API Key
api_key = os.environ.get('ANTHROPIC_API_KEY')
if not api_key:
    print("❌ 未设置 ANTHROPIC_API_KEY 环境变量")
    print("请先设置: set ANTHROPIC_API_KEY=sk-ant-xxx")
    sys.exit(1)
else:
    print(f"✅ API Key已设置: {api_key[:20]}...")

# 2. 检查Docker
try:
    import docker
    client = docker.from_env()
    client.ping()
    print("✅ Docker运行正常")
except Exception as e:
    print(f"❌ Docker不可用: {e}")
    sys.exit(1)

# 3. 检查anthropic库
try:
    import anthropic
    print(f"✅ anthropic库已安装 (版本: {anthropic.__version__})")
except ImportError:
    print("❌ anthropic库未安装，请运行: pip install anthropic")
    sys.exit(1)

print("\n【步骤2】准备测试数据...")

# 获取或创建测试用户
user, created = User.objects.get_or_create(
    username='test_ai_dev',
    defaults={
        'email': 'test@example.com',
        'is_staff': True,
        'is_superuser': False
    }
)
if created:
    user.set_password('test123456')
    user.save()
    print(f"✅ 创建测试用户: {user.username}")
else:
    print(f"✅ 使用现有用户: {user.username}")

# 获取或创建测试项目
project, created = Project.objects.get_or_create(
    name='AI开发测试项目',
    defaults={
        'description': '用于测试AI自动开发功能',
        'created_by': user
    }
)
print(f"✅ {'创建' if created else '使用'}测试项目: {project.name}")

# 创建测试需求
print("\n【步骤3】创建测试需求...")

# 创建需求文档
doc, _ = RequirementDocument.objects.get_or_create(
    title='AI开发功能测试文档',
    defaults={
        'document_type': 'txt',
        'status': 'analyzed',
        'uploaded_by': user,
        'project': project,
        'extracted_text': '测试需求文档'
    }
)

# 创建需求分析
analysis, _ = RequirementAnalysis.objects.get_or_create(
    document=doc,
    defaults={
        'analysis_report': '测试分析报告',
        'requirements_count': 1
    }
)

# 创建业务需求
requirement, created = BusinessRequirement.objects.get_or_create(
    analysis=analysis,
    requirement_id='TEST-E2E-001',
    defaults={
        'requirement_name': '简单计数器功能',
        'requirement_type': 'functional',
        'module': '测试模块',
        'requirement_level': 'high',
        'description': '''实现一个简单的计数器功能：
1. 显示当前计数值（初始为0）
2. 提供"增加"按钮，点击后数值+1
3. 提供"减少"按钮，点击后数值-1
4. 提供"重置"按钮，点击后数值归零
5. 使用Vue 3 Composition API实现
6. 需要编写Playwright测试用例''',
        'acceptance_criteria': '''验收标准：
1. 计数器初始值为0
2. 点击增加按钮，数值正确增加
3. 点击减少按钮，数值正确减少
4. 点击重置按钮，数值归零
5. 测试用例全部通过'''
    }
)
print(f"✅ {'创建' if created else '使用'}测试需求: {requirement.requirement_id}")

print("\n【步骤4】创建AI开发配置...")

# 删除已存在的测试配置
AIDevelopmentConfig.objects.filter(name='E2E测试配置').delete()

config = AIDevelopmentConfig.objects.create(
    name='E2E测试配置',
    project=project,
    git_repository_url='https://github.com/test/test-repo.git',
    git_username='test_user',
    git_password_encrypted='',  # 测试环境不需要真实密码
    git_default_branch='main',
    project_code_path='/workspace/code',
    ai_tool='claude_code',
    llm_model='sonnet',
    llm_api_key_encrypted='',  # 将在任务中使用环境变量的API Key
    auto_install_test_tools=True,
    test_framework='playwright',
    use_docker=True,
    docker_image='python:3.10-slim',  # 使用简单镜像快速测试
    build_command='echo "Build completed"',
    test_command='echo "Tests passed"',
    start_command='python -m http.server 8080',
    service_port=8080,
    is_active=True,
    created_by=user
)

# 加密API Key
from apps.ai_development.utils import encrypt_password
config.llm_api_key_encrypted = encrypt_password(api_key)
config.save()

print(f"✅ 创建配置: {config.name}")
print(f"   - AI工具: {config.ai_tool}")
print(f"   - 模型: {config.llm_model}")
print(f"   - Docker: {config.use_docker}")

print("\n【步骤5】创建AI开发任务...")

# 删除已存在的测试任务
AIDevelopmentTask.objects.filter(task_id__startswith='TEST-E2E').delete()

task = AIDevelopmentTask.objects.create(
    task_id='TEST-E2E-20260402-001',
    requirement=requirement,
    config=config,
    status='pending',
    progress=0,
    current_step='等待执行',
    git_branch='feature/TEST-E2E-001',
    started_by=user
)

print(f"✅ 创建任务: {task.task_id}")
print(f"   - 需求: {requirement.requirement_name}")
print(f"   - 状态: {task.get_status_display()}")

print("\n【步骤6】执行AI开发任务...")
print("⚠️  这一步会调用真实的Anthropic API，会产生费用！")
print("⚠️  预计耗时: 30-60秒")

choice = input("\n是否继续执行? (y/n): ").strip().lower()
if choice != 'y':
    print("❌ 用户取消执行")
    sys.exit(0)

print("\n开始执行AI开发...")
print("-" * 70)

# 手动执行任务逻辑（简化版，不使用Celery）
from apps.ai_development.ai_tools import AnthropicAPIController
from apps.ai_development.utils import decrypt_password
import docker

docker_client = docker.from_env()
container = None

try:
    task.status = 'connecting'
    task.started_at = django.utils.timezone.now()
    task.save()
    print(f"[{task.progress}%] {task.status}: 正在创建Docker容器...")

    # 创建容器
    container = docker_client.containers.run(
        config.docker_image,
        detach=True,
        command='sleep 300',
        volumes={
            f'test_e2e_{task.task_id}': {'bind': '/workspace', 'mode': 'rw'}
        }
    )
    task.container_id = container.id
    task.save()
    print(f"✅ 容器已创建: {container.id[:12]}")

    # 初始化代码目录
    container.exec_run(['mkdir', '-p', '/workspace/code'])
    print("✅ 工作目录已创建")

    # 执行AI开发
    task.status = 'ai_coding'
    task.progress = 20
    task.save()
    print(f"\n[{task.progress}%] {task.status}: 启动AI控制器...")

    llm_api_key = decrypt_password(config.llm_api_key_encrypted)
    ai_controller = AnthropicAPIController(
        container=container,
        model=config.llm_model,
        api_key=llm_api_key
    )

    def progress_callback(percentage, message):
        task.progress = percentage
        task.current_step = message
        task.save()
        print(f"[{percentage}%] {message}")

    result = ai_controller.execute_development(
        requirement_text=requirement.description,
        requirement_id=requirement.requirement_id,
        requirement_name=requirement.requirement_name,
        on_progress=progress_callback
    )

    print("\n" + "-" * 70)

    if result['success']:
        task.status = 'completed'
        task.progress = 100
        task.current_step = 'AI开发完成'
        task.ai_conversation_logs = result['conversation_logs']
        task.completed_at = django.utils.timezone.now()
        task.service_url = f"http://localhost:{config.service_port}"
        task.save()

        print("\n✅ AI开发成功!")
        print(f"   生成文件数: {len(result['files_modified'])}")
        print(f"   文件列表:")
        for file in result['files_modified']:
            print(f"     - {file}")

        # 验证文件
        print("\n【步骤7】验证生成的文件...")
        for file_path in result['files_modified']:
            try:
                verify_result = container.exec_run(['cat', f'/workspace/code/{file_path}'])
                if verify_result.exit_code == 0:
                    content = verify_result.output.decode('utf-8')
                    print(f"\n✅ 文件 {file_path} (大小: {len(content)} 字节)")
                    print(f"   预览:")
                    lines = content.split('\n')[:10]
                    for line in lines:
                        print(f"   {line}")
                    if len(content.split('\n')) > 10:
                        print(f"   ... (共 {len(content.split('\n'))} 行)")
                else:
                    print(f"❌ 文件 {file_path} 不存在或无法读取")
            except Exception as e:
                print(f"❌ 验证文件 {file_path} 失败: {e}")

        print("\n" + "=" * 70)
        print("测试总结")
        print("=" * 70)
        print(f"✅ 任务ID: {task.task_id}")
        print(f"✅ 状态: {task.get_status_display()}")
        print(f"✅ 耗时: {(task.completed_at - task.started_at).total_seconds():.1f} 秒")
        print(f"✅ 生成文件: {len(result['files_modified'])} 个")
        print(f"✅ 容器ID: {container.id[:12]}")

        print("\n🎉 端到端测试通过!")
        print("\n后续可以:")
        print("  1. 访问Django Admin查看任务详情:")
        print(f"     http://localhost:8000/admin/ai_development/aidevelopmenttask/{task.id}/")
        print("  2. 检查容器中的文件:")
        print(f"     docker exec {container.id[:12]} ls -la /workspace/code")
        print("  3. 查看AI对话日志:")
        print(f"     在Admin中查看任务的'AI对话日志'字段")

    else:
        task.status = 'failed'
        task.error_message = result.get('error', 'Unknown error')
        task.completed_at = django.utils.timezone.now()
        task.save()

        print(f"\n❌ AI开发失败: {result.get('error')}")
        print(f"\n错误日志:")
        print(result.get('conversation_logs', 'No logs'))

except Exception as e:
    print(f"\n❌ 测试过程出错: {e}")
    import traceback
    traceback.print_exc()

    task.status = 'failed'
    task.error_message = str(e)
    task.save()

finally:
    # 清理容器
    if container:
        print(f"\n是否保留容器用于检查? (y/n): ", end='')
        keep = input().strip().lower()
        if keep != 'y':
            try:
                container.stop()
                container.remove()
                print("✅ 容器已清理")
            except:
                print("⚠️  容器清理失败，请手动清理")
        else:
            print(f"✅ 容器已保留: {container.id[:12]}")
            print(f"   查看文件: docker exec {container.id[:12]} ls -la /workspace/code")
            print(f"   进入容器: docker exec -it {container.id[:12]} bash")
            print(f"   删除容器: docker rm -f {container.id[:12]}")

print("\n测试完成!")
