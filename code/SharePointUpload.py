 #!/usr/bin/python
 # -*- coding: utf-8 -*-

import os
import sys  # For simplicity, we'll read config file from 1st CLI param sys.argv[1]
import json
import logging
import time

import requests
import re

def GetSiteID(H, C):
    logger = logging.getLogger('mylogger')

    U = C["endpoint"] + "/sites/"+ C["hostname"] + ":/sites/" + C["SPsite"]
    
    # set proxy 
    if "proxy" in C: proxy = C["proxy"]
    else: proxy = {}

    try:
        R = requests.get( U, headers=H, proxies=proxy )
        R.raise_for_status()
        logger.info("Get siteID for \"" + C["SPsite"] + "\": Successed")
        logger.info("SiteID for \"" + C["SPsite"] + " is: " + str(R.json()["id"]))
        return R.json()["id"]
    except:
        logger.error("Get siteID for " + C["SPsite"] + ": Failed")
        logger.error("The status_code for response using GetSiteID() is: " + str(R.status_code))
        logger.error("Error message: " + str(R.json()["error"]["message"]) )
        sys.exit()

def GetDriveID(H, C, siteID):
    logger = logging.getLogger('mylogger')

    U = C["endpoint"] + "/sites/"+ siteID + "/drive"

    # set proxy 
    if "proxy" in C: proxy = C["proxy"]
    else: proxy = {}

    try:
        R = requests.get( U, headers=H, proxies=proxy )
        R.raise_for_status()
        logger.info("Get driveID for site \"" + str(siteID) + "\": Successed")
        logger.info("DriveID is: " + str(R.json()["id"]))
        return R.json()["id"]
    except:
        logger.error("Get driveID for site \"" + str(siteID) + "\": Failed" )
        logger.error("The status_code for response using GetDriveID() is: " + str(R.status_code))
        logger.error("Error message: " + str(R.json()["error"]["message"]) )
        sys.exit()

def GetItemID(H, C, siteID, item):
    logger = logging.getLogger('mylogger')

    [relativePath, itemName] = os.path.split(item)

    if relativePath == "":
        U = C["endpoint"] + "/sites/" + siteID + "/drive/root/children"
    else:
        U = C["endpoint"] + "/sites/" + siteID + "/drive/root:/" + relativePath + ":/children"

    # set proxy 
    if "proxy" in C: proxy = C["proxy"]
    else: proxy = {}
    
    try:
        Res = requests.get( U, headers=H, proxies=proxy )
        Res.raise_for_status()
        R = Res.json()["value"]

        itemID = None
        for i in range(len(R)):
            if R[i]["name"] == itemName:
                itemID = R[i]["id"]
                logger.info("Get itemID for item \""+ itemName + "\": Scuccessed")
                logger.debug("ItemID for \"" + itemName + "\" is: " + str(itemID))
                return itemID
        
        #In case itemName not found
        logger.debug("\"" + itemName + "\" is not found under path: "+ relativePath)
        return False
    except:
        logger.warning("Get itemID for item \""+ itemName + "\": Failed")
        logger.debug("The status_code for response using GetItemID() is: " + str(Res.status_code))
        logger.debug("Error message: " + str(Res.json()["error"]["message"]) )
        return False

# Create folder with all its parent folders if they didn't exist
def CreateFolder(H, C, siteID, cloudRoot, relativePath):
    logger = logging.getLogger('mylogger')

    folderPath = cloudRoot + relativePath 
    folderID = GetItemID(H, C, siteID, folderPath)

    #if folder already exists, stop creating new folder and return the existed one's ID
    if folderID != False:
        logger.info("Folder \"" + folderPath + "\" already exists")
        return folderID
    
    #if folder doesn't exist, creat new one
    if folderID == False:
        [parentPath, folderName] = os.path.split(relativePath)
        #use CreateFolder to return ID for parent folder
        if parentPath == "\\": 
            parentID = CreateFolder(H, C, siteID, "", cloudRoot)
        else:
            parentID = CreateFolder(H, C, siteID, cloudRoot, parentPath) 

        newfolder = {
            "folder": { },
            "name": folderName
            }

        H["Content-Type"]="application/json"
        U = C["endpoint"] + "/sites/" + siteID + "/drive/items/" + parentID + "/children"

        # set proxy 
        if "proxy" in C: proxy = C["proxy"]
        else: proxy = {}

        try:
            Res = requests.post(U, headers=H, data=json.dumps(newfolder), proxies=proxy)
            Res.raise_for_status()
            logger.info("Create folder \"" + folderName + "\": Successed" )
            logger.debug("ItemID for new folder \"" + folderName + "\" is:" + str(Res.json()["id"]))
            return Res.json()["id"]
        except:
            logger.warning("Create folder \"" + folderName + "\": Failed" )
            logger.warning("The status_code for response using CreateFolder() is: " + str(Res.status_code))
            logger.warning("Error message: " + str(Res.json()["error"]["message"]) )
            return False

# Upload files up to 4MB in size
def UploadFile(H, C, siteID, localRoot, cloudRoot, relativePath):#rootPath, filePath):
    logger = logging.getLogger('mylogger')

    [parentPath, fileName] = os.path.split(relativePath)
    fileName = fileName.strip()    #remove leading and tailing space 
    if parentPath == "\\":
        parentID = CreateFolder(H, C, siteID, "", cloudRoot)
    else:
        parentID = CreateFolder(H, C, siteID, cloudRoot, parentPath)

    U = C["endpoint"] + "/sites/" + siteID + "/drive/items/" + parentID + ":/" + fileName +":/content"

    # set proxy 
    if "proxy" in C: proxy = C["proxy"]
    else: proxy = {}

    absPath = localRoot + relativePath
    size = os.path.getsize(absPath)
    Fhandler = open(absPath, mode='rb')
    Fhandler.seek(0)
    Fdata = Fhandler.read(size)
    Fhandler.close()

    try:
        Res = requests.put(U, headers=H, data=Fdata, proxies=proxy)
        Res.raise_for_status()
        logger.info("Upload file " + absPath + ": Successed")
        logger.debug("ItemID for file \"" + relativePath + "\" is:" + str(Res.json()["id"]))
        return True
    except:
        logger.warning("Upload file " + absPath + ": Failed")
        logger.warning("The status_code for response using UploadFile() is: " + str(Res.status_code))
        logger.warning("Error message: " + str(Res.json()["error"]["message"]) )
        return False

# Upload large file - Create session for uploading files large than 4MB
def CreateUploadSession(H, C, siteID, parentID, fileName):
    logger = logging.getLogger('mylogger')

    U = C["endpoint"] + "/sites/" + siteID + "/drive/items/" + parentID + ":/" + fileName + ":/createUploadSession"
    H["Content-Type"] = "application/json"

    # set proxy 
    if "proxy" in C: proxy = C["proxy"]
    else: proxy = {}
    
    requestBody = {
        "item": {
            "@microsoft.graph.conflictBehavior": "replace"
        }
    }

    try:
        Res = requests.post(U, headers=H, data=json.dumps(requestBody), proxies=proxy)
        Res.raise_for_status()
        logger.info("Create upload session for large files: Succeed")
        logger.debug("UploadUrl is: " + Res.json()["uploadUrl"])
        logger.debug("Expiration date is :" +  Res.json()["expirationDateTime"])
        return Res.json()["uploadUrl"]
    except:
        logger.warning("Create upload session for large files: Failed")
        logger.warning("The status_code for response using CreateUploadSession() is: " + str(Res.status_code))
        logger.warning("Error message: " + str(Res.json()["error"]["message"]) )
        return False

# Upload large file - Upload file from A byte to B byte
def UploadFileSegment(uploadUrl, absPath, Abyte, Bbyte, proxy):
    logger = logging.getLogger('mylogger')

    fileSize = os.path.getsize(absPath)
    if (Abyte >= fileSize) or (Abyte >= Bbyte):
        logger.warning("Get segemnt for file " + absPath + " : Failed" )
        logger.debug("File size is: " + str(fileSize))
        logger.debug("Required segment in UploadFileSegment is :" + str(Abyte) + " to " + str(Bbyte))
        return False

    if (Bbyte >= fileSize): Bbyte = fileSize-1

    Fhandler = open(absPath, mode='rb')
    Fhandler.seek(Abyte)
    Fdata = Fhandler.read(Bbyte - Fhandler.tell() +1) #Get binary data from Abyte to Bbyte
    Fhandler.close()

    H = {
        'Conten-Lenth': str(Bbyte-Abyte+1),
        'Content-Range': 'bytes '+ str(Abyte) +'-'+ str(Bbyte) +'/'+ str(fileSize)
        }

    try:
        Res = requests.put(uploadUrl, headers=H, data=Fdata, proxies=proxy)
        Res.raise_for_status()
        logger.debug("Upload segment " + str(Abyte) + " to " + str(Bbyte) + " for file " + absPath + " : Successed")
        
        return Res
    except Exception as e:
        logger.warning("Upload segment " +str(Abyte) + " to " + str(Bbyte) + " for file " + absPath + " : Failed")
        logger.debug(str(e))
        return Res  

def GetNextExpectedRange(res):
    resJson = res.json()
    nextRanges = resJson["nextExpectedRanges"]
    if len(nextRanges) >=1 :
        matchobj = re.match(r"[0-9]*", nextRanges[0])
        return int(matchobj.group())
    else:
        return False

# Upload files with large size
def UploadLargeFile(H, C, siteID, localRoot, cloudRoot, relativePath, segment=5*1024*1024):
    logger = logging.getLogger('mylogger')

    absPath = localRoot + relativePath
    [parentPath, fileName] = os.path.split(relativePath)
    fileName = fileName.strip()

    #Create parent folder and get folder's id
    parentID = CreateFolder(H, C, siteID, cloudRoot, parentPath)
    #Creat Upload Session
    uploadUrl = CreateUploadSession(H, C, siteID, parentID, fileName)

    # set proxy 
    if "proxy" in C: proxy = C["proxy"]
    else: proxy = {}

    startByte = 0
    endByte = segment-1
    flag = True

    while flag:
        res = UploadFileSegment(uploadUrl, absPath, startByte, endByte, proxy)

        code = res.status_code
        if code == 202:
            flag = True
            startByte = GetNextExpectedRange(res)
            endByte = startByte + segment - 1 

        elif code == 200 or code == 201:
            logger.info("Upload file " + absPath + ": Successed")
            return True

        elif code==500 or code==502 or code==503 or code==504:
            logger.debug("Retry uploading segment " + str(startByte) + " to " + str(endByte) + " for file " + absPath)
            flag = True

        else:
            flag = False
    
    return False

def DeleteItem(H, C, siteID, itemID):
    logger = logging.getLogger('mylogger')
    
    U = C["endpoint"] + "/sites/" + siteID + "/drive/items/" + itemID

    # set proxy 
    if "proxy" in C: proxy = C["proxy"]
    else: proxy = {}

    try:
        Res = requests.delete(U, headers=H, proxies=proxy)
        Res.raise_for_status()
        return True
    except:
        logger.warning("Delete " + itemID + ": Failed" )
        logger.warning("The status_code for response using DeleteItem() is: " + str(Res.status_code))
        logger.warning("Error message: " + str(Res.json()["error"]["message"]) )
        return False

# Delete all subfolders and files under folderPath
def DeleteFolder(H, C, siteID, cloudRoot, relativePath):
    logger = logging.getLogger('mylogger')

    folderPath = cloudRoot + relativePath
    logger.info("Deleting folder: \"" + folderPath + "\"")

    folderID = GetItemID(H, C, siteID, folderPath)
    if folderID: #folder found
        result = DeleteItem(H, C, siteID, folderID)
        
        if result:
            logger.info("Delete folder \"" + folderPath + "\": Successed")
            return True
        else:
            logger.info("Delete folder: \"" + folderPath + "\": Failed")
            return False
    
    else:   #folder not found
        logger.info("Delete folder: \"" + folderPath + "\": Failed")
        logger.info("Folder \"" + folderPath + "\" does not exist")
        return False

def DeleteFile(H, C, siteID, cloudRoot, relativePath):
    logger = logging.getLogger('mylogger')

    filePath = cloudRoot + relativePath  
    logger.info("Deleting file: \"" + filePath + "\"")

    fileID = GetItemID(H, C, siteID, filePath)
    if fileID: #file found
        result = DeleteItem(H, C, siteID, fileID)

        if result:
            logger.info("Delete file: \"" + filePath + "\": Successed")
            return True
        else:
            logger.info("Delete file: \"" + filePath + "\": Failed")
            return False
    else: #file not found
        logger.info("Delete file: \"" + filePath + "\": Failed")
        logger.info("File \"" + filePath + "\" does not exist")
        return False

def SendMessage(C, upload_success, upload_fail, delete_success, delete_fail):
    url = C["webhookUrl"]
    H = {}
    H["Content-Type"] =  "application/json"

    # set proxy 
    if "proxy" in C: proxy = C["proxy"]
    else: proxy = {}

    t = time.localtime(time.time())
    
    d = {
        "msgtype": "markdown",
        "markdown": {
            "content":
            "执行时间: " + str(t.tm_year) + "-" + str(t.tm_mon) + "-" + str(t.tm_mday) + " " + str(t.tm_hour) + ":" + str(t.tm_min)  + "\n" + \
            "[点此链接从pytsupport站点查看](https://scsksh.sharepoint.cn/:f:/r/sites/pytsupport/Shared%20Documents/PYT-ProdEnv?csf=1&web=1&e=TewbUr) " + \
            "（需要scsksh邮箱/密码登录）\n" + \
            ">上传成功: <font color=\"comment\">" + str(upload_success) + "</font>\n" + \
            ">上传失败: <font color=\"comment\">" + str(upload_fail) + "</font>\n" + \
            ">删除成功: <font color=\"comment\">" +  str(delete_success) + "</font>\n" + \
            ">删除失败: <font color=\"comment\">" + str(delete_fail) + "</font>\n"

        }
    }
    data = json.dumps(d)
    res = requests.post(url, headers=H, data=data, proxies=proxy)

    return res

def GetDriveItem(H, C, siteID, folderPath):
    logger = logging.getLogger('mylogger')

    H["Content-Type"]="application/json"
    U = C["endpoint"] + "/sites/" + siteID + "/drive/root:/" + folderPath + ":/children"

    # set proxy 
    if "proxy" in C: proxy = C["proxy"]
    else: proxy = {}

    R = []
    try:
        while True:
            Res = requests.get(U, headers=H, proxies=proxy)
            R = R + Res.json()["value"]

            if "@odata.nextLink" not in Res.json(): break
            U = Res.json()["@odata.nextLink"]

        logger.info("Get children for folder \""+ folderPath + "\": Succeed")
    except:
        logger.warning("Get children for folder \""+ folderPath + "\": Failed")
        logger.debug("The status_code for response using GetDriveItem() is: " + str(Res.status_code))
        logger.debug("Error message: " + str(Res.json()["error"]["message"]) )
        return False

    paths = []

    for i in range(len(R)):
        child = os.path.join(folderPath, R[i]["name"])
        itemType = None
        if "folder" in R[i]: 
            itemType = "Directory"
            childPaths = GetDriveItem(H, C, siteID, child)
            if childPaths == False: continue
            paths = paths + childPaths

            [_,_,relativePath] = child.partition(C["cloudRoot"])
            paths.append(relativePath + "\t" + itemType)
        else: 
            itemType = "File"
            
            [_,_,relativePath] = child.partition(C["cloudRoot"])
            paths.append(relativePath + "\t" + itemType)

    return paths


