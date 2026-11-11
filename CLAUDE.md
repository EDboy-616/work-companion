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

装好后**通常不用重启**——本机实测目录一出现就被接管（"skill 不热重载"的说法在这个版本上不成立）。

试跑验收见 `TESTING.md`（用场景剧本代替测试）：说"这周五要交个方案"，回复里**必须**出现"我记下了"、且日期换成年月日；无持久记忆的环境里必须明说"只能在这次对话里帮你盯着"。

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

1. frontmatter **只有** `name` + `description`——不加 `version` / `allowed-tools` / `model` 等，部分 harness 会报解析警告（codex 内置的 `review-agent` 用的正是这两个字段，可作佐证）
2. `description` 保持**中英双语**，并写成**分层路由文案**——做什么 + 什么时候用 + 什么时候别用
3. 正文**零工具名**——不出现 Read/Write/Bash，只说"记录/读取/写入文件"
4. 不依赖绝对路径、脚本、环境变量
5. **记忆降级规则**必须保留——有自带记忆就用，只有文件读写就落清单，都没有则退回会话内记忆，且禁止假装已持久化

### 记忆：借环境的，不落仓库

skill **不自建记忆文件**——它把承诺交给当前环境自带的记忆能力保存，只规定每条要带的五样要素（内容 / 记录日 / 到期日 / 状态 / 提醒历史），存储格式由环境决定。所以仓库里不会出现运行时的记忆产物。

`.gitignore` 里仍保留 `work-companion.md` 的排除规则，是给"只有文件读写"的降级环境留的保险——那种环境会落成清单文件，别让它进仓库。

### 写这条提示词时最容易犯的错

**写出一条模型没有信号去执行的指令。** 已经栽过三次：「会话结束前主动说明」（模型感知不到会话何时结束）、「会话开始时读取记忆」（skill 靠触发加载，根本不存在"会话开始"这个时刻）。第三个是 2026-11-11 模拟试跑测出来的：「先看环境有什么记忆能力，再决定怎么做」——模型查不出自己身处什么环境。同一环境下它写时说「记忆只在这台电脑上」、被追问时又说「这个环境没有持久记忆，这次对话里帮你盯着」，两句都不是探测出来的，是碰出来的。

改法是**把判断依据收窄到它眼下看得见的东西**：上下文里有没有指明记忆位置、工具列表里有没有能写文件的工具；两个问题都答不上来，就按最保守的那一档办。同理，凡是要求它「感知环境」「感知会话边界」的句子，都要先问一句：**这个信号它现在拿得到吗？**

改 SKILL.md 时逐句自问：**这句话，它在当下有办法知道自己该动了吗？**

### 两个脚本层面的坑

- `install.ps1` 的输出**刻意只用 ASCII**：Windows PowerShell 5.1 会把 UTF-8 脚本按 ANSI 读，非 ASCII 输出会乱码。别"顺手"给它加中文提示。
- `install.sh` 用 `set -eu`，且网络兜底依赖 `curl` 或 `wget`（都没有时以退出码 3 结束）。

## 当前状态

`v0.2.0` 已发布：`main` 与 `dev` 同步在该提交上（2026-11-11 合并并推送）。`dev` 上另有一批**未发布**的修复，见 `CHANGELOG.md` 的「未发布」一节。SKILL.md 已从"只有壳"推进到完整可用：记忆交由环境、触发面收窄、边界与增强路径齐备、五类动作全部到位。仍是纯提示词，没有代码。

还欠的：

- **记忆的承重墙仍未验证**：借环境记忆这条假设，在**没有记忆机制的环境**里已实测退化成空声称（说了「我记下了」，什么都没存）；在真实 Claude Code 主会话里还没验过
- **行为走查**：`TESTING.md` 的 A–G 组只跑过一轮**模拟**（结论见 `TEST-RUN-2026-11-11.md`）。D 组（克制）、F 组、G 组，以及一切需要「已到期 / 隔天 / 隔周」时间推进的项，都还没跑——它们只能真实使用里走
- **cursor 路径**从未验证（本机没装 cursor）；codex 只验了结构，没验加载
- 记忆的跨机同步——当前版本明确不做，用户接受两台电脑各自失忆。**另有一层同样没做**：记忆按项目分（`~/.claude/projects/<项目路径>/memory/`），跨项目也读不到；同一个仓库算一个项目

改完记得同步 `README.md` 的能力表与 `CHANGELOG.md`——这两处最容易和实现脱节。
