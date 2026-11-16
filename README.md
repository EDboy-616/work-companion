# Work Companion（工作伴侣）

一个 skill，只干一件事：**别让你答应过的事被忘掉**。

它记下你亲口说过的承诺、自己的任务，以及你明确要求盯着的人情跟进；在你问起时列全，在你说出明确收尾词时顺带提一句。
不催、不打断、不替你规划。支持多种 harness（Claude Code / 桌面版 / 其他 agent 框架），一份 `SKILL.md` 通用。

## 它是什么

更像一个**记性好、嘴不碎的老同事**：

- 你说过"周五要交方案"，它当场换算成绝对日期记进一份清单
- 你说"我要把报告写完"，它当成自己的任务记下；说"提醒我周三催他"，它记成待跟进
- 你问"我有什么没做的"，它分"你要做的"和"等对方"两段列全
- 话题正好收尾，而清单里有件事已经逾期或三天内要到期——它在回复末尾顺带提一句
- 除此之外它不开口：不主动催进度、不分析你的工作模式、不安抚情绪

后面那三件它以前写过，2026-11-12 全删了——原因是模型没有可靠的信号去判断"现在该不该做"，写出来只会变成瞎猜或空许诺。教训记在 [CLAUDE.md](CLAUDE.md)。

## 核心能力（四个动作，没有别的）

| 动作 | 什么时候发生 |
|------|--------------|
| **当场记下** | 你亲口说出承诺、自己的任务，或明确要求盯着某个跟进时。**只有这一轮真的写进清单了**，它才说"我记下了" |
| **收尾顺带一句** | 用户说出明确收尾词时（`先这样`／`收工`／`就这样`／`今天到这`／`先到这`／`没别的了`；**纯闲聊、纯问答不算；录入那一轮不算，下一轮按正常收尾判断**），且清单里有**未完成或待跟进**并已逾期／今天到期／三天内到期的条目，或有**等待对方**且对方承诺日已到／已过的条目。一次最多一句，**那一句里只说一条**；同一件事在同一段对话里最多主动提一次；话题正热时不打断 |
| **被问就列全** | 你说"我有什么没做的"，分两段列：**你要做的**（未完成＋待跟进）、**等对方**（等待对方），段内按到期日排；作废的不列，删掉的连提都不提 |
| **定时唤起** | **仅在你明确要求时**才挂一次性任务，挂上后告诉你什么时候会响；挂不上就直说。你没要求，它不会许诺"到期那天我叫你" |

每条记录带五个要素：**内容 / 记录日 / 到期日 / 状态 / 提醒历史**。到期日可以空着（写 `—`），空日期的条目不主动提醒。相对日期当场换算成绝对日期，有歧义当场反问一次（只问一次，不猜）。

**记哪三类**：承诺（答应别人或自己认下、对他人有交付的事）、任务（自己要做、没有外部交付对象的事）、跟进（涉及别人且你明确要求盯着的事）。只说"他答应我周五给报价"、没让你盯，不记；说"到时提醒我"才记成**等待对方**，说"提醒我周三催他"记成**待跟进**。指给 AI 的请求（"帮我看看文件"）不记。

## 清单存在哪

一个**与你当前项目无关的固定位置**——你的主目录下，文件名固定，例如 `work-companion/commitments.md`（文件名沿用旧版，里面现在也装任务与跟进）。**本会话第一次写入的那一轮它就把完整路径报给你**（只说一次），不用你自己去翻。

- **不会写进你当前的工作目录**：那是你的项目，不该凭空多出文件；而且你换个目录清单就断了
- **先读再写，绝不整份覆盖**：改期改原条目、完成改状态、作废打标记
- **与环境自带的记忆分工**：项目知识、代码偏好那类交给环境自己的记忆；这份清单只管"你答应要办的事、自己的任务、要盯的跟进"。同一件事两边都碰得到时，以清单为准
- **可选脚本**：同一 skill 目录下带一个 `scripts/ledger.py`，装上后可以用它安全读写和校验清单；没装或跑不起来，文本规则照样完整工作。安装时加 `--with-scripts`（PowerShell 用 `-WithScripts`）

状态有五种：**未完成 / 已完成 / 已作废 / 等待对方 / 待跟进**。**等待对方**是球在对方手里（等交付或回复），**待跟进**是轮到你开口去问或催。走法：**完成**只勾选不删除 · **改期**更新原条目（旧日期进提醒历史）· **"算了不做了"**标记作废（不再提醒，但仍看得见）· **"忘了吧"**整条删除，此后连"那条已经删了"这种提及都不许出现 · **等待对方到期未回复**不改状态，收尾时可以问一句"要不要问一下" · **两件事记成了一条** → 信息并进保留的那条、另一行直接删掉，不拿"已作废"当"已合并"用。

### 可选清单脚本

`skills/work-companion/scripts/ledger.py` 是个纯标准库的 Python 3 小工具，装不装都不影响 skill 工作。装上后可以做机械活：`query` 按"你要做的／等对方"两段列未结项、`list` 列全部、`add` 追加、`update` 改状态/改期/删除、`validate` 查字段与重复、`due --within 3` 算收尾窗口、`self-test` 自测。它用文件锁和原子替换写入，避免两个会话同时写时丢条目。

## 设计原则

1. **说到才做，做不到就直说**——"我记下了"必须钉在写入这个动作上；环境没有可写的地方，就改口"只能在这次对话里帮你盯着"
2. **顺带，不是催促**——措辞是"事实 + 轻问"（"周五的方案今天到期，需要我先准备什么吗？"），不施压
3. **只记你自己或你要求盯的事**——你转述给客户的 deadline 照记；别人答应你的不记，除非你说"到时提醒我"或"提醒我催他"
4. **用你的原词**——不改写、不猜测、不做心理分析
5. **不替你规划**——按到期日列，不说"你应该先做哪个"
6. **可撤销**——删除就是删除，永不复现

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
./install.sh --with-scripts      # 连同可选的清单脚本一起装
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

装好后通常不用重启——本机实测目录一出现就被接管；不放心就重启对应 agent。

## 文件结构

```
.claude-plugin/
├─ plugin.json        # 插件 manifest（name / version / description）
└─ marketplace.json   # 官方 marketplace 入口
skills/
└─ work-companion/
   ├─ SKILL.md        # skill 核心源文件
   └─ scripts/
      └─ ledger.py    # 可选清单 CLI（查询/读写/校验/到期筛选）
install.sh            # macOS / Linux 安装脚本
install.ps1           # Windows 安装脚本
COMPATIBILITY.md      # 兼容性说明：环境适配表与安装检查清单
TESTING.md            # 试跑剧本（用场景代替测试）
TEST-RUN-2026-11-13.md # 上一轮试跑记录（v0.3.1 修后复验 + 并发首跑）
TEST-RUN-2026-11-12.md # 更早一轮试跑记录（暴露五个问题的原始报告）
CLAUDE.md             # 仓库指引（面向后续的开发实例）
CHANGELOG.md
```

运行时那份 `commitments.md` **不在这个仓库里，也不该在**——它在你的主目录，含你的个人工作数据，`.gitignore` 已排除。

## 跨 harness 兼容

SKILL.md 刻意做了平台中立：frontmatter 只有通用字段、正文零工具名引用、相对路径；**核心行为不依赖脚本**，随附的 `scripts/ledger.py` 只是可选增强。内置降级规则——需要落盘却写不进去时，它只在这一次对话里盯着，并明说是这样。
详见 [COMPATIBILITY.md](COMPATIBILITY.md)。

## 隐私

- 清单写在**你自己的机器上**（主目录下一个固定路径），skill 不上传、不外发
- **跨项目共用一份**：它落在与项目无关的位置，所以在哪个仓库里干活都读得到同一份清单
- **跨电脑不同步**：两台电脑各写各的，这是当前版本明确不做的部分
- 只记承诺/任务/跟进的原话与日期，不记情绪、不做猜测；说"忘了吧"即整条删除，永不复现
- 可选脚本只在本地读写清单，不联网、不上传

## License

Private / personal use.
