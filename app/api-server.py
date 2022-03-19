# coding=utf8
from typing import Optional
import re
import os
import time
import json
import requests
import hashlib
from fastapi import FastAPI, Response, status, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.characters import crawler


# Application
description = """
Snap Genshin Web API

## About us
[Snap Genshin](https://www.snapgenshin.com/)

"""
app = FastAPI(
    title="SnapGenshinWebAPI",
    version="1.5",
    redoc_url=None,
    docs_url=None
)
# 全局变量
cacheTime = 600
charactersCacheTime = 7 * 24 * 60 * 60
# 内存缓存 - 版本分发
AllReleaseDict = {}
GlobalStablePatch = {}
CNStablePatch = {}
LatestRelease = ""
LastPatchCacheTimestamp = ""
# 内存缓存 - 角色JSON
LastCharactersCacheTimestamp = ""
LastPendingCharactersCacheTimestamp = ""
CharactersDict = ""
# 内存缓存 - 公告
manifestoCache = ""


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
@app.post("/characters/refreshMeta", status_code=200)
def refreshCharacterMeta(background_tasks: BackgroundTasks, userSentData: EncryptedPost, response: Response):
    """
    :return: result: 'OK' if new task generated, 'pending' if a previous task is ongoing
    """
    global LastPendingCharactersCacheTimestamp, LastCharactersCacheTimestamp, CharactersDict
    userSentData = userSentData.dict()
    if verifyKey(userSentData['key'], userSentData['parameter']):
        # 判断当前是否有挂起的刷新任务
        if LastPendingCharactersCacheTimestamp != "":
            expectedFileName = "./data/characters-" + LastPendingCharactersCacheTimestamp + ".json"
            previousTaskFinished = os.path.exists(expectedFileName)
            if previousTaskFinished:
                # 上一次任务已完成，新缓存已生成
                # 复制时间戳到最新版本，重置挂起任务记录
                LastCharactersCacheTimestamp = LastPendingCharactersCacheTimestamp[:]
                LastPendingCharactersCacheTimestamp = ""
                # 将新的JSON文件写入内存
                f = open(expectedFileName, encoding='utf-8')
                text = f.read()
                f.close()
                CharactersDict = text
                # 开始新的刷新任务
                currentTimestamp = str(int(time.time()))
                background_tasks.add_task(crawler.getAllCharacters, False, currentTimestamp)
                LastPendingCharactersCacheTimestamp = currentTimestamp
                return {
                    "result": "OK",
                    "message": "A new characters JSON cache is generating at the background",
                    "timestamp": currentTimestamp
                }
            else:
                # 已有任务但未完成
                return {
                    "result": "pending",
                    "message": "The previous refresh task is still ongoing",
                    "timestamp": LastPendingCharactersCacheTimestamp
                }
        else:
            currentTimestamp = str(int(time.time()))
            background_tasks.add_task(crawler.getAllCharacters, False, currentTimestamp)
            LastPendingCharactersCacheTimestamp = currentTimestamp
            return {
                "result": "OK",
                "message": "A new characters JSON cache is generating at the background",
                "timestamp": currentTimestamp
            }
    else:
        response.status_code = status.HTTP_403_FORBIDDEN
        return {'result': 'failed'}


@app.get("/characters/{action}")
def getLatestCharacters(action: str, background_tasks: BackgroundTasks):
    global LastPendingCharactersCacheTimestamp, LastCharactersCacheTimestamp, CharactersDict
    # If there is memory cache, return it
    acceptedActions = ["version", "live"]
    if action in acceptedActions:
        if CharactersDict != "" and LastCharactersCacheTimestamp != "":
            print("access from memory cache")
            pass
        else:
            # If there is a pending timestamp, check task status
            if LastPendingCharactersCacheTimestamp != "":
                expectedFileName = "./data/characters-" + LastPendingCharactersCacheTimestamp + ".json"
                previousTaskFinished = os.path.exists(expectedFileName)
                # Task finished
                if previousTaskFinished:
                    # take pending timestamp to cached timestamp
                    LastCharactersCacheTimestamp = LastPendingCharactersCacheTimestamp[:]
                    LastPendingCharactersCacheTimestamp = ""
                    # 将新的JSON文件写入内存
                    f = open(expectedFileName, encoding='utf-8')
                    text = f.read()
                    f.close()
                    CharactersDict = text
            elif LastCharactersCacheTimestamp != "":
                expectedFileName = "./data/characters-" + LastCharactersCacheTimestamp + ".json"
                f = open(expectedFileName, encoding='utf-8')
                text = f.read()
                f.close()
                CharactersDict = text
            else:
                # 没有任何可能的内存缓存
                # 检查是否有文件IO缓存
                files = os.listdir("./data/")
                latestTimestamp = 0
                for file in files:
                    timestamp = re.search("(-)(\d)+", file)
                    if timestamp is not None:
                        timestamp = timestamp[0].replace("-", "")
                        if int(timestamp) > latestTimestamp:
                            latestTimestamp = int(timestamp)
                if latestTimestamp != 0:
                    print("has assigned timestamp " + str(latestTimestamp) + " to cache")
                    LastCharactersCacheTimestamp = str(latestTimestamp)
                    expectedFileName = "./data/characters-" + LastCharactersCacheTimestamp + ".json"
                    f = open(expectedFileName, encoding='utf-8')
                    text = f.read()
                    f.close()
                    CharactersDict = text
                else:
                    currentTimestamp = str(int(time.time()))
                    background_tasks.add_task(crawler.getAllCharacters, False, currentTimestamp)
                    LastPendingCharactersCacheTimestamp = currentTimestamp
                    return {
                        "action": action,
                        "code": "903",
                        "timestamp": "",
                        "result": ""
                    }
        if action == "live":
            return {
                "action": "live",
                "code": "901",
                "timestamp": LastCharactersCacheTimestamp,
                "result": CharactersDict
            }
        else:
            return {
                "action": "version",
                "code": "902",
                "timestamp": LastCharactersCacheTimestamp
            }
    else:
        # 调用了错误的方法
        return {
            "action": action,
            "result": "failed",
            "data": ""
        }
