# AI自动编码功能技术方案设计

## 一、需求概述

实现全链路自动化中的第2步"根据需求调用AI编码",在需求分析页面调起AI编码工具(Claude Code/Codex CLI),自动完成:
1. 拉取代码 → 2. AI开发 → 3. 本地构建 → 4. 自测试 → 5. 提交代码 → 6. 启动服务 → 7. 返回服务地址

整个过程需要实时更新状态到需求列表。

---

## 二、核心技术难点分析

### 2.1 交互式CLI工具控制

**问题**: Claude Code和Codex CLI都是交互式命令行工具,需要在后端程序中控制其会话。

**技术方案对比**:

| 方案 | 技术栈 | 优势 | 劣势 | 推荐度 |
|------|--------|------|------|--------|
| **方案A: pexpect控制伪终端** | Python pexpect | • 完全控制交互式会话<br>• 可捕获所有输出<br>• 支持复杂交互 | • Windows支持不好(需winpty)<br>• 需要精确匹配prompt | ⭐⭐⭐⭐ |
| **方案B: Claude Code API** | 官方API(如存在) | • 稳定可靠<br>• 无需控制终端 | • Claude Code目前无官方API<br>• 需调研是否有headless模式 | ⭐⭐ |
| **方案C: subprocess + 输入重定向** | Python subprocess | • 简单易实现 | • 无法处理复杂交互<br>• 难以实时获取输出 | ⭐⭐ |
| **方案D: WebSocket代理模式** | Flask-SocketIO/Django Channels | • 用户可参与交互<br>• 实时性好 | • 半自动化(问答模式)<br>• 实现复杂 | ⭐⭐⭐ |

**推荐方案**: **方案A (pexpect) + 方案D (WebSocket) 混合模式**
- 完全授权模式: 使用pexpect自动化控制
- 问答模式: 使用WebSocket流式传输,用户参与决策

### 2.2 环境隔离与执行

**问题**: 多用户并发开发,需要隔离环境避免冲突和安全风险。

**技术方案对比**:

| 方案 | 隔离级别 | 资源消耗 | 安全性 | 复杂度 | 推荐度 |
|------|----------|----------|--------|--------|--------|
| **方案A: Docker容器** | 进程+网络+文件系统 | 中等 | 高 | 中等 | ⭐⭐⭐⭐⭐ |
| **方案B: Python虚拟环境** | Python包 | 低 | 低 | 低 | ⭐⭐ |
| **方案C: 独立VM** | 操作系统级 | 高 | 最高 | 高 | ⭐⭐⭐ |
| **方案D: Kubernetes Job** | 容器编排 | 中等 | 高 | 高 | ⭐⭐⭐⭐ |

**推荐方案**: **方案A (Docker容器)**

**Docker方案设计**:
```dockerfile
# 基础镜像
FROM python:3.10-slim

# 安装必要工具
RUN apt-get update && apt-get install -y \
    git \
    nodejs \
    npm \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 安装Claude Code CLI
RUN npm install -g @anthropic/claude-code

# 安装Playwright/Selenium
RUN pip install playwright selenium && \
    playwright install chromium

# 工作目录
WORKDIR /workspace

# 配置git
RUN git config --global user.name "AI Developer" && \
    git config --global user.email "ai@testhub.com"

# 入口脚本
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

**容器执行流程**:
1. 为每个开发任务动态创建容器
2. 挂载代码卷 + 配置卷
3. 执行开发任务
4. 保留容器日志用于审计
5. 任务完成后清理容器(可选保留用于调试)

### 2.3 任务调度与并发控制

**问题**: 多用户同时发起开发需求,如何调度和限流?

**技术方案对比**:

| 方案 | 并发控制 | 任务队列 | 分布式支持 | 推荐度 |
|------|----------|----------|------------|--------|
| **方案A: Celery + Redis** | 队列限流 | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| **方案B: Django-Q** | 进程池 | ✅ | ❌ | ⭐⭐⭐ |
| **方案C: Kubernetes CronJob/Job** | Pod限制 | ✅ | ✅ | ⭐⭐⭐⭐ |
| **方案D: 自定义线程池** | Semaphore | ❌ | ❌ | ⭐⭐ |

**推荐方案**: **方案A (Celery + Redis + Docker)**

**调度策略**:
```python
# Celery配置
CELERY_TASK_ROUTES = {
    'apps.ai_development.tasks.execute_ai_coding': {
        'queue': 'ai_coding',
        'routing_key': 'ai_coding',
    }
}

# 并发控制
CELERYD_CONCURRENCY = 3  # 同时最多3个AI编码任务
CELERY_TASK_TIME_LIMIT = 3600  # 单任务最长1小时
CELERY_TASK_SOFT_TIME_LIMIT = 3300  # 软限制55分钟

# 优先级队列
CELERY_TASK_QUEUE_MAX_PRIORITY = 10
```

**任务优先级规则**:
- P0需求: 优先级10 (最高)
- P1需求: 优先级7
- P2需求: 优先级5
- P3需求: 优先级3

### 2.4 状态实时同步

**问题**: AI开发过程漫长(可能10-30分钟),如何实时同步状态到前端?

**技术方案对比**:

| 方案 | 实时性 | 服务器压力 | 实现复杂度 | 推荐度 |
|------|--------|------------|------------|--------|
| **方案A: WebSocket** | 实时 | 需维护连接 | 中等 | ⭐⭐⭐⭐⭐ |
| **方案B: SSE (Server-Sent Events)** | 准实时 | 较低 | 低 | ⭐⭐⭐⭐ |
| **方案C: 轮询** | 延迟3-5秒 | 高 | 低 | ⭐⭐⭐ |
| **方案D: 长轮询** | 准实时 | 中等 | 中等 | ⭐⭐⭐ |

**推荐方案**: **方案A (WebSocket) + 方案C (轮询) 降级**
- 首选WebSocket (Django Channels)
- 不支持WebSocket时降级为轮询

**状态更新节点** (每个节点都推送到前端):
1. ✅ 任务已创建
2. 🔌 正在连接服务器...
3. 📁 正在克隆代码仓库...
4. 🤖 正在启动AI编码工具...
5. 💡 AI正在分析需求...
6. ⚙️ AI正在编写代码...
7. 🔨 正在本地构建...
8. 🧪 正在执行自动化测试...
9. ✅ 测试通过,正在提交代码...
10. 🚀 正在启动服务...
11. 🎉 开发完成!

---

## 三、数据库模型设计

### 3.1 AI开发配置表 (AIDevelopmentConfig)

```python
class AIDevelopmentConfig(models.Model):
    """AI开发配置"""
    # 基本信息
    name = models.CharField(max_length=200, verbose_name='配置名称')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='ai_dev_configs', verbose_name='关联项目')

    # Git配置
    git_provider = models.CharField(
        max_length=20,
        choices=[('gitlab', 'GitLab'), ('github', 'GitHub'), ('gitee', 'Gitee'), ('custom', '自定义')],
        verbose_name='Git平台'
    )
    git_base_url = models.URLField(verbose_name='Git平台地址', help_text='如: https://gitlab.com')
    git_username = models.CharField(max_length=100, verbose_name='Git用户名')
    git_password_encrypted = models.CharField(max_length=500, verbose_name='Git密码(加密存储)')
    git_repository_url = models.URLField(verbose_name='仓库地址')
    git_default_branch = models.CharField(max_length=100, default='main', verbose_name='默认分支')

    # 服务器配置
    execution_mode = models.CharField(
        max_length=20,
        choices=[('local', '平台所在服务器'), ('remote', '远程服务器')],
        default='local',
        verbose_name='执行模式'
    )
    remote_host = models.CharField(max_length=255, blank=True, null=True, verbose_name='远程服务器IP')
    remote_port = models.IntegerField(default=22, blank=True, null=True, verbose_name='SSH端口')
    remote_username = models.CharField(max_length=100, blank=True, null=True, verbose_name='SSH用户名')
    remote_password_encrypted = models.CharField(max_length=500, blank=True, null=True, verbose_name='SSH密码(加密)')

    # 项目路径配置
    project_code_path = models.CharField(max_length=500, verbose_name='项目代码路径', help_text='如: /home/projects/myapp')

    # AI编码工具配置
    ai_tool = models.CharField(
        max_length=20,
        choices=[('claude_code', 'Claude Code'), ('codex_cli', 'Codex CLI')],
        default='claude_code',
        verbose_name='AI编码工具'
    )
    authorization_mode = models.CharField(
        max_length=20,
        choices=[('full_auto', '完全授权'), ('interactive', '问答模式')],
        default='full_auto',
        verbose_name='授权模式'
    )

    # 大模型配置
    llm_model = models.CharField(
        max_length=50,
        verbose_name='大模型',
        help_text='Claude Code: sonnet/opus/haiku; Codex CLI: gpt-5.4-xhigh'
    )
    llm_api_key_encrypted = models.CharField(max_length=500, verbose_name='模型API Key(加密)', blank=True, null=True)

    # 测试工具配置
    auto_install_test_tools = models.BooleanField(default=True, verbose_name='自动安装测试工具')
    test_framework = models.CharField(
        max_length=20,
        choices=[('playwright', 'Playwright'), ('selenium', 'Selenium'), ('both', '两者都安装')],
        default='playwright',
        verbose_name='测试框架'
    )

    # 环境配置
    use_docker = models.BooleanField(default=True, verbose_name='使用Docker隔离')
    docker_image = models.CharField(max_length=200, default='testhub/ai-dev:latest', verbose_name='Docker镜像')
    environment_variables = models.JSONField(default=dict, blank=True, verbose_name='环境变量')

    # 构建配置
    build_command = models.TextField(blank=True, verbose_name='构建命令', help_text='如: npm run build')
    test_command = models.TextField(blank=True, verbose_name='测试命令', help_text='如: npm test')
    start_command = models.TextField(blank=True, verbose_name='启动命令', help_text='如: npm run serve')
    service_port = models.IntegerField(default=8080, verbose_name='服务端口')

    # 元数据
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ai_development_config'
        verbose_name = 'AI开发配置'
        verbose_name_plural = 'AI开发配置'
```

### 3.2 AI开发任务表 (AIDevelopmentTask)

```python
class AIDevelopmentTask(models.Model):
    """AI开发任务"""
    TASK_STATUS_CHOICES = [
        ('pending', '待处理'),
        ('queued', '已排队'),
        ('connecting', '连接服务器中'),
        ('cloning', '克隆代码中'),
        ('starting_ai', '启动AI工具中'),
        ('ai_analyzing', 'AI分析需求中'),
        ('ai_coding', 'AI编码中'),
        ('building', '构建中'),
        ('testing', '测试中'),
        ('committing', '提交代码中'),
        ('starting_service', '启动服务中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
    ]

    # 基本信息
    task_id = models.CharField(max_length=100, unique=True, verbose_name='任务ID')
    requirement = models.ForeignKey(
        'requirement_analysis.BusinessRequirement',
        on_delete=models.CASCADE,
        related_name='ai_dev_tasks',
        verbose_name='关联需求'
    )
    config = models.ForeignKey(AIDevelopmentConfig, on_delete=models.PROTECT, verbose_name='开发配置')

    # 状态信息
    status = models.CharField(max_length=30, choices=TASK_STATUS_CHOICES, default='pending', verbose_name='状态')
    progress = models.IntegerField(default=0, verbose_name='进度百分比')
    current_step = models.CharField(max_length=200, blank=True, verbose_name='当前步骤')

    # Git信息
    git_branch = models.CharField(max_length=200, blank=True, verbose_name='开发分支')
    git_commit_hash = models.CharField(max_length=40, blank=True, verbose_name='提交哈希')
    git_commit_message = models.TextField(blank=True, verbose_name='提交信息')

    # 执行信息
    container_id = models.CharField(max_length=64, blank=True, verbose_name='容器ID')
    execution_logs = models.TextField(blank=True, verbose_name='执行日志')
    ai_conversation_logs = models.TextField(blank=True, verbose_name='AI对话日志')

    # 测试信息
    build_success = models.BooleanField(null=True, verbose_name='构建是否成功')
    build_output = models.TextField(blank=True, verbose_name='构建输出')
    test_success = models.BooleanField(null=True, verbose_name='测试是否成功')
    test_output = models.TextField(blank=True, verbose_name='测试输出')
    test_report_url = models.URLField(blank=True, null=True, verbose_name='测试报告URL')

    # 服务信息
    service_url = models.URLField(blank=True, null=True, verbose_name='服务地址')
    service_username = models.CharField(max_length=100, blank=True, verbose_name='服务账号')
    service_password = models.CharField(max_length=100, blank=True, verbose_name='服务密码')
    service_pid = models.IntegerField(null=True, verbose_name='服务进程ID')

    # 错误信息
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    error_stack = models.TextField(blank=True, verbose_name='错误堆栈')

    # 元数据
    started_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='发起人')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    # Celery任务ID
    celery_task_id = models.CharField(max_length=100, blank=True, verbose_name='Celery任务ID')

    class Meta:
        db_table = 'ai_development_task'
        verbose_name = 'AI开发任务'
        verbose_name_plural = 'AI开发任务'
        ordering = ['-created_at']
```

### 3.3 Git仓库配置表 (GitRepositoryConfig)

```python
class GitRepositoryConfig(models.Model):
    """Git仓库配置(支持自动发现)"""
    config = models.ForeignKey(AIDevelopmentConfig, on_delete=models.CASCADE, related_name='repositories')
    repository_name = models.CharField(max_length=200, verbose_name='仓库名称')
    repository_url = models.URLField(verbose_name='仓库URL')
    default_branch = models.CharField(max_length=100, default='main', verbose_name='默认分支')
    description = models.TextField(blank=True, verbose_name='仓库描述')
    is_discovered = models.BooleanField(default=False, verbose_name='是否自动发现')
    last_sync_at = models.DateTimeField(null=True, blank=True, verbose_name='最后同步时间')

    class Meta:
        db_table = 'git_repository_config'
        unique_together = ['config', 'repository_url']
```

---

## 四、API接口设计

### 4.1 配置管理接口

```python
# GET /api/ai-development/configs/
# 列出所有配置

# POST /api/ai-development/configs/
# 创建配置
{
    "name": "前端项目AI开发配置",
    "project": 1,
    "git_provider": "gitlab",
    "git_base_url": "https://gitlab.company.com",
    "git_username": "developer",
    "git_password": "password123",  # 后端自动加密
    "execution_mode": "remote",
    "remote_host": "192.168.1.100",
    "remote_port": 22,
    "remote_username": "ubuntu",
    "remote_password": "server_password",
    "project_code_path": "/home/ubuntu/projects/frontend",
    "ai_tool": "claude_code",
    "authorization_mode": "full_auto",
    "llm_model": "sonnet",
    "use_docker": true,
    "build_command": "npm run build",
    "test_command": "npm test",
    "start_command": "npm run dev",
    "service_port": 5173
}

# GET /api/ai-development/configs/{id}/
# 获取配置详情

# PUT /api/ai-development/configs/{id}/
# 更新配置

# DELETE /api/ai-development/configs/{id}/
# 删除配置

# POST /api/ai-development/configs/{id}/test_connection/
# 测试连接(Git + SSH)
```

### 4.2 仓库发现接口

```python
# POST /api/ai-development/configs/{id}/discover_repositories/
# 自动发现Git账号下的所有仓库
{
    "sync_all": true  # 是否同步所有仓库
}

# Response:
{
    "discovered_count": 15,
    "repositories": [
        {
            "name": "frontend-app",
            "url": "https://gitlab.company.com/team/frontend-app.git",
            "default_branch": "main",
            "description": "前端应用"
        },
        ...
    ]
}
```

### 4.3 开发任务接口

```python
# POST /api/ai-development/tasks/create/
# 创建AI开发任务
{
    "requirement_id": 123,  # 需求ID
    "config_id": 1,  # 使用的配置
    "git_branch_name": "feature/REQ-123",  # 可选,默认自动生成
    "code_version": "v1.2.0"  # 要拉取的代码版本
}

# Response:
{
    "task_id": "AIDEV-20260402-001",
    "status": "queued",
    "queue_position": 2,  # 队列位置
    "estimated_start_time": "2026-04-02T14:30:00Z"
}

# GET /api/ai-development/tasks/{task_id}/
# 获取任务详情

# GET /api/ai-development/tasks/{task_id}/progress/
# 获取任务进度(轮询接口)
{
    "task_id": "AIDEV-20260402-001",
    "status": "ai_coding",
    "progress": 45,
    "current_step": "AI正在编写用户登录功能...",
    "logs": "最近的日志输出...",
    "elapsed_time": 320  # 已耗时(秒)
}

# POST /api/ai-development/tasks/{task_id}/cancel/
# 取消任务

# WebSocket /ws/ai-development/tasks/{task_id}/
# WebSocket实时状态推送
```

### 4.4 需求关联接口

```python
# 在需求详情API中添加AI开发相关字段
GET /api/requirement-analysis/api/requirements/{id}/

Response:
{
    "id": 123,
    "requirement_id": "REQ-001",
    "requirement_name": "用户登录功能",
    ...
    "ai_development": {
        "is_configured": true,  # 是否已配置AI开发
        "latest_task": {
            "task_id": "AIDEV-20260402-001",
            "status": "completed",
            "service_url": "http://192.168.1.100:5173",
            "service_username": "admin",
            "service_password": "admin123",
            "completed_at": "2026-04-02T15:30:00Z"
        },
        "all_tasks_count": 3,
        "success_count": 2,
        "failed_count": 1
    }
}

# POST /api/requirement-analysis/api/requirements/{id}/start_ai_development/
# 直接从需求页面发起AI开发
{
    "config_id": 1
}
```

---

## 五、Celery任务实现(核心)

### 5.1 主任务编排

```python
# apps/ai_development/tasks.py
from celery import shared_task, chain, group
from celery.exceptions import SoftTimeLimitExceeded
import docker
import pexpect
from paramiko import SSHClient
from .models import AIDevelopmentTask, AIDevelopmentConfig
from .ai_tools import ClaudeCodeController, CodexCLIController
from .utils import encrypt_password, decrypt_password, send_websocket_update

@shared_task(bind=True, time_limit=3600, soft_time_limit=3300)
def execute_ai_coding(self, task_id):
    """
    执行AI编码主任务
    """
    task = AIDevelopmentTask.objects.get(task_id=task_id)
    config = task.config

    try:
        # 1. 更新状态: 连接服务器
        update_task_status(task, 'connecting', 5, '正在连接服务器...')

        if config.use_docker:
            # Docker模式
            result = execute_in_docker(task, config)
        else:
            # 直接模式
            result = execute_directly(task, config)

        # 9. 更新状态: 完成
        update_task_status(task, 'completed', 100, '开发完成!')
        task.service_url = result['service_url']
        task.service_username = result.get('username', '')
        task.service_password = result.get('password', '')
        task.completed_at = timezone.now()
        task.save()

        return {'success': True, 'task_id': task_id}

    except SoftTimeLimitExceeded:
        update_task_status(task, 'failed', task.progress, '任务超时')
        task.error_message = '任务执行超过时间限制'
        task.save()
        raise

    except Exception as e:
        logger.exception(f"AI开发任务失败: {task_id}")
        update_task_status(task, 'failed', task.progress, f'任务失败: {str(e)}')
        task.error_message = str(e)
        task.error_stack = traceback.format_exc()
        task.save()
        raise


def execute_in_docker(task, config):
    """在Docker容器中执行"""
    client = docker.from_env()

    # 创建容器
    update_task_status(task, 'starting_ai', 10, '正在创建Docker容器...')

    container = client.containers.run(
        image=config.docker_image,
        detach=True,
        remove=False,  # 保留容器用于日志审计
        environment={
            'GIT_URL': config.git_repository_url,
            'GIT_USERNAME': config.git_username,
            'GIT_PASSWORD': decrypt_password(config.git_password_encrypted),
            'GIT_BRANCH': task.git_branch,
            'AI_TOOL': config.ai_tool,
            'LLM_MODEL': config.llm_model,
            'LLM_API_KEY': decrypt_password(config.llm_api_key_encrypted),
            'REQUIREMENT_TEXT': task.requirement.description,
            'AUTHORIZATION_MODE': config.authorization_mode,
            **config.environment_variables
        },
        volumes={
            f'/var/testhub/workspaces/{task.task_id}': {'bind': '/workspace', 'mode': 'rw'}
        },
        ports={
            f'{config.service_port}/tcp': config.service_port
        }
    )

    task.container_id = container.id
    task.save()

    # 2. 克隆代码
    update_task_status(task, 'cloning', 15, '正在克隆代码仓库...')
    exec_in_container(container, f'''
        git clone --depth 1 --branch {config.git_default_branch} \
        https://{config.git_username}:{decrypt_password(config.git_password_encrypted)}@{extract_repo_url(config.git_repository_url)} /workspace/code
        cd /workspace/code
        git checkout -b {task.git_branch}
    ''')

    # 3. 启动AI编码工具
    update_task_status(task, 'starting_ai', 20, f'正在启动 {config.ai_tool}...')

    if config.ai_tool == 'claude_code':
        ai_controller = ClaudeCodeController(
            container=container,
            model=config.llm_model,
            api_key=decrypt_password(config.llm_api_key_encrypted),
            authorization_mode=config.authorization_mode
        )
    else:
        ai_controller = CodexCLIController(
            container=container,
            model=config.llm_model,
            api_key=decrypt_password(config.llm_api_key_encrypted)
        )

    # 4. AI开发
    update_task_status(task, 'ai_coding', 30, 'AI正在分析需求...')

    ai_result = ai_controller.execute_development(
        requirement_text=task.requirement.description,
        requirement_id=task.requirement.requirement_id,
        requirement_name=task.requirement.requirement_name,
        on_progress=lambda step, msg: update_task_status(task, 'ai_coding', 30 + step, msg)
    )

    task.ai_conversation_logs = ai_result['conversation_logs']
    task.save()

    # 5. 构建
    update_task_status(task, 'building', 70, '正在构建项目...')
    build_result = exec_in_container(container, config.build_command or 'echo "No build command"')
    task.build_success = build_result['exit_code'] == 0
    task.build_output = build_result['output']
    task.save()

    if not task.build_success:
        raise Exception(f"构建失败:\n{build_result['output']}")

    # 6. 测试
    update_task_status(task, 'testing', 80, '正在执行自动化测试...')
    test_result = exec_in_container(container, config.test_command or 'echo "No test command"')
    task.test_success = test_result['exit_code'] == 0
    task.test_output = test_result['output']
    task.save()

    if not task.test_success:
        raise Exception(f"测试失败:\n{test_result['output']}")

    # 7. 提交代码
    update_task_status(task, 'committing', 90, '正在提交代码到Git仓库...')
    commit_message = f'''feat: {task.requirement.requirement_name}

需求编号: {task.requirement.requirement_id}
需求名称: {task.requirement.requirement_name}

由AI自动开发完成
'''

    commit_result = exec_in_container(container, f'''
        cd /workspace/code
        git add .
        git commit -m "{commit_message}"
        git push origin {task.git_branch}
    ''')

    # 提取commit hash
    task.git_commit_hash = extract_commit_hash(commit_result['output'])
    task.git_commit_message = commit_message
    task.save()

    # 8. 启动服务
    update_task_status(task, 'starting_service', 95, '正在启动服务...')
    service_result = exec_in_container_background(container, config.start_command or 'echo "No start command"')
    task.service_pid = service_result['pid']
    task.save()

    # 等待服务启动
    import time
    time.sleep(5)

    # 获取服务URL
    host_ip = get_docker_host_ip()
    service_url = f"http://{host_ip}:{config.service_port}"

    return {
        'service_url': service_url,
        'username': 'admin',  # 可从配置或AI返回中提取
        'password': 'admin123'
    }
```

### 5.2 AI工具控制器

```python
# apps/ai_development/ai_tools/claude_code_controller.py
import pexpect
import time

class ClaudeCodeController:
    """Claude Code控制器"""

    def __init__(self, container, model, api_key, authorization_mode='full_auto'):
        self.container = container
        self.model = model
        self.api_key = api_key
        self.authorization_mode = authorization_mode
        self.conversation_logs = []

    def execute_development(self, requirement_text, requirement_id, requirement_name, on_progress=None):
        """执行开发"""

        # 在容器中启动Claude Code
        if on_progress:
            on_progress(5, '正在启动Claude Code...')

        # 使用pexpect控制Claude Code(通过docker exec)
        child = pexpect.spawn(
            f'docker exec -it {self.container.id} claude-code',
            encoding='utf-8',
            timeout=1800  # 30分钟超时
        )

        try:
            # 等待Claude Code启动
            child.expect('Welcome to Claude Code', timeout=30)
            self.log_output(child.before)

            # 切换模型
            if on_progress:
                on_progress(10, f'正在切换到 {self.model} 模型...')

            child.sendline(f'/model {self.model}')
            child.expect('Model switched to', timeout=10)
            self.log_output(child.before)

            # 设置授权模式
            if self.authorization_mode == 'full_auto':
                child.sendline('/non-interactive')
                child.expect('Non-interactive mode enabled', timeout=10)

            # 发送开发指令
            if on_progress:
                on_progress(15, 'AI正在分析需求...')

            prompt = f"""
我需要你根据以下需求进行开发:

需求编号: {requirement_id}
需求名称: {requirement_name}

详细需求:
{requirement_text}

请按照以下步骤完成开发:
1. 分析需求,理解功能点
2. 设计技术方案
3. 编写代码实现
4. 本地构建并确保没有错误
5. 使用playwright/selenium编写自动化测试用例
6. 运行测试确保全部通过

完成后请告诉我:
- 实现了哪些功能
- 修改了哪些文件
- 测试结果如何
"""

            child.sendline(prompt)

            # 监控AI输出
            step_count = 15
            while True:
                try:
                    index = child.expect([
                        'Analyzing',
                        'Writing code',
                        'Building',
                        'Testing',
                        'All tests passed',
                        'Error:',
                        'Done',
                        pexpect.TIMEOUT,
                        pexpect.EOF
                    ], timeout=60)

                    output = child.before + child.after
                    self.log_output(output)

                    if index == 0:  # Analyzing
                        if on_progress:
                            on_progress(20, 'AI正在分析需求...')
                    elif index == 1:  # Writing code
                        step_count = min(step_count + 5, 60)
                        if on_progress:
                            on_progress(step_count, 'AI正在编写代码...')
                    elif index == 2:  # Building
                        if on_progress:
                            on_progress(65, 'AI正在构建项目...')
                    elif index == 3:  # Testing
                        if on_progress:
                            on_progress(70, 'AI正在运行测试...')
                    elif index == 4:  # All tests passed
                        if on_progress:
                            on_progress(85, '所有测试通过!')
                        break
                    elif index == 5:  # Error
                        error_msg = child.before
                        raise Exception(f"AI执行出错: {error_msg}")
                    elif index == 6:  # Done
                        break
                    elif index in [7, 8]:  # Timeout or EOF
                        break

                except pexpect.TIMEOUT:
                    # 继续等待
                    continue

            # 退出Claude Code
            child.sendline('/exit')
            child.expect(pexpect.EOF, timeout=10)

            return {
                'success': True,
                'conversation_logs': '\n'.join(self.conversation_logs)
            }

        finally:
            if child.isalive():
                child.close()

    def log_output(self, output):
        """记录输出"""
        if output:
            self.conversation_logs.append(output)
            logger.info(f"[Claude Code] {output}")
```

---

## 六、前端实现

### 6.1 需求详情页添加AI开发按钮

```vue
<!-- frontend/src/views/requirement-analysis/RequirementDetail.vue -->
<template>
  <div class="requirement-detail">
    <!-- ...现有需求详情内容... -->

    <!-- AI开发区域 -->
    <div class="ai-development-section" v-if="requirement">
      <h3>🤖 AI自动开发</h3>

      <!-- 配置选择 -->
      <div v-if="!currentDevTask || currentDevTask.status === 'completed' || currentDevTask.status === 'failed'">
        <el-select v-model="selectedConfigId" placeholder="选择开发配置">
          <el-option
            v-for="config in devConfigs"
            :key="config.id"
            :label="config.name"
            :value="config.id">
            <span>{{ config.name }}</span>
            <span style="color: #8492a6; font-size: 13px">
              ({{ config.ai_tool }} - {{ config.llm_model }})
            </span>
          </el-option>
        </el-select>

        <el-button
          type="primary"
          @click="startAIDevelopment"
          :disabled="!selectedConfigId"
          icon="el-icon-cpu">
          启动AI开发
        </el-button>

        <el-button
          type="info"
          @click="showConfigDialog = true"
          icon="el-icon-setting">
          配置管理
        </el-button>
      </div>

      <!-- 开发进度 -->
      <div v-if="currentDevTask && currentDevTask.status !== 'completed' && currentDevTask.status !== 'failed'"
           class="dev-progress">
        <h4>{{ getStatusText(currentDevTask.status) }}</h4>

        <el-progress
          :percentage="currentDevTask.progress"
          :status="currentDevTask.status === 'failed' ? 'exception' : undefined">
        </el-progress>

        <div class="current-step">
          {{ currentDevTask.current_step }}
        </div>

        <!-- 实时日志 -->
        <el-collapse v-model="activeCollapse">
          <el-collapse-item title="查看实时日志" name="logs">
            <div class="log-viewer">
              <pre>{{ currentDevTask.execution_logs || '等待日志输出...' }}</pre>
            </div>
          </el-collapse-item>
        </el-collapse>

        <el-button
          type="danger"
          size="small"
          @click="cancelDevelopment">
          取消开发
        </el-button>
      </div>

      <!-- 开发结果 -->
      <div v-if="currentDevTask && currentDevTask.status === 'completed'" class="dev-result success">
        <h4>✅ 开发完成!</h4>

        <div class="result-info">
          <div class="info-item">
            <span class="label">服务地址:</span>
            <a :href="currentDevTask.service_url" target="_blank">
              {{ currentDevTask.service_url }}
            </a>
          </div>
          <div class="info-item">
            <span class="label">账号:</span>
            <span>{{ currentDevTask.service_username }}</span>
          </div>
          <div class="info-item">
            <span class="label">密码:</span>
            <span>{{ currentDevTask.service_password }}</span>
          </div>
          <div class="info-item">
            <span class="label">Git分支:</span>
            <span>{{ currentDevTask.git_branch }}</span>
          </div>
          <div class="info-item">
            <span class="label">Commit:</span>
            <span>{{ currentDevTask.git_commit_hash }}</span>
          </div>
        </div>

        <el-button type="primary" @click="viewTestReport">
          查看测试报告
        </el-button>
        <el-button type="success" @click="viewAILogs">
          查看AI对话日志
        </el-button>
      </div>

      <!-- 失败结果 -->
      <div v-if="currentDevTask && currentDevTask.status === 'failed'" class="dev-result error">
        <h4>❌ 开发失败</h4>
        <div class="error-message">
          {{ currentDevTask.error_message }}
        </div>
        <el-button type="warning" @click="retryDevelopment">
          重试
        </el-button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      requirement: null,
      devConfigs: [],
      selectedConfigId: null,
      currentDevTask: null,
      websocket: null,
      pollInterval: null,
      activeCollapse: []
    }
  },

  mounted() {
    this.loadRequirement()
    this.loadDevConfigs()
  },

  beforeUnmount() {
    this.cleanupPolling()
    this.cleanupWebSocket()
  },

  methods: {
    async loadDevConfigs() {
      const response = await api.get('/ai-development/configs/', {
        params: { project: this.requirement.project }
      })
      this.devConfigs = response.data.results || response.data
    },

    async startAIDevelopment() {
      try {
        const response = await api.post(
          `/requirement-analysis/api/requirements/${this.$route.params.id}/start_ai_development/`,
          { config_id: this.selectedConfigId }
        )

        this.currentDevTask = response.data
        this.$message.success('AI开发任务已启动')

        // 尝试建立WebSocket连接
        this.setupWebSocket(this.currentDevTask.task_id)

        // 备用轮询机制
        this.startPolling()

      } catch (error) {
        this.$message.error('启动失败: ' + (error.response?.data?.error || error.message))
      }
    },

    setupWebSocket(taskId) {
      if (!window.WebSocket) {
        console.warn('浏览器不支持WebSocket,使用轮询模式')
        return
      }

      const wsUrl = `ws://${window.location.host}/ws/ai-development/tasks/${taskId}/`
      this.websocket = new WebSocket(wsUrl)

      this.websocket.onopen = () => {
        console.log('WebSocket连接已建立')
        // WebSocket连接成功,停止轮询
        if (this.pollInterval) {
          clearInterval(this.pollInterval)
          this.pollInterval = null
        }
      }

      this.websocket.onmessage = (event) => {
        const data = JSON.parse(event.data)
        this.currentDevTask = { ...this.currentDevTask, ...data }
      }

      this.websocket.onerror = () => {
        console.warn('WebSocket连接失败,切换到轮询模式')
        this.startPolling()
      }

      this.websocket.onclose = () => {
        console.log('WebSocket连接已关闭')
      }
    },

    startPolling() {
      if (this.pollInterval) return

      this.pollInterval = setInterval(async () => {
        try {
          const response = await api.get(
            `/ai-development/tasks/${this.currentDevTask.task_id}/progress/`
          )
          this.currentDevTask = response.data

          if (['completed', 'failed', 'cancelled'].includes(response.data.status)) {
            this.cleanupPolling()
            this.cleanupWebSocket()
          }
        } catch (error) {
          console.error('轮询任务状态失败:', error)
        }
      }, 3000)
    },

    cleanupPolling() {
      if (this.pollInterval) {
        clearInterval(this.pollInterval)
        this.pollInterval = null
      }
    },

    cleanupWebSocket() {
      if (this.websocket) {
        this.websocket.close()
        this.websocket = null
      }
    },

    getStatusText(status) {
      const statusMap = {
        'pending': '待处理',
        'queued': '已排队',
        'connecting': '连接服务器中',
        'cloning': '克隆代码中',
        'starting_ai': '启动AI工具中',
        'ai_analyzing': 'AI分析需求中',
        'ai_coding': 'AI编码中',
        'building': '构建中',
        'testing': '测试中',
        'committing': '提交代码中',
        'starting_service': '启动服务中',
        'completed': '已完成',
        'failed': '失败',
        'cancelled': '已取消'
      }
      return statusMap[status] || status
    }
  }
}
</script>
```

---

## 七、安全性设计

### 7.1 凭证加密存储

```python
# apps/ai_development/utils/encryption.py
from cryptography.fernet import Fernet
from django.conf import settings
import base64

# 从环境变量获取加密密钥
ENCRYPTION_KEY = settings.AI_DEV_ENCRYPTION_KEY  # 需在.env中配置

def encrypt_password(plain_text: str) -> str:
    """加密密码"""
    if not plain_text:
        return ''

    f = Fernet(ENCRYPTION_KEY.encode())
    encrypted = f.encrypt(plain_text.encode())
    return base64.b64encode(encrypted).decode()

def decrypt_password(encrypted_text: str) -> str:
    """解密密码"""
    if not encrypted_text:
        return ''

    f = Fernet(ENCRYPTION_KEY.encode())
    encrypted = base64.b64decode(encrypted_text.encode())
    decrypted = f.decrypt(encrypted)
    return decrypted.decode()
```

### 7.2 Docker容器资源限制

```python
# 创建容器时添加资源限制
container = client.containers.run(
    image=config.docker_image,
    detach=True,
    # CPU限制
    cpu_period=100000,  # 100ms
    cpu_quota=50000,    # 50ms (相当于0.5个CPU核心)
    # 内存限制
    mem_limit='2g',
    memswap_limit='2g',
    # 磁盘限制
    storage_opt={'size': '10G'},
    # 网络隔离
    network_mode='bridge',
    # 只读文件系统(除了挂载的工作目录)
    read_only=True,
    tmpfs={'/tmp': 'size=1G'},
    # 禁用特权模式
    privileged=False,
    # 安全配置
    security_opt=['no-new-privileges'],
    # PID限制
    pids_limit=100
)
```

### 7.3 代码审计日志

```python
class DevelopmentAuditLog(models.Model):
    """开发审计日志"""
    task = models.ForeignKey(AIDevelopmentTask, on_delete=models.CASCADE)
    action = models.CharField(max_length=100, verbose_name='操作')
    details = models.JSONField(verbose_name='详情')
    ip_address = models.GenericIPAddressField(verbose_name='IP地址')
    user_agent = models.CharField(max_length=500, verbose_name='User Agent')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='时间戳')

    class Meta:
        db_table = 'development_audit_log'
```

---

## 八、方案对比与推荐

### 方案总结

| 方案 | 环境隔离 | AI工具控制 | 状态更新 | 复杂度 | 推荐度 |
|------|----------|------------|----------|--------|--------|
| **方案1(推荐)** | Docker | pexpect | WebSocket+轮询 | 中 | ⭐⭐⭐⭐⭐ |
| **方案2** | 本地虚拟环境 | pexpect | 轮询 | 低 | ⭐⭐⭐ |
| **方案3** | Kubernetes | Job API | WebSocket | 高 | ⭐⭐⭐⭐ |

### 推荐方案: 方案1 (Docker + pexpect + WebSocket)

**优势**:
1. ✅ **安全性高**: Docker提供完整的进程、网络、文件系统隔离
2. ✅ **可扩展**: 可轻松扩展到多台服务器
3. ✅ **资源可控**: 精确限制CPU、内存、磁盘
4. ✅ **易于审计**: 所有操作都在容器中,日志完整
5. ✅ **实时反馈**: WebSocket保证用户体验
6. ✅ **兼容性好**: pexpect支持各种CLI工具

**劣势**:
1. ❌ Windows环境下Docker Desktop性能较差(建议Linux服务器)
2. ❌ 需要额外维护Docker镜像
3. ❌ 初次实现复杂度较高

---

## 九、实施计划

### 阶段1: 基础设施搭建 (1周)
- [ ] 创建`ai_development` Django app
- [ ] 数据库表设计与迁移
- [ ] Docker镜像构建(包含Claude Code、Playwright、Selenium)
- [ ] 凭证加密工具开发
- [ ] Celery队列配置

### 阶段2: 核心功能开发 (2-3周)
- [ ] AI开发配置CRUD接口
- [ ] Git仓库自动发现功能
- [ ] Claude Code控制器开发
- [ ] Codex CLI控制器开发(如需要)
- [ ] Docker容器编排逻辑
- [ ] Celery任务编排

### 阶段3: 状态同步 (1周)
- [ ] Django Channels集成(WebSocket)
- [ ] 状态更新推送机制
- [ ] 轮询降级机制
- [ ] 日志流式传输

### 阶段4: 前端开发 (1周)
- [ ] 配置管理页面
- [ ] 需求详情页AI开发区域
- [ ] 实时进度展示组件
- [ ] 结果展示页面

### 阶段5: 测试与优化 (1周)
- [ ] 单元测试
- [ ] 集成测试
- [ ] 压力测试(并发任务)
- [ ] 安全测试
- [ ] 性能优化

### 阶段6: 文档与培训 (3天)
- [ ] 用户使用文档
- [ ] 管理员运维文档
- [ ] 团队培训

**总计: 6-7周**

---

## 十、关键决策点需要确认

请确认以下关键技术选型:

1. **环境隔离方案**: Docker容器 vs 本地虚拟环境?
   - 推荐: **Docker容器**

2. **AI工具支持**: 是否两者都支持,还是只支持Claude Code?
   - 推荐: **先支持Claude Code,预留Codex CLI接口**

3. **状态更新机制**: WebSocket vs 纯轮询?
   - 推荐: **WebSocket(主) + 轮询(降级)**

4. **测试工具安装**: 自动安装 vs 镜像预装?
   - 推荐: **镜像预装**(启动更快)

5. **远程服务器支持**: 第一期是否支持?
   - 推荐: **第一期仅支持本地服务器,第二期支持远程SSH**

6. **代码版本管理**: 是否支持tag/commit hash指定?
   - 推荐: **第一期支持branch,第二期支持tag/commit**

7. **AI授权模式**: 是否第一期就实现问答模式?
   - 推荐: **第一期仅完全授权,第二期增加问答模式**

---

## 十一、风险与应对

### 风险1: Claude Code无法自动化控制
**应对**:
- 调研Claude Code是否有`--non-interactive`或API模式
- 如不支持,考虑使用Anthropic API直接编排开发流程

### 风险2: AI开发质量不稳定
**应对**:
- 提供详细的prompt工程指导
- 实现"AI开发 + 人工Review"机制
- 记录所有AI对话,便于优化prompt

### 风险3: Docker资源消耗过大
**应对**:
- 严格限制单容器资源(CPU: 0.5核, 内存: 2GB)
- 任务完成后及时清理容器
- 实现容器池复用机制

### 风险4: 并发任务导致服务器压力过大
**应对**:
- Celery队列限流(最多3个并发)
- 监控服务器资源,动态调整并发数
- 支持分布式部署多台Worker

---

## 十二、成本估算

### 服务器资源
- 单个AI开发任务: 0.5 CPU核心 + 2GB内存 + 10GB磁盘
- 并发3个任务: 1.5 CPU + 6GB内存 + 30GB磁盘
- **推荐配置**: 4核CPU + 16GB内存 + 500GB SSD

### 开发人力
- 后端开发: 3周 (1人)
- 前端开发: 1周 (1人)
- 测试: 1周 (1人)
- **总计**: 约 5人周

### AI API成本
- 单次开发约消耗: 50,000-100,000 tokens
- Claude Sonnet成本: $3/1M input tokens, $15/1M output tokens
- 单次开发成本: 约 $0.5-$2
- 每月100次开发: **约 $50-$200**

---

## 十三、后续扩展方向

1. **智能代码Review**: AI审核提交的代码质量
2. **自动修复Bug**: 根据测试报告自动修复失败的用例
3. **多仓库支持**: 同时操作前后端多个仓库
4. **可视化Pipeline**: 类似GitLab CI的可视化开发流程
5. **IDE集成**: 支持VSCode插件直接触发
6. **代码质量分析**: SonarQube集成
7. **性能测试**: 自动执行性能测试并生成报告

---

## 附录

### 附录A: Docker镜像Dockerfile

```dockerfile
FROM python:3.10-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    nodejs \
    npm \
    build-essential \
    libssl-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 安装Claude Code
RUN npm install -g @anthropic/claude-code

# 安装Python测试工具
RUN pip install --no-cache-dir \
    playwright==1.40.0 \
    selenium==4.15.0 \
    pytest==7.4.3 \
    pytest-playwright==0.4.3 \
    requests==2.31.0

# 安装Playwright浏览器
RUN playwright install chromium
RUN playwright install-deps chromium

# 配置Git
RUN git config --global user.name "AI Developer" && \
    git config --global user.email "ai@testhub.com" && \
    git config --global core.autocrlf false

# 工作目录
WORKDIR /workspace

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD git --version && claude-code --version || exit 1

CMD ["/bin/bash"]
```

### 附录B: 入口脚本示例

```bash
#!/bin/bash
# entrypoint.sh

set -e

echo "=== TestHub AI Development Container ==="
echo "AI Tool: $AI_TOOL"
echo "LLM Model: $LLM_MODEL"
echo "Git URL: $GIT_URL"
echo "Git Branch: $GIT_BRANCH"

# 执行开发任务
cd /workspace

# 这里将由Celery任务通过docker exec执行具体命令
exec "$@"
```

### 附录C: Claude Code命令参考

```bash
# 启动Claude Code
claude-code

# 非交互模式(如支持)
claude-code --non-interactive

# 切换模型
/model sonnet
/model opus
/model haiku

# 设置API Key
/api-key YOUR_API_KEY

# 退出
/exit
```

### 附录D: Celery配置

```python
# backend/celery.py
from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

app = Celery('testhub')
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现任务
app.autodiscover_tasks()

# 配置队列
app.conf.task_routes = {
    'apps.ai_development.tasks.*': {'queue': 'ai_coding'},
}

app.conf.task_queues = {
    'ai_coding': {
        'exchange': 'ai_coding',
        'routing_key': 'ai_coding',
    }
}
```

---

**文档版本**: v1.0
**最后更新**: 2026-04-02
**作者**: Claude (Anthropic)
