# coding=utf8
from typing import Optional
import re
import os
import time
import json
import requests
import hashlib
from fastapi import FastAPI, Response, status, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.characters import crawler
# from fastapi import Depends, FastAPI, HTTPException
# from sqlalchemy.orm import Session

# from . import crud, models, schemas
# from .database import SessionLocal, engine

# models.Base.metadata.create_all(bind=engine)

# Application
description = """
Snap Genshin Web API

## About us
[Snap Genshin](https://www.snapgenshin.com/)

About this API: [https://github.com/DGP-Studio/Snap.Genshin.WebAPI](https://github.com/DGP-Studio/Snap.Genshin.WebAPI)


"""
app = FastAPI(
    title="SnapGenshinWebAPI",
    description=description,
    version="1.8.2",
    redoc_url=None,
    #docs_url=None,
    terms_of_service="https://www.snapgenshin.com/documents/statement/user-privacy-notice.html",
    license_info={
        "name": "MIT License",
        "url": "https://github.com/DGP-Studio/Snap.Genshin.WebAPI/blob/main/LICENSE",
    },
)

# 全局变量
cacheTime = 180
charactersCacheTime = 7 * 24 * 60 * 60
# 内存缓存 - 版本分发
AllReleaseDict = {}
GlobalStablePatch = {}
CNStablePatch = {}
LatestRelease = ""
LastPatchCacheTimestamp = ""
# 内存缓存 - 角色JSON
LastCharactersVersionCheckTime = 0
LastCharactersVersionMakeTime = 0
LatestCharactersVersion = ""
# 内存缓存 - 测试角色JSON
LastBetaCharactersVersionCheckTime = 0
LastBetaCharactersVersionMakeTime = 0
LatestBetaCharactersVersion = ""
# CharactersDict = ""
# 内存缓存 - 公告
manifestoCache = ""
# 全局变量 - 插件库
with open("./config/config.json", 'r', encoding='utf-8') as setting_json:
    ACCEPT_PLUGINS = json.load(setting_json)['accepted-plugin']
# 内存缓存
PluginVersionCache = {}
for plugin in ACCEPT_PLUGINS:
    PluginVersionCache[plugin] = ""


class EncryptedPost(BaseModel):
    body: str
    key: str
    parameter: str


# 验证POST Key
def verifyKey(encryptedKey, keyParameter):
    with open("./config/config.json", 'r', encoding='utf-8') as setting_json:
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
def refreshPatchMeta():
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
        if findFirstRelease and release["tag_name"] != LatestRelease:
            patchNoteBody = "该版本已不是最新版本，请更新至最新版！！！\n"
        else:
            patchNoteBody = ""
        thisReleaseDict = {"tag_name": release["tag_name"], "body": patchNoteBody + release["body"],
                           "browser_download_url": release["assets"][0]["browser_download_url"],
                           "asset_name": release["assets"][0]["name"]
                           }
        # 将当前 release 接入大字典，以tag_name为Key
        releaseDict[release['tag_name']] = thisReleaseDict
    # 在大字典中写入缓存时间
    releaseDict["cache_timestamp"] = str(int(time.time()))

    # 向文件缓存写入 JSON
    releaseJSON = json.dumps(releaseDict, ensure_ascii=False, indent=4)
    with open('./data/patch-cache.json', 'w', encoding='utf-8') as json_file:
        json_file.write(releaseJSON)
    json_file.close()

    # 写入全局
    global AllReleaseDict, LastPatchCacheTimestamp, GlobalStablePatch, CNStablePatch
    AllReleaseDict = releaseDict
    LastPatchCacheTimestamp = releaseDict['cache_timestamp']
    thisRelease = AllReleaseDict[LatestRelease]
    GlobalStablePatch = {'tag_name': thisRelease['tag_name'], 'body': thisRelease['body'],
                         'browser_download_url': thisRelease['browser_download_url'],
                         'cache_timestamp': LastPatchCacheTimestamp}
    CNStablePatch = {'tag_name': thisRelease['tag_name'], 'body': thisRelease['body'],
                     'browser_download_url':
                         'https://resource.snapgenshin.com/' + thisRelease['asset_name'],
                     'cache_timestamp': LastPatchCacheTimestamp}

    # 返回大字典
    return releaseDict


# 检查元数据是否为空或过期
def checkPatchMetaExpiration():
    global cacheTime
    if AllReleaseDict == {} or \
            (int(time.time()) - int(AllReleaseDict['cache_timestamp'])) > cacheTime:
        refreshPatchMeta()


# 设置主页
# app.mount("/", StaticFiles(directory="static", html=True), name="static")


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
        with open('./config/config.json', 'w', encoding='utf-8') as json_file:
            json_file.write(setting_json)
        json_file.close()
        return {'result': 'OK'}
    else:
        response.status_code = status.HTTP_403_FORBIDDEN
        return {'result': 'failed'}


@app.post("/admin/freshPatchCache", status_code=200)
def forceRefreshCache(userSentData: EncryptedPost, response: Response):
    userSentData = userSentData.dict()
    if verifyKey(userSentData['key'], userSentData['parameter']):
        refreshPatchMeta()
        return {'result': 'refresh cache successfully'}
    else:
        response.status_code = status.HTTP_403_FORBIDDEN
        return {'result': 'failed'}


# 全球区版本分发API
@app.get('/patch/stable/global')
def getPatchGlobal():
    checkPatchMetaExpiration()
    global GlobalStablePatch
    return GlobalStablePatch


# 中国区版本分发API
@app.get('/patch/stable/cn')
def getPatchGlobal():
    checkPatchMetaExpiration()
    global CNStablePatch
    return CNStablePatch


# 获取最新稳定版本的更新日志
@app.get("/patchNote/latest", status_code=200)
def getLatestPatchNote():
    checkPatchMetaExpiration()
    global GlobalStablePatch
    noteBody = GlobalStablePatch['body']
    return {"body": noteBody}


# 获取指定版本的更新日志
@app.get("/patchNote/{version}", status_code=200)
def getVersionPatchNote(version: str):
    checkPatchMetaExpiration()
    global AllReleaseDict
    note = AllReleaseDict[version]['body']
    return {"body": note}


# 设置公告
@app.post("/manifesto/announce", status_code=200)
def setManifesto(userSentData: EncryptedPost, response: Response):
    global manifestoCache
    userSentData = userSentData.dict()
    if verifyKey(userSentData['key'], userSentData['parameter']):
        newAnnouncement = userSentData['body']
        with open('./data/manifesto.txt', 'w', encoding='utf-8') as ann_file:
            ann_file.write(newAnnouncement)
        manifestoCache = newAnnouncement[:]
        return {'result': 'OK'}
    else:
        response.status_code = status.HTTP_403_FORBIDDEN
        return {'result': 'failed'}


# 获取公告
@app.get("/manifesto")
def getManifesto():
    global manifestoCache
    if manifestoCache == "":
        f = open("./data/manifesto.txt", encoding='utf-8')
        text = f.read()
        f.close()
        manifestoCache = text[:]
    else:
        pass
    return {"manifesto": manifestoCache}


# 刷新角色信息缓存
@app.post("/characters/refreshMeta/live", status_code=200)
def refreshCharacterMeta(background_tasks: BackgroundTasks, userSentData: EncryptedPost, response: Response):
    """
    :return: result: 'OK' if new task generated, 'pending' if a previous task is ongoing
    """
    global LastCharactersVersionMakeTime
    userSentData = userSentData.dict()
    if verifyKey(userSentData['key'], userSentData['parameter']):
        currentTimestamp = int(time.time())
        if currentTimestamp - LastCharactersVersionMakeTime < 600:
            return {"result": "skipped"}
        else:
            background_tasks.add_task(crawler.getAllCharacters, False, str(currentTimestamp))
            LastCharactersVersionMakeTime = currentTimestamp
            return {"result": "OK"}
    else:
        response.status_code = status.HTTP_403_FORBIDDEN
        return {'result': 'failed'}


# 获取角色信息
@app.get("/characters/live", status_code=200)
def getLatestCharacters(background_tasks: BackgroundTasks):
    global LastCharactersVersionCheckTime, LatestCharactersVersion, LastCharactersVersionMakeTime
    # If there is memory cache, return it
    currentTimestamp = int(time.time())
    if currentTimestamp - LastCharactersVersionCheckTime > 600:
        #print("currentTimestamp: " + str(currentTimestamp))
        #print("LastCharactersVersionCheckTime: " + str(LastCharactersVersionCheckTime))
        LastCharactersVersionCheckTime = currentTimestamp
        files = os.listdir("./data/od21/Metadata/")
        latestTimestamp = 0
        for file in files:
            timestamp = re.search("(-)(\d)+", file)
            if timestamp is not None:
                timestamp = timestamp[0].replace("-", "")
                if int(timestamp) > latestTimestamp:
                    latestTimestamp = int(timestamp)
        if latestTimestamp != 0:
            # 将IO结果中最新的缓存写入内存
            print("has assigned timestamp " + str(latestTimestamp) + " to cache")
            LatestCharactersVersion = str(latestTimestamp)
            return {"result": "OK", "message": "new IO cache returned", "timestamp": LatestCharactersVersion}
        else:
            # 无任何缓存的极端情况
            background_tasks.add_task(crawler.getAllCharacters, False, str(currentTimestamp))
            LastCharactersVersionMakeTime = currentTimestamp
            return {"result": "failed", "message": "Making new cache", "timestamp": str(currentTimestamp)}
    else:
        return {"result": "OK", "message": "memory cache returned", "timestamp": LatestCharactersVersion}


# 刷新测试角色信息缓存
@app.post("/characters/refreshMeta/beta", status_code=200)
def refreshCharacterMeta(background_tasks: BackgroundTasks, userSentData: EncryptedPost, response: Response):
    """
    :return: result: 'OK' if new task generated, 'pending' if a previous task is ongoing
    """
    global LastBetaCharactersVersionMakeTime
    userSentData = userSentData.dict()
    if verifyKey(userSentData['key'], userSentData['parameter']):
        currentTimestamp = int(time.time())
        if currentTimestamp - LastBetaCharactersVersionMakeTime < 600:
            return {"result": "skipped"}
        else:
            background_tasks.add_task(crawler.getAllCharacters, True, str(currentTimestamp))
            LastBetaCharactersVersionMakeTime = currentTimestamp
            return {"result": "OK"}
    else:
        response.status_code = status.HTTP_403_FORBIDDEN
        return {'result': 'failed'}


# 获取测试角色信息
@app.get("/characters/beta", status_code=200)
def getLatestCharacters(background_tasks: BackgroundTasks):
    global LastBetaCharactersVersionCheckTime, LatestBetaCharactersVersion, LastBetaCharactersVersionMakeTime
    # If there is memory cache, return it
    currentTimestamp = int(time.time())
    if currentTimestamp - LastBetaCharactersVersionCheckTime > 600:
        #print("currentTimestamp: " + str(currentTimestamp))
        #print("LastBetaCharactersVersionCheckTime: " + str(LastBetaCharactersVersionCheckTime))
        LastBetaCharactersVersionCheckTime = currentTimestamp
        files = os.listdir("./data/od21/Metadata/")
        latestTimestamp = 0
        for file in files:
            timestamp = re.search("(beta-)(\d)+", file)
            if timestamp is not None:
                timestamp = timestamp[0].replace("beta-", "")
                if int(timestamp) > latestTimestamp:
                    latestTimestamp = int(timestamp)
        if latestTimestamp != 0:
            # 将IO结果中最新的缓存写入内存
            print("has assigned timestamp " + str(latestTimestamp) + " to cache")
            LatestBetaCharactersVersion = str(latestTimestamp)
            return {"result": "OK", "message": "new IO cache returned", "timestamp": LatestBetaCharactersVersion}
        else:
            # 无任何缓存的极端情况
            background_tasks.add_task(crawler.getAllCharacters, True, str(currentTimestamp))
            LastBetaCharactersVersionMakeTime = currentTimestamp
            return {"result": "failed", "message": "Making new cache", "timestamp": str(currentTimestamp)}
    else:
        return {"result": "OK", "message": "memory cache returned", "timestamp": LatestBetaCharactersVersion}


@app.get("/plugin/update/{PluginName}", status_code=200)
def getPluginVersion(PluginName: str):
    # global cacheTime, PluginVersionCache, ACCEPT_PLUGINS
    refreshTask = False

    if PluginName not in ACCEPT_PLUGINS:
        raise HTTPException(status_code=404, detail="Not a valid plugin")

    if PluginVersionCache[PluginName] != "":
        lastCacheTimestamp = int(PluginVersionCache[PluginName]["cache_timestamp"])
        if int(time.time()) - lastCacheTimestamp >= cacheTime:
            refreshTask = True
    else:
        refreshTask = True

    if refreshTask:
        apiUrl = "https://api.github.com/repos/%s/releases/latest" % (PluginName.replace("*", "/"))
        githubAPIResult = json.loads(requests.get(apiUrl).text)
        NewCache = {
            "tag_name": githubAPIResult["tag_name"],
            "cache_timestamp": str(int(time.time())),
            "url": githubAPIResult["assets"][0]["browser_download_url"]
        }
        PluginVersionCache[PluginName] = NewCache
        return NewCache
    else:
        return PluginVersionCache[PluginName]
