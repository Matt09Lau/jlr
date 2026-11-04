#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
revision="$(git rev-parse --verify refs/heads/main)"
git -c http.version=HTTP/1.1 push origin "$revision:refs/heads/main"

stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
git archive "$revision" -- index.html 前端设计稿 | tar -xf - -C "$stage"

auth=()
if [[ -n "${JLR_DEPLOY_PASS:-}" ]]; then
  command -v sshpass >/dev/null || { echo '密码部署需要 sshpass' >&2; exit 1; }
  export SSHPASS="$JLR_DEPLOY_PASS"
  auth=(sshpass -e)
fi
ssh_options='ssh -o StrictHostKeyChecking=yes -o ConnectTimeout=10'
if [[ -z "${JLR_DEPLOY_PASS:-}" ]]; then
  ssh_options+=' -o BatchMode=yes'
fi
echo "正在部署 $revision"
${auth[@]+"${auth[@]}"} rsync -az --chmod=Da+rx,Fa+r -e "$ssh_options" \
  "$stage/" cjlruser@10.0.0.215:/home/cjlruser/jlr-web/

site='http://10.0.0.215:11000'
draft='/%E5%89%8D%E7%AB%AF%E8%AE%BE%E8%AE%A1%E7%A8%BF/JLR_%E4%B8%BB%E6%95%B0%E6%8D%AE%E5%89%8D%E7%AB%AF%E8%AE%BE%E8%AE%A1%E7%A8%BF.html'
for path in / "$draft"; do
  status="$(curl -fsS --max-time 15 -o /dev/null -w '%{http_code}' "$site$path")"
  [[ "$status" == 200 ]] || { echo "部署验证失败，HTTP $status：$path" >&2; exit 1; }
done
echo "部署验证通过：$site/"
