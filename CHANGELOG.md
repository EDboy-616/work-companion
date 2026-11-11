# Changelog

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。版本号记录在 `.claude-plugin/plugin.json`。

## [0.1.0] - 2026-11-11

### 新增
- `SKILL.md` 初版：秘书型工作伴侣，含承诺跟踪、阶段小结、周度回顾、模式发现、情绪接应五类主动动作
- 硬约束体系：每次对话最多插一句、忽略即静默、不翻旧账、7 天降频、透明可撤销
- **跨 harness 兼容改造**：frontmatter 仅保留通用字段、双语 description、正文零工具名引用、相对路径、无脚本依赖
- **记忆降级规则**：无文件能力的环境（如网页版）退回会话内记忆，并明确告知用户未持久化
- `COMPATIBILITY.md`：环境适配表与安装检查清单

### 架构
- 仓库改造为标准分发结构：`.claude-plugin/`（plugin.json + marketplace.json）+ `skills/<name>/SKILL.md`
- 五种安装方式：一键脚本、官方 plugin marketplace、npx 通用安装器、git clone、手动复制
- `install.sh` / `install.ps1`：跨平台安装脚本，支持 `--target`（claude-code / codex / cursor / all / dir）与 `--force`
- `.gitignore`：排除运行时生成的工作记忆文件（含个人数据）

### 待办
- 内核能力实现：承诺解析、到期判断、周度汇总的自动化
- 记忆文件跨会话同步方案
- 更多 harness 的路径验证（codex / cursor 路径目前为约定值）
