如果改了service文件，需要重新加载系统管理器配置

# 1. 重新加载系统管理器配置
sudo systemctl daemon-reload

# 2. 设置开机自启
sudo systemctl enable pokeclaw.service

# 3. 立即启动服务
sudo systemctl start pokeclaw.service

# 4. 查看运行状态，确认是否启动成功
sudo systemctl status pokeclaw.service

---

如果改了.env文件，需要重启对应的 systemd 服务才能让新的环境变量生效

sudo systemctl restart pokeclaw.service