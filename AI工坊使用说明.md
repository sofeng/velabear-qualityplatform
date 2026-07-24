# AI工坊 - AI创建技能与插件上传功能说明

## 功能概述

AI工坊现已支持两种创建技能的方式：

### 1. AI创建技能 🤖
使用AI自动生成技能代码，支持三种技能类型：
- **Skill (技能)**: 生成可执行的Python函数
- **Prompt (提示词)**: 生成结构化的AI提示词
- **Agent (代理)**: 生成Agent配置

### 2. 上传插件 📦
上传自定义插件文件，支持两种格式：
- **单个Python文件** (.py)
- **ZIP插件包** (.zip)

---

## 一、AI创建技能

### 使用步骤

1. **进入AI工坊**
   - 登录系统
   - 进入【AI研发平台】→【AI工坊】

2. **点击"AI创建技能"按钮**
   - 选择技能类型（Skill/Prompt/Agent）
   - 输入生成提示词

3. **提交生成**
   - AI会根据提示词自动生成技能代码
   - 生成完成后，技能会显示在列表中
   - 状态为"草稿"，需要审核后才能启用

### 示例提示词

#### Skill类型示例
```
创建一个计算字符串相似度的技能，支持编辑距离和余弦相似度两种算法
```

#### Prompt类型示例
```
创建一个代码审查提示词，要求AI检查代码的安全性、性能和可维护性
```

#### Agent类型示例
```
创建一个自动化测试Agent，能够根据需求文档生成测试用例
```

### AI生成原理

1. **配置检测**：优先使用DeepSeek，其次Qwen
2. **智能生成**：根据技能类型生成相应的代码/配置
3. **模板降级**：如果AI不可用，返回可编辑的模板代码

### 注意事项

- AI生成的代码需要审核后才能使用
- 生成的代码可以在详情页中查看和编辑
- 建议先测试后再启用

---

## 二、上传插件

### 方式1：上传单个Python文件 (.py)

#### 文件格式

支持使用特殊注释标记声明元数据：

```python
# @plugin:name: 数据处理工具
# @plugin:description: 提供常用的数据处理功能
# @plugin:kind: skill
# @plugin:entrypoint: main
# @plugin:tags: 数据处理, 工具

"""模块文档字符串（作为备用描述）"""

def main(input_data):
    """技能主函数"""
    # 实现逻辑
    return {'status': 'success', 'result': '...'}
```

#### 支持的元数据标记

| 标记 | 说明 | 必需 |
|-----|------|-----|
| @plugin:name | 插件名称 | 否（默认使用文件名） |
| @plugin:description | 插件描述 | 否（使用模块文档字符串） |
| @plugin:kind | 技能类型 | 否（默认skill） |
| @plugin:entrypoint | 入口函数 | 否（自动检测main/execute/run） |
| @plugin:tags | 标签（逗号分隔） | 否 |

#### 使用步骤

1. 准备Python文件（参考 `example_plugin.py`）
2. 在AI工坊点击"上传插件"
3. 选择 .py 文件
4. 点击"上传"

---

### 方式2：上传ZIP插件包 (.zip)

#### ZIP包结构

```
my_plugin.zip
├── manifest.json    # 必需：插件元数据
├── main.py          # 必需：主代码文件
└── README.md        # 可选：说明文档
```

#### manifest.json 格式

```json
{
  "code": "unique_plugin_code",
  "name": "插件名称",
  "kind": "skill",
  "description": "插件描述",
  "version": "1.0.0",
  "provider": "提供者名称",
  "main": "main.py",
  "entrypoint": "main",
  "tags": ["标签1", "标签2"],
  "risk_level": "low",
  "config_schema": {
    "type": "object",
    "properties": {
      "param1": {
        "type": "string",
        "description": "参数1说明"
      }
    }
  }
}
```

#### 字段说明

| 字段 | 类型 | 必需 | 说明 |
|-----|------|-----|------|
| code | string | 否 | 唯一编码（未提供则自动生成） |
| name | string | 是 | 插件名称 |
| kind | string | 否 | 技能类型（默认skill） |
| description | string | 否 | 插件描述 |
| version | string | 否 | 版本号（默认1.0.0） |
| provider | string | 否 | 提供者（默认用户名） |
| main | string | 否 | 主文件名（默认main.py） |
| entrypoint | string | 否 | 入口函数（默认main） |
| tags | array | 否 | 标签列表 |
| risk_level | string | 否 | 风险等级（low/medium/high） |
| config_schema | object | 否 | 配置Schema（JSON Schema格式） |

#### 使用步骤

1. 创建插件目录（参考 `example_zip_plugin/`）
2. 编写 manifest.json 和代码文件
3. 将目录打包为 ZIP 文件
4. 在AI工坊点击"上传插件"
5. 选择 ZIP 文件
6. 点击"上传"

---

## 三、测试示例

### 示例1：单个Python文件

项目根目录下的 `example_plugin.py` 演示了如何创建单文件插件：

**功能**：数据处理工具
- 清洗数据（去除空值和重复项）
- 验证邮箱格式

**测试步骤**：
1. 直接上传 `example_plugin.py`
2. 查看技能列表，找到"数据处理工具"
3. 点击"查看"查看代码和配置

### 示例2：ZIP插件包

项目根目录下的 `example_zip_plugin/` 目录包含完整的ZIP插件示例：

**功能**：文本分析工具
- 词频统计
- 关键词提取

**测试步骤**：
1. 将 `example_zip_plugin` 目录打包为 ZIP
   ```bash
   # Windows PowerShell
   Compress-Archive -Path example_zip_plugin\* -DestinationPath text_analyzer.zip

   # Linux/Mac
   cd example_zip_plugin && zip -r ../text_analyzer.zip *
   ```
2. 上传 `text_analyzer.zip`
3. 查看技能列表，找到"文本分析工具"

---

## 四、常见问题

### Q1: AI创建技能失败怎么办？

**A**: 检查以下几点：
1. 是否配置了AI模型（DeepSeek或Qwen）
2. AI配置是否激活
3. 如果AI不可用，会返回可编辑的模板代码

### Q2: 上传插件时提示"文件格式不支持"？

**A**: 确保文件扩展名为 `.py` 或 `.zip`，且文件未损坏。

### Q3: ZIP插件上传后报错"缺少manifest.json"？

**A**: 确保ZIP包的根目录包含 `manifest.json` 文件，而不是嵌套在子目录中。

### Q4: 如何测试上传的插件？

**A**:
1. 在技能详情页查看代码
2. 使用"试运行"功能测试（如已实现）
3. 将技能标记为"已启用"后使用

### Q5: 上传的插件可以修改吗？

**A**:
- 单文件插件：可以在详情页直接编辑内容
- ZIP插件：修改后需要重新打包上传（建议使用复制功能创建新版本）

---

## 五、最佳实践

### 代码规范

1. **使用清晰的函数名**
   - 主函数建议命名为 `main`、`execute` 或 `run`
   - 功能函数使用动词开头（如 `process_data`）

2. **完善的错误处理**
   ```python
   def main(input_data):
       try:
           # 业务逻辑
           result = process(input_data)
           return {'status': 'success', 'result': result}
       except Exception as e:
           return {'status': 'error', 'message': str(e)}
   ```

3. **标准化的输入输出**
   - 输入：字典格式 `input_data`
   - 输出：包含 `status` 字段的字典

### 安全建议

1. **避免执行危险操作**
   - 不要使用 `eval()` 或 `exec()`
   - 不要访问敏感文件系统路径
   - 限制网络请求范围

2. **验证输入数据**
   ```python
   def main(input_data):
       if not isinstance(input_data, dict):
           return {'status': 'error', 'message': '输入必须是字典'}
       # ... 继续处理
   ```

3. **设置合理的风险等级**
   - low: 纯计算、数据处理
   - medium: 文件读写、网络请求
   - high: 系统调用、数据库操作

---

## 六、技术支持

如遇问题，请检查：
1. 浏览器控制台错误信息
2. Django后端日志
3. 上传的文件编码（必须是UTF-8）

更多信息，请参考项目文档或提Issue。
