# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 这个仓库是什么

**不是应用，是 skill 的分发仓库。** 没有构建、没有 lint、没有测试套件——"源码"只有一个 markdown 文件。

仓库里唯一的产品是 `skills/work-companion/SKILL.md`：一段在对话中被注入的指令文本。其余一切都是分发外壳（插件清单、安装脚本、文档）。所以改动分两类，别混着改：

- **改能力**（记录承诺、主动动作、措辞规则、硬约束）→ 只动 `SKILL.md`
- **改分发**（安装方式、插件元数据、文档）→ 动 `.claude-plugin/`、`install.sh`、`install.ps1`、根目录 md

## 常用命令

没有 build / test / lint 命令。开发循环是：**改 SKILL.md → 装到本地 harness → 手动试跑**。

安装到本机（`install.sh` 会**优先**使用脚本同目录下的 `skills/work-companion/SKILL.md`，找不到才走网络）：

```bash
./install.sh                      # → ~/.claude/skills/work-companion/
./install.sh --target all         # → claude-code / codex / cursor 全装
./install.sh --dir /custom/skills # → 自定义目录
./install.sh --force              # 目标已存在时覆盖
```

```powershell
.\install.ps1 -Target codex
.\install.ps1 -Dir C:\custom\skills -Force
```

试跑验收（`COMPATIBILITY.md` 里定义的检查清单）：说"这周五要交个方案"，回复里**必须**出现"我记下了"；在无文件能力的环境里试跑，AI 必须明说"没有地方长期保存"。

发版：改 `.claude-plugin/plugin.json` 的 `version`（semver），并在 `CHANGELOG.md` 顶部加一节。

## 架构要点

### 单一源文件 + 多路分发

`skills/work-companion/SKILL.md` 是唯一真相。五条分发路径全部以它为终点：

| 路径 | 载体 |
|------|------|
| 一键脚本 | `install.sh` / `install.ps1` 复制（或下载）SKILL.md |
| plugin marketplace | `.claude-plugin/plugin.json` + `marketplace.json` |
| npx `skills add` | 第三方工具直接读仓库结构 |
| git clone / 手动复制 | 用户自己 `cp` |

**安装脚本是"本地优先、网络兜底"的双路逻辑**：先看脚本同目录有没有 `skills/<name>/SKILL.md`（git clone 场景），没有才从 `raw.githubusercontent.com` 拉。两处都写着 `BRANCH="main"`——**网络兜底路径永远读 `main`**。所以 `dev` 上的改动，在合并进 `main` 之前，远程一行命令装不到。

### 跨 harness 兼容是硬约束，不是优化项

SKILL.md 要能原样塞进 Claude Code、桌面版、claude.ai、Codex、Cursor 等环境，因此以下五条是**改动 SKILL.md 时必须守住的不变量**（理由见 `COMPATIBILITY.md`）：

1. frontmatter **只有** `name` + `description`——不加 `version` / `allowed-tools` / `model` 等，部分 harness 会报解析警告
2. `description` 保持**中英双语**——Claude Code 走语义匹配，其他 harness 多为关键词/向量匹配
3. 正文**零工具名**——不出现 Read/Write/Bash，只说"记录/读取/写入文件"
4. 只用**相对路径**，无脚本、无环境变量依赖
5. **记忆降级规则**必须保留——无文件能力时退回会话内记忆，且禁止假装已持久化

### 运行时产物

skill 在运行时会在自己旁边生成 `work-companion.md`（工作记忆，一行一条承诺）。这是**用户个人数据**，已在 `.gitignore` 排除——不要提交，也不要把它挪进仓库。

### 两个脚本层面的坑

- `install.ps1` 的输出**刻意只用 ASCII**：Windows PowerShell 5.1 会把 UTF-8 脚本按 ANSI 读，非 ASCII 输出会乱码。别"顺手"给它加中文提示。
- `install.sh` 用 `set -eu`，且网络兜底依赖 `curl` 或 `wget`（都没有时以退出码 3 结束）。

## 当前状态

`v0.1.0`：**只有壳**。SKILL.md 目前是纯提示词指令，承诺的解析、到期判断、周度汇总全靠模型当场理解，没有任何自动化实现。`CHANGELOG.md` 的「待办」列着真正要做的内核：

- 承诺解析、到期判断、周度汇总的自动化
- 记忆文件的跨会话同步
- codex / cursor 的路径验证（现为社区约定值，未实测）

改完记得同步 `README.md` 的能力表与 `CHANGELOG.md`——这两处最容易和实现脱节。
