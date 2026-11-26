#!/usr/bin/env bash
# 推送前自动核验：保护有效数据完整无缺。
# 由 .githooks/pre-push 调用；也可独立执行做预检。
# 设计原则：仅阻断"损坏/未提交/冲突/进行中操作"，不阻断历史债务与正常同步。

set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1

BLOCK=0
fail() { echo "  [BLOCK] $*" >&2; BLOCK=$((BLOCK + 1)); }
warn() { echo "  [WARN ] $*"; }
ok()   { echo "  [OK   ] $*"; }

echo "pre-push-verify: 开始推送前自动核验..."

# 1. 工作区无未提交改动（未跟踪文件不阻断）
if git diff --quiet && git diff --cached --quiet; then
    ok "工作区无未提交改动（tracked 文件干净）"
else
    fail "工作区存在未暂存或未提交的改动，请先提交或 stash"
fi

# 2. 无进行中的 merge / rebase / cherry-pick / revert
GIT_DIR="$(git rev-parse --git-dir)"
BUSY=""
for marker in MERGE_HEAD rebase-merge rebase-apply CHERRY_PICK_HEAD REVERT_HEAD BISECT_LOG; do
    [ -e "$GIT_DIR/$marker" ] && BUSY="$BUSY $marker"
done
if [ -z "$BUSY" ]; then
    ok "无进行中的 merge/rebase/cherry-pick/revert/bisect 操作"
else
    fail "检测到进行中的操作:$BUSY，请先完成或终止"
fi

# 3. 无未解决冲突（index 无 unmerged entries）
UNMERGED="$(git ls-files -u)"
if [ -z "$UNMERGED" ]; then
    ok "无未解决的冲突（index 无 unmerged entries）"
else
    fail "存在未解决的冲突，请先解决"
fi

# 4. 所有引用可解析（本地 + 远端跟踪 + 全部 tag）
BROKEN=0
while IFS= read -r ref; do
    if ! git rev-parse -q --verify "$ref" >/dev/null 2>&1; then
        echo "        损坏引用: $ref" >&2
        BROKEN=$((BROKEN + 1))
    fi
done < <(git for-each-ref --format='%(refname)')
if [ "$BROKEN" -eq 0 ]; then
    ok "全部引用可解析（$(git for-each-ref --format='%(refname)' | wc -l | tr -d ' ') 个）"
else
    fail "$BROKEN 个引用无法解析"
fi

# 5. fsck 无损坏类错误（dangling/unreachable 为历史债务，不阻断）
FSCK_ERR="$(git fsck --no-dangling 2>&1 | grep -v '^unreachable ' | grep -v '^dangling ' || true)"
if [ -z "$FSCK_ERR" ]; then
    ok "git fsck 无损坏类错误"
else
    echo "$FSCK_ERR" >&2
    fail "git fsck 报告损坏类错误"
fi

# 提示性检查（不阻断）
STASH_COUNT="$(git stash list | wc -l | tr -d ' ')"
[ "$STASH_COUNT" -gt 0 ] && warn "存在 $STASH_COUNT 个 stash（不阻断推送）"
UNTRACKED="$(git ls-files --others --exclude-standard | wc -l | tr -d ' ')"
[ "$UNTRACKED" -gt 0 ] && warn "存在 $UNTRACKED 个未跟踪文件（不阻断推送）"

if [ "$BLOCK" -gt 0 ]; then
    echo "pre-push-verify: 核验未通过（$BLOCK 项阻断），推送已取消。" >&2
    exit 1
fi

echo "pre-push-verify: 全部核验通过，允许推送。"
exit 0
