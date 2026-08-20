# RepoImmune

**让 Coding Agent 记住仓库已经修复过的每一个 Bug。**

RepoImmune 把 Issue、Buggy/Fix Commit、代码 Diff、回归测试和符号级 AST 证据连接成可查询、可回放、可在 PR 中机械检查的“行为记忆”。它不是聊天记录，也不会只凭 Issue 标题宣称一个 Bug 已被证明。

| 输入 | 处理 | 输出 |
|---|---|---|
| GitHub 仓库或 PR Diff | 检索历史 Bug 的 Issue → 修复 → 测试 → AST 证据链 | 具体回归位置、来源、受保护测试和历史修复 |

## 60 秒开始

```bash
git clone https://github.com/Alex0AI/RepoImmune.git
cd RepoImmune
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .
repoimmune init .
repoimmune check --diff examples/reintroduce-astropy-12907.diff --memory examples/memory
repoimmune replay astropy-12907 --memory examples/memory
```

示例无需 API Key、Docker 或外部数据库。它会故意检出 Astropy PR #12907 曾经修复的一行结构性回归，并返回具体代码、Issue、PR、Commit 与 pytest 证据。

## 核心产物

- 带版本和内容哈希的开放 Behavior Card Schema（JSON Schema + TypeScript 类型）。
- Python AST 结构指纹与 TypeScript/JavaScript 确定性结构 Token。
- JSON、Markdown、SARIF 和静态 HTML 报告。
- 只读 GitHub Action、六工具 MCP Server 与开放 Agent Skill。
- 安全 Regression Capsule：不使用 shell，不执行未知仓库安装脚本，拒绝绝对路径和符号链接。
- GitHub Pages 静态 Demo，无登录、无密钥。

## 证据等级

- `verified`：本地直接回放或由一手代码/测试机械交叉验证。
- `externally_reported`：上游或人工验证数据集报告通过，但本地未完整复现。
- `heuristic`：候选或相似性信号，不是证明。
- `inconclusive`：证据冲突或不足。

RepoImmune 不会把相似度分数伪装成事实。每个结果必须展示命中的具体代码和来源 URL。

## 当前边界

v0.1 首先把 Python/pytest 做深；TypeScript/TSX 已提供可选、锁定版本的 tree-sitter 结构与调用提取器，JavaScript 使用确定性结构 Token，Jest/Vitest 可记录为测试证据，但尚未达到 Python 的分析深度。完整上游环境回放、跨过程调用图和更多语言属于后续计划。大规模数据卡在真正回放前标为 `externally_reported`；v0.1 中本地完整验证的行为 Capsule 是 Astropy 纵向切片。

详细英文文档、研究对比、安全模型和复现实验见主 [README](README.md)。
