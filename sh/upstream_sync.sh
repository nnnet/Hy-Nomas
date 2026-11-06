#!/usr/bin/env bash
set -euo pipefail

EXPECTED_UPSTREAM="https://github.com/Tencent-Hunyuan/Hy-Nomas.git"
EXPECTED_ORIGIN_RE='github\.com[:/]nnnet/Hy-Nomas(\.git)?$'

die() {
    printf 'upstream-sync: %s\n' "$*" >&2
    exit 1
}

repo_root() {
    git rev-parse --show-toplevel
}

verify_remotes() {
    local upstream_fetch upstream_push origin_fetch
    upstream_fetch="$(git remote get-url upstream)"
    upstream_push="$(git remote get-url --push upstream)"
    origin_fetch="$(git remote get-url origin)"

    [[ "$upstream_fetch" == "$EXPECTED_UPSTREAM" ]] || \
        die "unexpected upstream fetch URL: $upstream_fetch"
    [[ "$upstream_push" == "DISABLED" ]] || \
        die "upstream push URL must be DISABLED, got: $upstream_push"
    [[ "$origin_fetch" =~ $EXPECTED_ORIGIN_RE ]] || \
        die "origin must be nnnet/Hy-Nomas, got: $origin_fetch"
    [[ "$(git config --get branch.main.remote)" == "upstream" ]] || \
        die "local main must track upstream"
}

require_clean() {
    [[ -z "$(git status --porcelain --untracked-files=all)" ]] || \
        die "working tree is not clean; commit or deliberately discard changes first"
}

verify_main() {
    [[ "$(git rev-parse main)" == "$(git rev-parse upstream/main)" ]] || \
        die "local main does not match upstream/main"
}

verify_overlay() {
    local path bad=0
    while IFS= read -r path; do
        [[ -n "$path" ]] || continue
        if git cat-file -e "upstream/main:$path" 2>/dev/null; then
            printf 'tracked upstream path changed locally: %s\n' "$path" >&2
            bad=1
        fi
    done < <(
        {
            git diff --name-only --diff-filter=MD upstream/main...HEAD
            git diff --name-only --diff-filter=MD
            git diff --cached --name-only --diff-filter=MD
        } | sort -u
    )
    [[ "$bad" -eq 0 ]] || die "integration branch modifies upstream-owned files"
}

check_all() {
    verify_remotes
    verify_main
    verify_overlay
    printf 'upstream-sync check: OK\n'
}

sync_integration() {
    local branch
    verify_remotes
    require_clean
    branch="$(git branch --show-current)"
    [[ -n "$branch" && "$branch" != "main" ]] || \
        die "run sync from an integration branch, never from main"
    git fetch --prune upstream
    git branch --force main upstream/main
    git -c rebase.autoStash=false rebase upstream/main
    check_all
    printf 'rebased %s; review and push it to origin explicitly\n' "$branch"
}

sync_fork_main() {
    verify_remotes
    require_clean
    git fetch --prune upstream
    git branch --force main upstream/main
    git push origin upstream/main:main
    verify_main
}

cd "$(repo_root)"
case "${1:-check}" in
    check)
        check_all
        ;;
    sync)
        sync_integration
        ;;
    sync-fork-main)
        sync_fork_main
        ;;
    *)
        die "usage: $0 {check|sync|sync-fork-main}"
        ;;
esac
