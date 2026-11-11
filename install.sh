#!/usr/bin/env sh
# Work Companion — 一键安装脚本（macOS / Linux / Git Bash）
#
# 用法：
#   ./install.sh                          安装到 ~/.claude/skills/work-companion
#   ./install.sh --target codex           安装到 ~/.codex/skills/work-companion
#   ./install.sh --target all             安装到所有已识别的 harness
#   ./install.sh --dir /custom/skills     安装到自定义目录
#   ./install.sh --force                  目标已存在时覆盖
#
# 远程一键（仓库需公开，或设置 GITHUB_TOKEN）：
#   curl -fsSL https://raw.githubusercontent.com/EDboy-616/work-companion/main/install.sh | sh

set -eu

REPO="EDboy-616/work-companion"
BRANCH="main"
SKILL_NAME="work-companion"

TARGET="claude-code"
FORCE=0
CUSTOM_DIR=""

usage() {
  cat <<'EOF'
Work Companion 安装脚本

选项：
  --target <name>   安装目标：claude-code（默认）| codex | cursor | all | dir
  --dir <路径>     改用自定义目录（等价于 --target dir）
  --force          目标已存在时覆盖
  -h, --help       显示帮助
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="${2:-}"; [ -n "$TARGET" ] || { echo "缺少 --target 的值" >&2; exit 2; }; shift 2 ;;
    --dir)    CUSTOM_DIR="${2:-}"; [ -n "$CUSTOM_DIR" ] || { echo "缺少 --dir 的值" >&2; exit 2; }; TARGET="dir"; shift 2 ;;
    --force)  FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知参数：$1" >&2; usage; exit 2 ;;
  esac
done

# 定位源文件：优先使用脚本同目录的仓库副本（git clone 场景）
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SRC=""
if [ -f "$SCRIPT_DIR/skills/$SKILL_NAME/SKILL.md" ]; then
  SRC="$SCRIPT_DIR/skills/$SKILL_NAME/SKILL.md"
fi

download() {
  url="https://raw.githubusercontent.com/$REPO/$BRANCH/skills/$SKILL_NAME/SKILL.md"
  if command -v curl >/dev/null 2>&1; then
    if [ -n "${GITHUB_TOKEN:-}" ]; then
      curl -fsSL -H "Authorization: Bearer $GITHUB_TOKEN" "$url"
    else
      curl -fsSL "$url"
    fi
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- "$url"
  else
    echo "错误：需要 curl 或 wget 才能从远程下载" >&2
    exit 3
  fi
}

skills_dir_for() {
  case "$1" in
    claude-code) echo "$HOME/.claude/skills" ;;
    codex)       echo "$HOME/.codex/skills" ;;
    cursor)      echo "$HOME/.cursor/skills" ;;
    dir)         echo "$CUSTOM_DIR" ;;
    *)           echo "" ;;
  esac
}

install_one() {
  dest_dir="$1"
  [ -n "$dest_dir" ] || { echo "错误：目标目录为空" >&2; return 1; }
  dest="$dest_dir/$SKILL_NAME"

  if [ -f "$dest/SKILL.md" ] && [ "$FORCE" -ne 1 ]; then
    echo "已存在，跳过：$dest/SKILL.md（加 --force 可覆盖）"
    return 0
  fi

  mkdir -p "$dest"
  if [ -n "$SRC" ]; then
    cp "$SRC" "$dest/SKILL.md"
  else
    download > "$dest/SKILL.md"
  fi
  echo "已安装：$dest/SKILL.md"
}

case "$TARGET" in
  all)
    install_one "$HOME/.claude/skills"
    install_one "$HOME/.codex/skills"
    install_one "$HOME/.cursor/skills"
    ;;
  *)
    dir=$(skills_dir_for "$TARGET")
    if [ -z "$dir" ]; then
      echo "未知目标：$TARGET（可用：claude-code | codex | cursor | all | dir）" >&2
      exit 2
    fi
    install_one "$dir"
    ;;
esac

echo ""
echo "完成。请重启对应的 agent 使其生效。"
echo "卸载：删除上述 skills/$SKILL_NAME 目录即可。"
