# Snap.Genshin.WebAPI
General API designed for Snap.Genshin

**Snap Genshin API服务器后端当前需要更多开发者，如果你有Python编程经验并熟悉SQL，欢迎加入开发群**

## 测试API

- 在本地直接运行`run.bat`
- 可访问`http://127.0.0.1:8000/docs`以获取全部API

## 部署

- 在`setting.json`中修改`key`值
- 执行bash

```bash
cd /data/wwwroot/api.snapgenshin.com
fusermount --u /data/wwwroot/api.snapgenshin.com/data/od21/
rm -rf backup/*
mv -f * backup/
git clone https://github.com/DGP-Studio/Snap.Genshin.WebAPI
mv Snap.Genshin.WebAPI/* .
rm -rf Snap.Genshin.WebAPI
docker build -f Dockerfile -t sg-api/1.7 .
docker run -itp 3051:8080 \
    --name=SG-API-1.7 \
    --mount type=bind,source="$(pwd)"/data,target=/code/data \
    --mount type=bind,source="$(pwd)"/config,target=/code/config \
    sg-api/1.7
cp backup/data/* data/
cp backup/config/* config/
mkdir data/od21
rclone mount SGODChina:snapgenshin/ /data/wwwroot/api.snapgenshin.com/data/od21/ --daemon
docker restart SG-API-1.7
```

