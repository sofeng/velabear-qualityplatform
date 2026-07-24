# 文本分析工具插件

这是一个示例ZIP插件包，演示如何创建和上传带有manifest的完整插件。

## 功能

提供两种文本分析模式：

1. **词频统计** (word_count)
   - 统计文本中的词频
   - 返回总词数、唯一词数和Top 10高频词

2. **关键词提取** (keyword_extract)
   - 提取文本中的关键词
   - 过滤停用词后返回高频词

## 使用方法

### 输入格式

```json
{
  "text": "待分析的文本内容",
  "mode": "word_count 或 keyword_extract"
}
```

### 输出格式

**词频统计模式：**
```json
{
  "status": "success",
  "mode": "word_count",
  "result": {
    "total_words": 100,
    "unique_words": 50,
    "top_10": [["word1", 10], ["word2", 8], ...]
  }
}
```

**关键词提取模式：**
```json
{
  "status": "success",
  "mode": "keyword_extract",
  "keywords": ["keyword1", "keyword2", ...]
}
```

## 打包说明

将插件打包成ZIP时，请确保包含以下文件：
- manifest.json (必需)
- text_analyzer.py (主代码文件)
- README.md (可选，说明文档)

## 安装

1. 将此目录打包为 ZIP 文件
2. 在 AI工坊 中点击"上传插件"
3. 选择打包好的 ZIP 文件
4. 等待上传和解析完成
