# Snap.Genshin.WebAPI
General API designed for Snap.Genshin

## 测试API

- 在本地直接运行`run.bat`
- 可访问`http://127.0.0.1:8000/docs`以获取全部API

## 部署

- 在`setting.json`中修改`key`值
- 执行bash

```bash
docker build -f Dockerfile -t sg-api/test .
docker run -itp 3051:8080 \
    --name=test-sg-api \
    --mount type=bind,source="$(pwd)"/data,target=/code/data \
    --mount type=bind,source="$(pwd)"/config,target=/code/config \
    sg-api/test
```

