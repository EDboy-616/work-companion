# 兼容性说明（COMPATIBILITY）

本 skill 的设计目标：**一份 SKILL.md，装到任何支持 skill 机制的 agent harness 里都能工作**。

## 兼容性设计决策

| 决策 | 原因 |
|------|------|
| frontmatter 只有 `name` + `description` | 这是各 harness 最通用的交集字段；`version`、`allowed-tools`、`model` 等字段仅部分环境支持，可能引起解析警告 |
| `description` 中英双语 | Claude Code 按语义匹配触发；其他 harness 多为关键词/向量匹配，英文短语覆盖更广 |
| 正文零工具名引用 | 不提 Read/Write/Bash 等任何 harness 专属工具，统一用"记录/读取/写入文件"等中性动词，由各环境自行映射到自己的工具 |
| 记忆自动降级 | 有文件系统 → 写 `work-companion.md`；没有（claude.ai 网页版等）→ 会话内记忆 + 结束时明确告知未持久化 |
| 相对路径 | 只用相对路径（与 SKILL.md 同目录），不依赖任何绝对路径或环境变量 |
| 无脚本依赖 | 纯 markdown 指令，不要求 Bash/Python/Node 等运行时 |

## 已知环境的适配情况

| 环境 | 安装方式 | 文件记忆 | 备注 |
|------|---------|---------|------|
| Claude Code (CLI) | 复制到 `~/.claude/skills/work-companion/` | ✅ 完整支持 | 推荐环境 |
| Claude 桌面版 (Skills) | 上传 SKILL.md 作为 skill | ✅ 视沙盒而定 | 若无文件权限自动降级 |
| claude.ai (网页) | 同上 | ❌ 自动降级为会话内记忆 | 每次新会话需重新告知承诺 |
| 其他 agent harness | 按其 skill 规范加载 SKILL.md | 取决于该环境的文件能力 | 指令本身无平台依赖 |

## 安装到新 harness 的检查清单

1. 确认该 harness 支持"把一段 markdown 指令注入对话"的机制（skill / custom instruction / system prompt 附加均可）
2. 把 SKILL.md 放入对应位置；若该环境用 YAML 头解析，保留 frontmatter 两字段即可
3. 若环境有持久目录，确认 `work-companion.md` 的写入位置并对用户可见
4. 试运行：说一句"这周五要交个方案"，确认 AI 回复中包含"我记下了"
5. 试运行降级：在无文件能力环境确认 AI 会说明"没有地方长期保存"
