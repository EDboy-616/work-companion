#!/usr/bin/env sh
# Work Companion — 一键安装脚本（macOS / Linux / Git Bash）
#
# 用法：
#   ./install.sh                          安装到 ~/.claude/skills/work-companion
#   ./install.sh --target codex           安装到 ~/.codex/skills/work-companion
#   ./install.sh --target all             安装到所有已识别的 harness
#   ./install.sh --dir /custom/skills     安装到自定义目录
#   ./install.sh --force                  目标已存在时覆盖
#   ./install.sh --with-scripts           同时安装可选的清单脚本（默认不装）
#
# 远程一键（仓库需公开，或设置 GITHUB_TOKEN）：
#   curl -fsSL https://raw.githubusercontent.com/EDboy-616/work-companion/main/install.sh | sh

set -eu

REPO="EDboy-616/work-companion"
BRANCH="main"
SKILL_NAME="work-companion"

TARGET="claude-code"
FORCE=0
WITH_SCRIPTS=0
CUSTOM_DIR=""

usage() {
  cat <<'EOF'
Work Companion 安装脚本

选项：
  --target <name>   安装目标，默认 claude-code。可选：
                      国际 claude-code | codex | cursor | gemini | opencode |
                           copilot | windsurf | agents | kiro | openclaw
                      国内 lingma | qoder | qoder-cn | codebuddy | trae | trae-cn |
                           qwen | iflow | minimax
                      all = 只装到本机确实存在的那些
                      dir = 配合 --dir 使用
  --dir <路径>     改用自定义目录（等价于 --target dir）
  --force          目标已存在时覆盖
  --with-scripts   同时安装可选的清单脚本（默认不装）
  -h, --help       显示帮助
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="${2:-}"; [ -n "$TARGET" ] || { echo "缺少 --target 的值" >&2; exit 2; }; shift 2 ;;
    --dir)    CUSTOM_DIR="${2:-}"; [ -n "$CUSTOM_DIR" ] || { echo "缺少 --dir 的值" >&2; exit 2; }; TARGET="dir"; shift 2 ;;
    --force)  FORCE=1; shift ;;
    --with-scripts) WITH_SCRIPTS=1; shift ;;
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

download_raw() {
  rel="$1"
  url="https://raw.githubusercontent.com/$REPO/$BRANCH/$rel"
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
    return 3
  fi
}

download() {
  download_raw "skills/$SKILL_NAME/SKILL.md"
}

install_script() {
  dest_dir="$1"
  dest_script="$dest_dir/$SKILL_NAME/scripts/ledger.py"
  local_script="$SCRIPT_DIR/skills/$SKILL_NAME/scripts/ledger.py"
  mkdir -p "$(dirname "$dest_script")"
  if [ -f "$local_script" ]; then
    if cp "$local_script" "$dest_script"; then
      echo "已安装（可选脚本）：$dest_script"
      return 0
    fi
    echo "警告：可选脚本复制失败，SKILL.md 仍可独立工作" >&2
    return 1
  fi
  tmp="$dest_script.tmp"
  if download_raw "skills/$SKILL_NAME/scripts/ledger.py" > "$tmp" 2>/dev/null && mv "$tmp" "$dest_script"; then
    echo "已安装（可选脚本）：$dest_script"
  else
    rm -f "$tmp"
    echo "警告：可选脚本下载或落盘失败，SKILL.md 仍可独立工作" >&2
    return 1
  fi
}

skills_dir_for() {
  case "$1" in
    # 国际
    claude-code) echo "$HOME/.claude/skills" ;;
    codex)       echo "$HOME/.codex/skills" ;;
    cursor)      echo "$HOME/.cursor/skills" ;;
    gemini)      echo "$HOME/.gemini/skills" ;;
    opencode)    echo "$HOME/.config/opencode/skills" ;;
    copilot)     echo "$HOME/.copilot/skills" ;;
    windsurf)    echo "$HOME/.codeium/windsurf/skills" ;;
    agents)      echo "$HOME/.agents/skills" ;;
    kiro)        echo "$HOME/.kiro/skills" ;;
    openclaw)    echo "$HOME/.openclaw/skills" ;;
    # 国内
    lingma)      echo "$HOME/.lingma/skills" ;;
    qoder)       echo "$HOME/.qoder/skills" ;;
    qoder-cn)    echo "$HOME/.qoder-cn/skills" ;;
    codebuddy)   echo "$HOME/.codebuddy/skills" ;;
    trae)        echo "$HOME/.trae/skills" ;;
    trae-cn)     echo "$HOME/.trae-cn/skills" ;;
    qwen)        echo "$HOME/.qwen/skills" ;;
    iflow)       echo "$HOME/.iflow/skills" ;;
    minimax)     echo "$HOME/.minimax/skills" ;;
    dir)         echo "$CUSTOM_DIR" ;;
    *)           echo "" ;;
  esac
}

# --target all：只装到本机确实存在的 harness（父目录存在才算）
ALL_TARGETS="claude-code codex cursor gemini opencode copilot windsurf agents kiro openclaw lingma qoder qoder-cn codebuddy trae trae-cn qwen iflow minimax"

install_detected() {
  installed=0
  for t in $ALL_TARGETS; do
    d=$(skills_dir_for "$t")
    parent=$(dirname "$d")
    if [ -d "$parent" ]; then
      echo "→ $t"
      install_one "$d"
      installed=$((installed + 1))
    fi
  done
  if [ "$installed" -eq 0 ]; then
    echo "没有检测到任何已知 harness 目录，什么都没装。" >&2
    echo "用 --target <name> 指定，或 --dir <路径> 手动指定目录。" >&2
    return 1
  fi
  echo "共安装到 $installed 个 harness。"
}

install_one() {
  dest_dir="$1"
  [ -n "$dest_dir" ] || { echo "错误：目标目录为空" >&2; return 1; }
  dest="$dest_dir/$SKILL_NAME"

  if [ -f "$dest/SKILL.md" ] && [ "$FORCE" -ne 1 ]; then
    echo "已存在，跳过：$dest/SKILL.md（加 --force 可覆盖）"
    if [ "$WITH_SCRIPTS" -eq 1 ]; then
      install_script "$dest_dir" || echo "警告：可选脚本安装失败，SKILL.md 未改动" >&2
    fi
    return 0
  fi

  mkdir -p "$dest"
  if [ -n "$SRC" ]; then
    cp "$SRC" "$dest/SKILL.md"
  else
    download > "$dest/SKILL.md"
  fi
  echo "已安装：$dest/SKILL.md"
  if [ "$WITH_SCRIPTS" -eq 1 ]; then
    install_script "$dest_dir" || echo "警告：可选脚本安装失败，SKILL.md 仍可独立工作" >&2
  fi
}

case "$TARGET" in
  all) install_detected ;;
  *)
    dir=$(skills_dir_for "$TARGET")
    if [ -z "$dir" ]; then
      echo "未知目标：$TARGET" >&2
      echo "可用：$ALL_TARGETS | all | dir" >&2
      exit 2
    fi
    install_one "$dir"
    ;;
esac

echo ""
echo "完成。请重启对应的 agent 使其生效。"
echo "卸载：删除上述 skills/$SKILL_NAME 目录即可。"
