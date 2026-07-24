# AI自动编码功能实施指南

## ✅ 已完成工作(第一阶段)

### 1. 后端核心模块

#### 1.1 Django App创建
- ✅ 创建`apps/ai_development` app
- ✅ 配置app到`settings.py`的`INSTALLED_APPS`
- ✅ 添加URL路由到`backend/urls.py`

#### 1.2 数据库模型
创建了2个核心模型:

**AIDevelopmentConfig** (AI开发配置):
- Git配置(仓库地址、用户名、密码加密)
- AI工具配置(Claude Code、模型选择、API Key)
- 项目路径配置
- 构建/测试/启动命令
- Docker配置

**AIDevelopmentTask** (AI开发任务):
- 任务状态管理(11个状态节点)
- Git信息(分支、commit hash、提交信息)
- 执行日志(执行日志、AI对话日志)
- 测试结果(构建成功/失败、测试成功/失败)
- 服务信息(服务地址、账号密码)

#### 1.3 安全加密模块
- ✅ 创建`apps/ai_development/utils/encryption.py`
- ✅ 实现`encrypt_password()`和`decrypt_password()`
- ✅ 使用Fernet对称加密
- ✅ 支持从环境变量或Django SECRET_KEY派生密钥

#### 1.4 REST API
- ✅ 配置管理API (CRUD + 测试连接)
- ✅ 任务管理API (创建、查询、取消、获取进度)
- ✅ 序列化器(支持密码加密/解密)
- ✅ 权限控制(用户只能访问自己的配置和任务)

#### 1.5 Celery任务编排
- ✅ 创建`apps/ai_development/tasks.py`
- ✅ 实现`execute_ai_coding`主任务
- ✅ 实现Docker容器执行逻辑
- ✅ 11个状态节点的进度更新
- ✅ 容器资源限制(0.5 CPU + 2GB内存)

#### 1.6 AI工具控制器
- ✅ 创建`apps/ai_development/ai_tools/claude_code_controller.py`
- ✅ 实现ClaudeCodeController类
- ✅ 提供pexpect控制框架(注释示例)

#### 1.7 Docker支持
- ✅ 创建`deploy/Dockerfile.ai-dev`
- ✅ 创建构建脚本(`build-ai-dev-image.sh` / `.bat`)
- ✅ 预装Python、Node.js、Git、Playwright、Selenium

---

## 📋 后续待完成工作

### 第二阶段: 数据库与WebSocket

#### 2.1 数据库迁移 ⏳
```bash
# 1. 创建迁移文件
python manage.py makemigrations ai_development

# 2. 执行迁移
python manage.py migrate

# 3. 创建测试配置数据
python manage.py shell
>>> from apps.ai_development.models import AIDevelopmentConfig
>>> from apps.projects.models import Project
>>> from apps.users.models import User
>>> # 创建测试配置...
```

#### 2.2 Django Channels配置 ⏳
1. 安装依赖:
```bash
pip install channels channels-redis
```

2. 在`settings.py`添加:
```python
INSTALLED_APPS = [
    ...
    'channels',
]

ASGI_APPLICATION = 'backend.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}
```

3. 创建`backend/asgi.py`:
```python
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import apps.ai_development.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(
            apps.ai_development.routing.websocket_urlpatterns
        )
    ),
})
```

4. 创建`apps/ai_development/consumers.py` (WebSocket消费者)

5. 创建`apps/ai_development/routing.py` (WebSocket路由)

#### 2.3 实时状态推送 ⏳
在`tasks.py`的`update_task_status`函数中添加WebSocket推送:
```python
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def update_task_status(task, status, progress, current_step, save=True):
    task.status = status
    task.progress = progress
    task.current_step = current_step

    if save:
        task.save()

    # WebSocket推送
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'ai_dev_task_{task.task_id}',
        {
            'type': 'task_update',
            'data': {
                'task_id': task.task_id,
                'status': status,
                'progress': progress,
                'current_step': current_step
            }
        }
    )
```

---

### 第三阶段: 前端开发

#### 3.1 前端API封装 ⏳
创建`frontend/src/api/ai_development.js`:
```javascript
import api from '@/utils/api'

export default {
  // 配置管理
  getConfigs(params) {
    return api.get('/ai-development/configs/', { params })
  },
  createConfig(data) {
    return api.post('/ai-development/configs/', data)
  },
  updateConfig(id, data) {
    return api.put(`/ai-development/configs/${id}/`, data)
  },
  deleteConfig(id) {
    return api.delete(`/ai-development/configs/${id}/`)
  },
  testConnection(id) {
    return api.post(`/ai-development/configs/${id}/test_connection/`)
  },

  // 任务管理
  getTasks(params) {
    return api.get('/ai-development/tasks/', { params })
  },
  createTask(data) {
    return api.post('/ai-development/tasks/create_task/', data)
  },
  getTaskProgress(taskId) {
    return api.get(`/ai-development/tasks/${taskId}/progress/`)
  },
  cancelTask(taskId) {
    return api.post(`/ai-development/tasks/${taskId}/cancel/`)
  },
  getTaskLogs(taskId, logType) {
    return api.get(`/ai-development/tasks/${taskId}/logs/`, { params: { log_type: logType } })
  }
}
```

#### 3.2 配置管理页面 ⏳
创建`frontend/src/views/ai-development/AIDevelopmentConfig.vue`

页面功能:
- 配置列表(表格)
- 新增配置(对话框)
- 编辑配置
- 删除配置
- 测试Git连接

#### 3.3 需求详情页集成 ⏳
修改`frontend/src/views/requirement-analysis/RequirementDetail.vue`:

添加AI开发区块:
- 配置选择下拉框
- "启动AI开发"按钮
- 实时进度展示(WebSocket + 轮询降级)
- 开发结果展示(服务地址、账号密码、Git信息)

#### 3.4 任务监控页面 ⏳
创建`frontend/src/views/ai-development/TaskMonitor.vue`

页面功能:
- 任务列表
- 实时状态更新
- 日志查看
- 任务取消

---

### 第四阶段: 关键技术验证与优化

#### 4.1 Claude Code控制验证 🔴 **关键验证点**
**目的**: 验证pexpect能否有效控制Claude Code CLI

**验证步骤**:
1. 手动测试Claude Code CLI:
```bash
# 安装Claude Code (确认官方安装方式)
npm install -g @anthropic-ai/claude-code

# 测试启动
claude-code --help
claude-code --model sonnet --api-key YOUR_KEY

# 测试交互命令
/model sonnet
/non-interactive (如果支持)
```

2. 编写Python测试脚本验证pexpect控制:
```python
import pexpect

child = pexpect.spawn('claude-code --model sonnet --api-key YOUR_KEY')
child.expect('Ready')
child.sendline('Hello, please write a function to add two numbers')
child.expect('Done')
print(child.before)
```

3. 根据测试结果调整`claude_code_controller.py`

#### 4.2 Docker镜像构建 ⏳
```bash
# Windows
cd D:\AI\syswin-testhub\testhub-platform-src
deploy\build-ai-dev-image.bat

# Linux/Mac
cd /path/to/testhub-platform-src
bash deploy/build-ai-dev-image.sh
```

验证镜像:
```bash
docker run -it --rm testhub/ai-dev:latest bash
# 在容器中测试
git --version
node --version
python --version
playwright --version
# 测试Claude Code (如果已安装)
claude-code --version
```

#### 4.3 Celery配置优化 ⏳
在`backend/settings.py`添加:
```python
# Celery任务路由
CELERY_TASK_ROUTES = {
    'apps.ai_development.tasks.execute_ai_coding': {
        'queue': 'ai_coding',
        'routing_key': 'ai_coding',
    }
}

# 并发控制
CELERYD_CONCURRENCY = 3  # 最多3个并发任务
CELERY_TASK_TIME_LIMIT = 3600  # 1小时超时
CELERY_TASK_SOFT_TIME_LIMIT = 3300  # 55分钟软限制
```

启动Celery Worker:
```bash
# Windows
celery -A backend worker -l info -Q ai_coding --pool=solo

# Linux
celery -A backend worker -l info -Q ai_coding --concurrency=3
```

---

### 第五阶段: 测试与调试

#### 5.1 单元测试 ⏳
创建`apps/ai_development/tests.py`:
- 测试加密/解密功能
- 测试配置CRUD
- 测试任务创建
- 测试状态更新

#### 5.2 集成测试 ⏳
- 完整流程测试(创建配置 → 创建任务 → 执行 → 完成)
- WebSocket连接测试
- 轮询降级测试

#### 5.3 压力测试 ⏳
- 模拟3个并发任务
- 测试容器资源限制
- 测试任务队列

---

## 🎯 立即可执行的步骤

### Step 1: 安装依赖
```bash
pip install cryptography docker channels channels-redis
```

### Step 2: 创建数据库迁移
```bash
python manage.py makemigrations ai_development
python manage.py migrate
```

### Step 3: 创建超级用户(如果还没有)
```bash
python manage.py createsuperuser
```

### Step 4: 访问Admin创建测试配置
访问 http://localhost:8000/admin/ai_development/aidevelopmentconfig/
创建一个测试配置。

### Step 5: 测试API
使用Postman或curl测试API:
```bash
# 获取配置列表
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/ai-development/configs/

# 创建任务
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"requirement_id": 1, "config_id": 1}' \
  http://localhost:8000/api/ai-development/tasks/create_task/
```

---

## ⚠️ 关键注意事项

### 1. Claude Code安装方式待确认
**当前状态**: Dockerfile中使用假设的npm安装方式
**待办**: 查阅Claude Code官方文档,确认正确的安装和使用方式

可能的替代方案:
- 如果Claude Code无法自动化,考虑直接使用Anthropic API
- 编写自定义的AI开发编排流程

### 2. 密码加密密钥
**重要**: 生产环境需在`.env`文件配置专用密钥:
```bash
# .env
AI_DEV_ENCRYPTION_KEY=your-32-byte-base64-encoded-key
```

生成密钥:
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### 3. Docker资源限制
当前配置: 0.5 CPU + 2GB内存
根据实际测试结果可能需要调整。

### 4. Git凭证安全
Git密码以加密形式存储在数据库,但在容器执行时会解密。
确保容器运行在安全的网络环境中。

---

## 📚 相关文档

1. **技术方案**: `AI自动编码功能技术方案.md`
2. **API文档**: http://localhost:8000/api/docs/ (启动服务后访问)
3. **Admin管理**: http://localhost:8000/admin/ai_development/

---

## 🆘 常见问题

### Q1: 数据库迁移失败?
**A**: 检查模型是否有语法错误,确保Django配置正确:
```bash
python manage.py check
python manage.py makemigrations --dry-run
```

### Q2: Celery任务不执行?
**A**: 检查Celery Worker是否运行,Redis是否启动:
```bash
# 检查Redis
redis-cli ping

# 启动Celery Worker (在项目根目录)
celery -A backend worker -l info -Q ai_coding
```

### Q3: Docker容器无法访问?
**A**: 检查Docker是否运行,端口是否被占用:
```bash
docker ps
netstat -an | findstr 8080  # Windows
lsof -i :8080  # Linux/Mac
```

---

## ✨ 后续扩展方向

1. **远程服务器支持** (第二期)
   - SSH连接到远程服务器执行

2. **问答模式** (第二期)
   - WebSocket双向通信
   - 用户参与AI决策

3. **Git仓库自动发现** (第二期)
   - 根据Git账号自动列出所有仓库

4. **Codex CLI支持** (第二期)
   - 添加Codex CLI控制器

5. **智能代码Review** (第三期)
   - AI审核提交的代码质量

6. **自动修复Bug** (第三期)
   - 根据测试报告自动修复

---

**文档版本**: v1.0
**最后更新**: 2026-04-02
**下一步**: 执行数据库迁移 → 构建Docker镜像 → 验证Claude Code控制
