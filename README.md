# PaperSearchAgent

一个基于 A2A (Agent-to-Agent) 协议的学术论文搜索 AI 智能体，专门用于搜索学术论文。

## 项目简介

PaperSearchAgent 是一个智能的学术论文搜索助手，能够：

- **智能搜索**：通过自然语言描述搜索 arXiv 和 Semantic Scholar 上的学术论文
- **多语言支持**：支持中英文等多语言查询，自动将中文查询转换为英文关键词
- **查询分析**：使用 LLM 分析查询意图，提取关键词，优化搜索效果
- **结构化结果**：返回格式化的搜索结果，包含标题、作者、摘要、链接等信息
- **直接访问**：提供论文和 PDF 的直接链接（如果可用）

## 核心功能

### 论文搜索
- 支持自然语言查询
- 智能查询分析：使用 LLM 分析查询意图，提取关键词
- 中文查询自动转换：将中文查询转换为英文关键词，适配学术搜索引擎
- 整合多个学术数据库（arXiv、Semantic Scholar）
- 每次搜索返回最多 5 篇最相关的论文
- 提供完整的论文元数据

## 技术架构

```
PaperSearchAgent/
├── __main__.py              # 主入口，启动 A2A 服务器
├── agent_executor.py        # 核心执行器，处理 A2A 请求
├── config.py               # 配置管理
├── src/                    # 核心功能模块
│   ├── paper_search.py     # 学术论文搜索
│   ├── query_analyzer.py   # 查询分析与关键词提取
│   └── output_formatter.py # 输出格式化
└── start_agent.sh          # 启动脚本
```

## 快速开始

### 环境要求
- Python 3.10+
- arXiv API 访问
- Semantic Scholar API 密钥（可选）
- OpenAI API 密钥（用于查询分析，**必需**）
- 推荐使用`uv`来管理环境

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/HEHUA2005/PaperSearchAgent.git
   cd PaperSearchAgent
   ```

2. **安装依赖**
   ```bash
  uv sync 
   ```

3. **配置环境变量**
   ```bash
   # 创建 .env 文件
   AGENT_PORT="9998"
   SEMANTIC_SCHOLAR_API_KEY="your-semantic-scholar-api-key"  # 可选
   LLM_API_KEY="your-openai-api-key"  # 用于查询分析，必需
   ```

### 启动服务

```bash
# 使用启动脚本
bash start_agent.sh

# 或直接运行
uv run python -m __main__
```

服务将在 http://localhost:9998 启动。

## 使用示例

### 搜索论文
```bash
curl -X POST http://localhost:9998/api/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "sendMessage",
    "params": {
      "taskId": "task_id",
      "message": {
        "role": "user",
        "parts": [{"text": "找一些关于 Transformer 注意力机制的论文"}]
      }
    },
    "id": 1
  }'
```

## 搜索结果格式

搜索结果包含以下信息：
- **标题**：论文标题
- **作者**：作者列表和年份
- **来源**：arXiv 或 Semantic Scholar
- **摘要**：论文摘要（如果过长会截断）
- **链接**：论文页面 URL 和 PDF 下载链接（如果可用）

## 配置选项

通过环境变量进行配置：

- `AGENT_PORT`：服务端口（默认：9998）
- `ARXIV_CATEGORIES`：arXiv 搜索类别（默认：cs.AI,cs.LG,cs.CL）
- `SEMANTIC_SCHOLAR_API_KEY`：Semantic Scholar API 密钥（可选）
- `ENABLE_SEMANTIC_SCHOLAR`：是否启用 Semantic Scholar 搜索（默认：false）
- `MAX_SEARCH_RESULTS`：最大搜索结果数（默认：5）
- `ENABLE_PDF_URL_ENHANCEMENT`：是否启用增强的 PDF URL 提取（默认：true）

### 查询分析配置

- `LLM_API_KEY`：LLM API 密钥 - **必需**
- `LLM_API_URL`：完整的 LLM API 端点（如 https://api.openai.com/v1/chat/completions）
- `LLM_BASE_URL`：LLM API 基础 URL（如 https://api.openai.com/v1），如果提供，将与 "/chat/completions" 组合
- `LLM_MODEL`：使用的 LLM 模型（默认：gpt-3.5-turbo）
- `LLM_PROVIDER`：LLM 提供商（默认：openai，支持 OpenAI 兼容接口）
- `LLM_MAX_TOKENS`：最大生成令牌数（默认：4096）
- `LLM_TEMPERATURE`：生成温度（默认：0.3）
- `USE_FALLBACK_ON_LLM_ERROR`：LLM API 调用失败时是否使用原始查询作为回退（默认：false）

### PDF URL 增强配置

- `ENABLE_PDF_URL_ENHANCEMENT`：启用增强的 PDF URL 提取功能（默认：true）
  - 当启用时，系统会尝试从多个来源获取 PDF 链接：
    - Semantic Scholar 的 openAccessPdf 字段
    - 通过 arXiv ID 构建 arXiv PDF 链接
    - 通过 PubMed/PMC ID 构建医学论文链接
    - 通过 DOI 识别以下来源的 PDF：
      - bioRxiv/medRxiv 预印本服务器
      - Nature 期刊
      - Science 期刊
      - IEEE 论文
      - ACM 数字图书馆
      - 其他通用 DOI 链接
  - 当禁用时，仅使用 Semantic Scholar 的 openAccessPdf 字段

## A2A 协议集成

PaperSearchAgent 完全兼容 A2A (Agent-to-Agent) 通信协议：

- **协议版本**：A2A JSON-RPC 2.0
- **输入模式**：文本消息（自然语言查询）
- **输出模式**：文本消息（格式化的搜索结果）
- **流式支持**：支持实时响应流

### 消息格式

输入消息格式：
```json
{
  "message": {
    "role": "user",
    "parts": [
      {"kind": "text", "text": "your search query here"}
    ]
  }
}
```

## 示例查询

- "Find papers about transformer attention mechanisms"
- "Search for recent papers on reinforcement learning"
- "Papers on quantum computing"
- "找一些关于GAN的论文"
- "最新的神经网络研究"

## 许可证

本项目采用 MIT 许可证。

## 免责声明

这是一个演示项目。在生产环境中使用时，请确保实施适当的安全措施，包括输入验证和凭据的安全处理。