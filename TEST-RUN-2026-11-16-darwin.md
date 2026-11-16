# 达尔文评估记录（2026-11-16）

用 darwin-skill 2.1 对 `skills/work-companion/SKILL.md`（v0.4.0，76 行）做首次评估与优化。
记录留档：分数是 triage，keep/revert 走 paired 盲评。

## 环境与前置

- 目标：`skills/work-companion/SKILL.md`；基线 commit `3c1a008`，优化分支 `auto-optimize/20261116-2145`
- Runtime 红灯扫描：`SKILL.md` 命中 0；`README.md` 命中 3 行（`Claude Code 用户` / `在 Claude Code 中执行` / `/plugin install`），读上下文后判为**假阳性**——是"五选一安装方式"表格里描述第②种路径的行，同表还有 npx 跨 harness 与手动复制路径；记 `runtime_warn=0`
- 静态不变量复验：frontmatter 仅 `name` + `description`（description 441 字符、中英双语）；正文工具名/绝对路径/裸 `python` 命中 0；`scripts/ledger.py` 相对引用可达，`self-test ok`

## 测试 prompt

写入 `skills/work-companion/test-prompts.json`，三组：

1. 记录 → 查询 → 明确收尾（多轮）
2. 边界：不该记的两类 + 删除与作废必须分得开
3. 失败模式：未要求定时不许诺 / 只给日期没给时刻

## 基线（Phase 1）

- 结构 9 维（两位独立评委，互不知情）：两人总分均为 **65.1**（同分纯属巧合，但 top_gap 不同——A 指 dim4、B 指 dim5，共识是 dim3 缺清单损坏恢复路径、dim4 缺显性关卡）
- dim8 实测（独立评委读四份转录）：**8/10**
  - 三组 with-skill 全过：日期换算（11-20 周五 / 11-18 周三 / 11-23 下周一）、首次报完整路径、两段查询、`算了`→已作废、`忘了吧`→整行删除且只回"好"、定时任务带"到点先读清单"的守卫文本
  - 干净 baseline（无 skill、隔离目录）也完成了基础记录与换算，但只有 checklist——无五字段、无状态机、无"该记/不该记"边界；skill 的增量正落在这些结构上
  - **暴露缺陷**：用户说"20 号那天提醒我"，模型自行定为 09:00 并挂任务——未经确认的假设
- 折算总分：**83.5**（结构 65.1/77 + dim8 8×23/10）

## 优化（Phase 2）

### 第 1 轮 · dim4 检查点（含 dim8 暴露的 09:00 假设）

- 改动：§四 表前新增「🔴 反问点」——日期歧义 / 多候选匹配 / 定时缺时刻，同一问题只问一次；①② 当轮不写盘，③ 先记条目不挂任务。定时信号放宽为"给出日期或时点"，禁止自己挑时刻；§七 补"问了不答就先记下、不挂"
- paired 盲评（3 位独立评委，A/B 位置随机）：**3-0 better**，两票 clear、一票 slight
- 评委指出的附带张力（"不写盘" vs "只记录、不挂"）已在本轮内收紧措辞

### 第 2 轮 · dim5 具体性

- 改动：§三 清单路径去掉"如"，钉死为相对主目录的 `work-companion/commitments.md`；§五 补一行收尾句形状示例（不含绝对日期，避免被当成真实条目）
- paired 盲评：**3-0 better**，三票均 slight → 按 HL-4 边际收益收手
- 未采纳：评委建议的查询输出成句示例。理由是 SKILL.md 里写带日期的示例条目，会重演 2026-11-11"报出只存在于 `TESTING.md` 台词里的承诺"那类事故

## 结果

- `SKILL.md` 76 → 79 行；能力与状态机未增删
- 两轮均 keep；版本升 0.4.1，文档按仓库纪律两头改（README / COMPATIBILITY / TESTING / CLAUDE / CHANGELOG + 两处 JSON）
- **仍欠**：E4 与反问点在真实 harness 复跑；时间推进（隔天/到期当天）从未跑过；codex/cursor 实际加载未验

## 给下一轮的提醒

- 判 dim4 时注意：这个 skill 刻意不打断用户，**只有三处**该停下来问；不要为了 rubric 分把"删除前确认"加进来——`TESTING.md` C2 要求"忘了吧"当轮整行删除
- 实测隔离很关键：子 agent 会自己发现仓库里的 `ledger.py`，baseline 会被污染；本轮第一次 baseline 即因此作废，改用隔离目录 + 明令禁读仓库后重跑
- 子 agent 会**真的创建定时任务**（本轮实测 3 创建了 `wc-remind-release-20261120`）；测试后必须清场