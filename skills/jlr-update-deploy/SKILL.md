---
name: jlr-update-deploy
description: JLR 主分支推送成功后部署已提交的静态页面并验证站点。
---

在仓库根执行 `bash skills/jlr-update-deploy/deploy.sh`。脚本推送 main，随后将同一提交的首页和前端设计稿同步至 10.0.0.215 的 JLR 静态目录，验证两个页面均返回 HTTP 200。

部署机器需能访问内网并配置 SSH 密钥和可信主机记录。若沿用团队提供的密码，设置 JLR_DEPLOY_PASS 并安装 sshpass。密码不得写入仓库。若已推送而部署失败，可重新运行脚本。部署目标由服务器管理员维护 Nginx。
