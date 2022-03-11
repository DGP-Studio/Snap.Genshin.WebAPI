# coding=utf8
from typing import Optional
import time
import json
import requests
import hashlib
from fastapi import FastAPI, Response, status
from pydantic import BaseModel

# 全局变量
cacheTime = 600
app = FastAPI()
# 内存缓存
AllReleaseDict = {}
GlobalStablePatch = {}
CNStablePatch = {}
LatestRelease = ""
LastCacheTimestamp = ""


class EncryptedPost(BaseModel):
    body: str
    key: str
    parameter: str


# 验证POST Key
def verifyKey(encryptedKey, keyParameter):
    with open("setting.json", 'r', encoding='utf-8') as setting_json:
        currentKey = json.load(setting_json)['key']
    # 加密方法
    keyValue = currentKey + keyParameter[::-1] + "masterain"
    correctKey = hashlib.md5(keyValue.encode('utf-8')).hexdigest()
    # 返回验证结果
    if encryptedKey == correctKey:
        return True
    else:
        return False


# 刷新全部Release数据
def refreshMeta():
    # 读取全部 Release
    githubAPIResult = requests.get("https://api.github.com/repos/DGP-Studio/Snap.Genshin/releases")
    releaseDict = {}

    # 设置判断 latest release变量
    # 将 latest release tag_name 写入内存
    global LatestRelease
    findFirstRelease = False

    # 遍历全部release并处理数据
    for release in json.loads(str(githubAPIResult.text)):
        # 寻找latest release
        if not findFirstRelease and not release["prerelease"]:
            findFirstRelease = True
            print("Latest release: " + release["tag_name"])
            LatestRelease = release["tag_name"]

        # 处理当前release数据
        thisReleaseDict = {"tag_name": release["tag_name"], "body": release["body"],
                           "browser_download_url": release["assets"][0]["browser_download_url"],
                           "asset_name": release["assets"][0]["name"]
                           }
        # 将当前 release 接入大字典，以tag_name为Key
        releaseDict[release['tag_name']] = thisReleaseDict
    # 在大字典中写入缓存时间
    releaseDict["cache_timestamp"] = str(int(time.time()))

    # 向文件缓存写入 JSON
    releaseJSON = json.dumps(releaseDict, ensure_ascii=False, indent=4)
    with open('patch-cache.json', 'w', encoding='utf-8') as json_file:
        json_file.write(releaseJSON)
    json_file.close()

    # 写入全局
    global AllReleaseDict, LastCacheTimestamp, GlobalStablePatch, CNStablePatch
    AllReleaseDict = releaseDict
    LastCacheTimestamp = releaseDict['cache_timestamp']
    thisRelease = AllReleaseDict[LatestRelease]
    GlobalStablePatch = {'tag_name': thisRelease['tag_name'], 'body': thisRelease['body'],
                         'browser_download_url': thisRelease['browser_download_url'],
                         'cache_timestamp': LastCacheTimestamp}
    CNStablePatch = {'tag_name': thisRelease['tag_name'], 'body': thisRelease['body'],
                     'browser_download_url':
                         'https://resource.snapgenshin.com/' + thisRelease['asset_name'],
                     'cache_timestamp': LastCacheTimestamp}

    # 返回大字典
    return releaseDict


# 检查元数据是否为空或过期
def checkMetaExpiration():
    global cacheTime
    if AllReleaseDict == {} or \
            (int(time.time()) - int(AllReleaseDict['cache_timestamp'])) > cacheTime:
        refreshMeta()


# 管理相关
@app.get('/admin/isOnline')
def isOnline():
    return {'online': True}


# 设置加密Key
@app.post("/admin/setKey", status_code=200)
def setAnnouncement(userSentData: EncryptedPost, response: Response):
    userSentData = userSentData.dict()
    if verifyKey(userSentData['key'], userSentData['parameter']):
        newSetting = {'key': userSentData['body']}
        setting_json = json.dumps(newSetting, ensure_ascii=False, indent=4)
        with open('setting.json', 'w', encoding='utf-8') as json_file:
            json_file.write(setting_json)
        json_file.close()
        return {'result': 'OK'}
    else:
        response.status_code = status.HTTP_403_FORBIDDEN
        return {'result': 'failed'}


# 全球区版本分发API
@app.get('/patch/stable/global')
def getPatchGlobal():
    checkMetaExpiration()
    global GlobalStablePatch
    return GlobalStablePatch


# 中国区版本分发API
@app.get('/patch/stable/cn')
def getPatchGlobal():
    checkMetaExpiration()
    global CNStablePatch
    return CNStablePatch


# 获取最新稳定版本的更新日志
@app.get("/patchNote/latest", status_code=200)
def getLatestPatchNote():
    checkMetaExpiration()
    global GlobalStablePatch
    noteBody = GlobalStablePatch['body']
    return {"body": noteBody}


# 获取指定版本的更新日志
@app.get("/patchNote/{version}", status_code=200)
def getVersionPatchNote(version: str):
    checkMetaExpiration()
    global AllReleaseDict
    note = AllReleaseDict[version]['body']
    return {"body": note}


# 设置公告
@app.post("/manifesto/announce", status_code=200)
def setManifesto(userSentData: EncryptedPost, response: Response):
    userSentData = userSentData.dict()
    if verifyKey(userSentData['key'], userSentData['parameter']):
        newAnnouncement = userSentData['body']
        with open('manifesto.txt', 'w', encoding='utf-8') as ann_file:
            ann_file.write(newAnnouncement)
        return {'result': 'OK'}
    else:
        response.status_code = status.HTTP_403_FORBIDDEN
        return {'result': 'failed'}


# 获取公告
@app.get("/manifesto")
def getManifesto():
    f = open("manifesto.txt", encoding='utf-8')
    text = f.read()
    f.close()
    return {"manifesto": text}
