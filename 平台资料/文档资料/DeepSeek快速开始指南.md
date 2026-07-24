# DeepSeek AI自动编码 - 快速开始指南

## 🎉 验证完成状态

✅ **所有验证已通过！**
- ✅ openai库已安装
- ✅ API连接正常
- ✅ 代码生成成功
- ✅ 代码解析功能正常
- ✅ Docker集成测试通过
- ✅ 数据库迁移完成

现在可以开始使用AI自动编码功能了！

---

## 📋 使用流程

### 第1步: 确保Django服务运行

```bash
# 启动Django开发服务器
python manage.py runserver
```

访问: http://localhost:8000/admin/

---

### 第2步: 创建AI开发配置

1. **登录Django Admin**
   - 访问: http://localhost:8000/admin/
   - 使用超级用户账号登录

2. **进入AI开发配置页面**
   - 点击侧边栏: **AI Development** → **AI开发配置**
   - 或直接访问: http://localhost:8000/admin/ai_development/aidevelopmentconfig/

3. **点击"添加 AI开发配置"**

4. **填写配置信息**:

#### 基本信息
- **配置名称**: `DeepSeek自动开发配置`
- **关联项目**: 选择你的项目（如果没有，先在"项目管理"中创建）

#### Git配置
- **Git仓库地址**: `https://github.com/your-org/your-repo.git`
- **Git用户名**: 你的Git用户名
- **Git密码(加密存储)**: 你的Git密码或Personal Access Token
- **默认分支**: `main` 或 `master`

#### 项目路径配置
- **项目代码路径**: `/workspace/code` (保持默认)

#### AI编码工具配置 ⭐
- **AI编码工具**: 选择 **`DeepSeek API`** ⭐
- **大模型**: 填写 **`deepseek-coder`** (推荐) 或 `deepseek-chat`
- **模型API Key(加密)**: 粘贴你的DeepSeek API Key

> **提示**:
> - `deepseek-coder`: 专门优化代码生成，推荐用于开发任务
> - `deepseek-chat`: 通用对话模型，适合复杂需求分析

#### 测试工具配置
- **自动安装测试工具**: ✅ 勾选
- **测试框架**: 选择 `Playwright` 或 `Selenium`

#### 环境配置
- **使用Docker隔离**: ✅ 勾选（推荐）
- **Docker镜像**: `python:3.10-slim` (或使用自定义镜像)

#### 构建配置（可选）
- **构建命令**: `npm run build` 或 `python setup.py build`
- **测试命令**: `npm test` 或 `pytest`
- **启动命令**: `npm run dev` 或 `python manage.py runserver`
- **服务端口**: `8080` 或你的应用端口

#### 元数据
- **是否启用**: ✅ 勾选
- **创建者**: 自动设置为当前用户

5. **点击"保存"**

配置会自动加密Git密码和API Key后保存到数据库。

---

### 第3步: 创建业务需求

在使用AI自动开发前，需要先有业务需求：

1. **创建需求文档**
   - 进入: **Requirement Analysis** → **需求文档**
   - 上传需求文档或创建文本需求

2. **AI分析需求**（如果使用需求分析功能）
   - 系统会自动生成需求分析
   - 提取业务需求列表

3. **或手动创建业务需求**
   - 进入: **Requirement Analysis** → **业务需求**
   - 点击"添加业务需求"
   - 填写:
     - **需求编号**: `REQ-001`
     - **需求名称**: `用户登录功能`
     - **需求描述**: 详细描述功能需求
     - **验收标准**: 列出验收条件

---

### 第4步: 创建AI开发任务

#### 方式1: 通过Django Admin创建

1. **进入AI开发任务页面**
   - 访问: http://localhost:8000/admin/ai_development/aidevelopmenttask/
   - 点击"添加 AI开发任务"

2. **填写任务信息**:
   - **任务ID**: 自动生成（如 `AIDEV-20260402-001`）
   - **关联需求**: 选择刚创建的业务需求
   - **开发配置**: 选择DeepSeek配置
   - **开发分支**: `feature/REQ-001` (自动生成)
   - **发起人**: 当前用户

3. **保存后查看任务详情**

#### 方式2: 通过API创建（推荐用于前端集成）

```bash
# POST /api/ai-development/tasks/create_task/
curl -X POST http://localhost:8000/api/ai-development/tasks/create_task/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token your-token-here" \
  -d '{
    "requirement_id": 1,
    "config_id": 1
  }'
```

---

### 第5步: 执行AI开发任务

#### 使用Celery Worker执行（生产环境）

1. **启动Celery Worker**:
```bash
# Windows
celery -A backend worker -l info -P solo

# Linux/Mac
celery -A backend worker -l info
```

2. **触发任务执行**:
任务会自动进入Celery队列执行。

#### 手动测试执行（开发环境）

使用测试脚本验证整个流程：

```bash
# 设置DeepSeek API Key
$env:DEEPSEEK_API_KEY="sk-your-key-here"

# 运行端到端测试
python tests/test_e2e_ai_development.py
```

**测试脚本会**:
1. 创建测试用户、项目、需求
2. 创建DeepSeek配置
3. 创建AI开发任务
4. 在Docker容器中执行AI开发
5. 验证生成的文件
6. 显示详细日志

---

### 第6步: 监控任务进度

#### 通过Django Admin查看

1. **访问任务列表**:
   http://localhost:8000/admin/ai_development/aidevelopmenttask/

2. **点击任务查看详情**，可以看到:
   - **状态**: pending → connecting → cloning → ai_coding → building → testing → committing → completed
   - **进度**: 0% → 100%
   - **当前步骤**: 实时更新的步骤描述
   - **执行日志**: 完整的命令输出
   - **AI对话日志**: DeepSeek的完整响应
   - **容器ID**: Docker容器标识
   - **Git信息**: 分支名、commit hash、commit message
   - **构建/测试结果**: 是否成功、输出内容
   - **服务地址**: 启动后的服务URL

#### 通过API查询进度

```bash
# GET /api/ai-development/tasks/{task_id}/progress/
curl http://localhost:8000/api/ai-development/tasks/AIDEV-20260402-001/progress/
```

**响应示例**:
```json
{
  "task_id": "AIDEV-20260402-001",
  "status": "ai_coding",
  "progress": 45,
  "current_step": "DeepSeek AI正在生成代码...",
  "started_at": "2026-04-02T10:30:00Z",
  "estimated_completion": null
}
```

---

## 📊 任务状态说明

| 状态 | 进度 | 说明 |
|------|------|------|
| **pending** | 0% | 等待执行 |
| **queued** | 5% | 已加入队列 |
| **connecting** | 10% | 连接服务器/创建容器 |
| **cloning** | 15% | 克隆代码仓库 |
| **starting_ai** | 20% | 启动AI工具 |
| **ai_analyzing** | 30% | AI分析需求中 |
| **ai_coding** | 40-60% | AI编码中 |
| **building** | 70% | 构建项目 |
| **testing** | 80% | 执行测试 |
| **committing** | 90% | 提交代码到Git |
| **starting_service** | 95% | 启动服务 |
| **completed** | 100% | 已完成 |
| **failed** | - | 失败（查看error_message） |
| **cancelled** | - | 已取消 |

---

## 🔍 查看任务结果

### 1. 查看生成的代码

**方式1: 在Git仓库中查看**
```bash
# 切换到开发分支
git fetch origin
git checkout feature/REQ-001

# 查看提交历史
git log

# 查看修改的文件
git diff main
```

**方式2: 进入Docker容器查看**
```bash
# 获取容器ID (在任务详情中)
docker ps -a | grep aidev

# 进入容器
docker exec -it <container_id> bash

# 查看生成的文件
cd /workspace/code
ls -la
cat src/components/Login.vue
```

### 2. 查看AI对话日志

在Django Admin任务详情页面，滚动到 **"AI对话日志"** 字段，可以看到：
- DeepSeek的完整响应
- 生成的代码内容
- 技术方案说明
- 实现要点

### 3. 查看构建/测试结果

在任务详情页面查看：
- **构建是否成功**: ✅/❌
- **构建输出**: 完整的构建日志
- **测试是否成功**: ✅/❌
- **测试输出**: 测试用例执行结果

### 4. 访问启动的服务

如果配置了启动命令，任务完成后可以访问：
- **服务地址**: 在任务详情中查看（如 `http://192.168.1.100:8080`）
- **服务账号/密码**: 如果AI生成了，会显示在这里

---

## 💰 成本估算

### DeepSeek定价
- **价格**: ¥1/百万tokens (约$0.14/百万tokens)
- **充值**: 最低¥5起

### 单次开发任务成本估算

| 需求复杂度 | Token消耗 | 费用 |
|-----------|----------|------|
| 简单功能 (如计数器) | 2,000-5,000 | ¥0.002-0.005 |
| 中等功能 (如登录页面) | 5,000-10,000 | ¥0.005-0.01 |
| 复杂功能 (如CRUD模块) | 10,000-20,000 | ¥0.01-0.02 |

**示例**: 开发一个完整的用户管理模块（含CRUD、权限、测试）
- 预计Token: 15,000
- 费用: ¥0.015 (约$0.002)
- 时间: 30-60秒

### 月度成本估算

假设每天开发10个中等复杂度功能：
- 日消耗: 10 × 7,500 tokens = 75,000 tokens
- 日费用: ¥0.075
- **月费用**: ¥2.25 (约$0.32)

---

## 🛠️ 常见问题

### Q1: DeepSeek生成的代码质量如何？

**A**:
- ✅ **代码生成**: deepseek-coder专门优化，质量接近Claude Sonnet
- ✅ **测试覆盖**: 会自动生成Playwright/Selenium测试
- ✅ **最佳实践**: 遵循Vue 3/React等框架的最佳实践
- ⚠️ **建议**: 仍需人工review，特别是安全相关代码

### Q2: 如果AI生成的代码有错误怎么办？

**A**:
1. 查看"构建输出"和"测试输出"了解具体错误
2. 手动修改代码（在Git分支中）
3. 或重新创建任务，调整需求描述更详细
4. 未来版本会支持"问答模式"，可与AI交互修复

### Q3: 可以同时运行多个AI开发任务吗？

**A**:
- ✅ 可以，Celery支持并发
- ⚠️ 注意DeepSeek API限流: 60次/分钟，5个并发
- 💡 建议: 配置Celery并发数 ≤ 5

### Q4: Docker容器会自动清理吗？

**A**:
- ❌ 默认不会自动清理（用于审计）
- 💡 可以手动清理: `docker rm -f <container_id>`
- 💡 或定期清理: 在settings中配置自动清理策略

### Q5: 如何切换回Anthropic API？

**A**:
1. 打开AI开发配置
2. 修改"AI编码工具"为 `Anthropic API (Claude)`
3. 修改"大模型"为 `sonnet`/`opus`/`haiku`
4. 更新"模型API Key"为Anthropic Key
5. 保存

### Q6: 支持哪些编程语言？

**A**:
DeepSeek支持主流语言：
- ✅ Python, JavaScript/TypeScript, Vue, React
- ✅ Java, Go, Rust, C++
- ✅ HTML/CSS, SQL
- ⚠️ 建议在需求描述中明确指定语言和框架

---

## 📚 相关文档

- **完整技术方案**: `AI自动编码功能技术方案.md` (67页)
- **实施指南**: `AI自动编码功能实施指南.md`
- **DeepSeek集成报告**: `DeepSeek集成完成报告.md`
- **API文档**: http://localhost:8000/api/docs/
- **模块README**: `apps/ai_development/README.md`

---

## 🎯 下一步建议

### 立即可做
1. ✅ **在Django Admin中创建DeepSeek配置**
2. ✅ **创建一个简单需求测试**（如计数器功能）
3. ✅ **运行端到端测试验证**
4. ✅ **查看生成的代码质量**

### 后续开发
1. ⏳ **前端界面开发**
   - AI开发配置管理页面
   - 任务创建向导
   - 实时进度监控页面
   - 需求详情页的"AI开发"按钮

2. ⏳ **功能增强**
   - WebSocket实时推送
   - 问答模式（半自动化）
   - 代码质量分析
   - 成本统计报表

3. ⏳ **生产环境部署**
   - 配置Celery Worker
   - Docker镜像优化
   - 监控告警设置

---

## 🎉 开始使用吧！

现在所有准备工作都已完成，你可以：

1. **启动Django服务**: `python manage.py runserver`
2. **访问Admin**: http://localhost:8000/admin/
3. **创建DeepSeek配置**
4. **创建第一个AI开发任务**
5. **见证AI自动编码的魔力！** ✨

**祝你使用愉快！如有问题，请查看上面的常见问题或相关文档。**

---

*最后更新: 2026-04-02*
*DeepSeek API验证状态: ✅ 全部通过*
