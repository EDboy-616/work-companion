# Work Companion（工作伴侣）

一个 skill：秘书型的工作伴侣。在用户与 AI 日常协作的过程中，默默记录承诺、
主动分析总结、在合适的时机给建议和提醒——但不唠叨、不打断、不翻旧账。

支持多种 harness（Claude Code / 桌面版 / 其他 agent 框架），一份 `SKILL.md` 通用。

## 它是什么

不是工具，更像一个**平级的工作伙伴**：平时默默跟着协作，当对话出现合适的时机时，
它才轻声插一句。它的定位介于“秘书”与“老同事”之间：

- 像秘书——记录你答应过的事，到期主动提醒，定期给你做工作小结
- 像老同事——只在你亲口说过的事上开口，从不凭空猜测、不替你规划

## 核心能力

| 能力 | 说明 |
|------|------|
| 承诺跟踪 | 你说“周五要交个方案”，它记下、到期提醒、完成后勾选归档 |
| 阶段小结 | 话题收尾或连续完成几件事时，用 2-3 句复盘做了什么、卡在哪 |
| 周度回顾 | 每周五或连续多日工作后，给一段本周小结和下周优先级建议 |
| 模式发现 | 记录累积后，发现反复出现的阻塞或习惯，温和指出（同一模式只提一次） |
| 情绪接应 | 你说“烦”“来不及了”时只共情不推进，把选择权留给你 |

## 设计原则

1. **透明**——每次记录都明确告诉你“我记下了：xxx”，记忆存在你自己的环境里，随时可查看、可清除
2. **克制**——每次对话最多主动插一句；被忽略一次即永久静默该条
3. **不翻旧账**——提醒用“事实+留白”措辞（“周五的方案，需要我先准备什么吗？”），不施压
4. **可撤销**——你说“忘了吧”，立即删除且永不复现
5. **只记事实**——只记承诺原话，不记情绪、不做猜测

## 安装（五选一）

| 方式 | 适合谁 | 命令 |
|------|--------|------|
| ① 一键脚本 | 想省事 | `./install.sh` 或 `.\install.ps1` |
| ② 官方 plugin marketplace | Claude Code 用户 | `/plugin marketplace add EDboy-616/work-companion` |
| ③ npx 通用安装器 | 跨 harness | `npx skills add EDboy-616/work-companion` |
| ④ git clone | 要审计/锁版本 | 见下 |
| ⑤ 手动复制 | 全手动控制 | 见下 |

### ① 一键脚本

**macOS / Linux / Git Bash：**

```bash
git clone https://github.com/EDboy-616/work-companion.git && cd work-companion && ./install.sh
```

**Windows PowerShell：**

```powershell
git clone https://github.com/EDboy-616/work-companion.git; cd work-companion; .\install.ps1
```

常用参数：

```bash
./install.sh --target all        # 装到所有已识别的 harness
./install.sh --target codex      # 指定 harness
./install.sh --dir ~/my/skills   # 自定义目录
./install.sh --force             # 覆盖已存在的版本
```

### ② 官方 plugin marketplace（Claude Code）

在 Claude Code 中执行：

```
/plugin marketplace add EDboy-616/work-companion
/plugin install work-companion@work-companion-marketplace
```

> 仓库当前为**私有**，`marketplace add` 需要你的 GitHub 凭据已在本机登录。

### ③ npx 通用安装器（跨 harness）

```bash
npx skills add EDboy-616/work-companion
```

> 由第三方工具 [vercel-labs/skills](https://github.com/vercel-labs/skills) 提供，
> 支持 Claude Code、Cursor、Codex、Copilot 等 20+ agent。私有仓库需先登录 GitHub。

### ④ git clone（可审计）

```bash
git clone https://github.com/EDboy-616/work-companion.git ~/src/work-companion
cp -r ~/src/work-companion/skills/work-companion ~/.claude/skills/
```

更新：`cd ~/src/work-companion && git pull && cp -r skills/work-companion ~/.claude/skills/`

### ⑤ 手动复制

把 `skills/work-companion/` 整个目录复制到目标 harness 的 skills 目录：

| harness | 常见路径 |
|---------|---------|
| Claude Code | `~/.claude/skills/` |
| Codex | `~/.codex/skills/` |
| Cursor | `~/.cursor/skills/` |

> Codex / Cursor 路径为社区约定值，若与实际不符请以该工具文档为准。

安装后重启对应 agent 即可生效。

## 文件结构

```
.claude-plugin/
├─ plugin.json        # 插件 manifest（name / version / description）
└─ marketplace.json   # 官方 marketplace 入口
skills/
└─ work-companion/
   └─ SKILL.md        # skill 唯一源文件
install.sh            # macOS / Linux 安装脚本
install.ps1           # Windows 安装脚本
COMPATIBILITY.md      # 兼容性说明：环境适配表与安装检查清单
TESTING.md            # 试跑剧本（用场景代替测试）
CLAUDE.md             # 仓库指引（面向后续的开发实例）
CHANGELOG.md
```

记忆**不自建文件**：skill 把承诺交给当前环境自带的记忆能力保存，只规定每条要带的要素，格式由环境决定。记忆留在本机，不随仓库同步。

## 跨 harness 兼容

SKILL.md 刻意做了平台中立：frontmatter 只有通用字段、正文零工具名引用、
相对路径、无脚本依赖，并内置记忆降级规则（无文件能力的环境自动退回会话内记忆）。
详见 [COMPATIBILITY.md](COMPATIBILITY.md)。

## 隐私

- 记忆存在**你自己的环境里**——用该环境自带的记忆能力，skill 不自建文件、不外发
- 记忆**只在本机**：不随仓库同步，也不随 skill 分发；仓库内不含任何个人工作数据
- 只记承诺原话与事实，不记情绪、不做猜测；你说“忘了吧”即删除

## License

Private / personal use.
