# 项目协作约定

- 用户要求：每次完成代码修改并通过必要检查后，自动创建本地 Git 提交并推送到 GitHub。
- 提交只包含本次任务的相关修改，不夹带用户无关改动。
- 用户已授权每次修改后自动推送到 GitHub；推送失败时保留本地提交并说明原因，不强制推送覆盖远程历史。
- 每次提交到 main 后，按 [JLR 更新部署 skill](skills/jlr-update-deploy/SKILL.md) 执行 `bash skills/jlr-update-deploy/deploy.sh`，由该脚本完成 GitHub 推送、内网部署及 HTTP 验证。部署失败时分别报告推送与部署状态。
