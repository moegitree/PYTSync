#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys  # For simplicity, we'll read config file from 1st CLI param sys.argv[1]
import json
import logging
import time
import queue
import threading
import requests
import msal

import SharePointUpload as SPU
import DirectoryTree2file as DT

# Set Logging config
current_path = os.path.dirname(__file__)
log_file_path = os.path.join(current_path, r'logs\Log.log')
if not os.path.exists(os.path.join(current_path, r'logs')): 
    os.mkdir(os.path.join(current_path, r'logs'))
    f = open(os.path.join(current_path, r'logs\Log.log'), mode='w')
    f.close()

logger = logging.getLogger('mylogger')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh = logging.FileHandler(filename=log_file_path, encoding='utf-8', mode='w')
fh.setFormatter(formatter)
logger.addHandler(fh)

# Load endpoint and credential info from parameter file.
#config = json.load(open(sys.argv[1]))
config = json.load(open(os.path.join(current_path, "parameters.json")))

# set proxy 
if "proxy" in config: proxy = config["proxy"]
else: proxy = {}

# Create a preferably long-lived app instance which maintains a token cache.
app = msal.ConfidentialClientApplication(
    config["client_id"], authority=config["authority"],
    client_credential=config["secret"], proxies=proxy)

# The pattern to acquire a token looks like this.
result = None

# Firstly, looks up a token from cache
# Since we are looking for token for the current app, NOT for an end user,
# notice we give account parameter as None.
result = app.acquire_token_silent(config["scope"], account=None)

if not result:
    logger.info("No suitable token exists in cache. Let's get a new one from AAD.")
    result = app.acquire_token_for_client(scopes=config["scope"])

if "access_token" in result:
    headers = {'Authorization': 'Bearer ' + result['access_token']}

    #--------------------Main Part-----------------#
    siteID = SPU.GetSiteID(headers, config)
    #driveID = GetDriveID(headers, config, siteID)
    #rootID = GetItemID(headers, config, siteID, config['cloudRoot'])

    # Get root folder stucture and compare it with the saved one.
    DT1 = DT.GetDirectroyTree(config["localRoot"], config["subFolders"])
    DT2 = SPU.GetCloudDirectoryTree(headers, config, siteID)
    DT.DirectoryTree2File(DT2, config["saveFileStructure"])

    [d12, f12, d21, f21] = DT.CmpDirectoryTree(DT1, DT2, config["noDeleteFolders"])
    uploadFileNum_success = 0
    uploadFileNum_fail = 0
    deleteFileNum_success = 0
    deleteFileNum_fail = 0

    itemIDList = {} # dict for storing item id

    # create new folders
    for i in range(len(d12)):
        if d12[i] == "": continue
        folder_path = config['cloudRoot'] + d12[i]
        logger.info("Main process: " + folder_path)
        print(folder_path)
        SPU.CreateFolder(headers, config, siteID, config['cloudRoot'], d12[i], itemIDList)

    # upload new fils
    Q_f12 = queue.Queue(len(f12))
    for i in range(len(f12)):
        Q_f12.put(f12[i])
    
    thread_num = 4
    thread_list = [None]*4
    for i in range(thread_num):
        thread_list[i] = SPU.uploadFileThread("Thread-"+str(i), headers=headers, config=config, siteID=siteID, itemIDList=itemIDList, queue=Q_f12)
    for i in range(thread_num):
        thread_list[i].start()

    uploadFileNum_success = 0
    uploadFileNum_fail = 0
    for i in range(thread_num):
        thread_list[i].join()
        uploadFileNum_success += thread_list[i].success_count
        uploadFileNum_fail += thread_list[i].fail_count

    # delete old files
    for i in range(len(f21)):
        file_path = config['cloudRoot'] + f21[i]
        logger.info("Main process: " + file_path)
        print(file_path)
        r = SPU.DeleteFile(headers, config, siteID, config['cloudRoot'], f21[i], itemIDList)

        if r: deleteFileNum_success += 1
        else: deleteFileNum_fail += 1

    # delete old folders
    for i in range(len(d21)):
        if d21[i] == "": continue
        folder_path = config['cloudRoot'] + d21[i]
        logger.info("Main process: " + folder_path)
        print(folder_path)
        SPU.DeleteFolder(headers, config, siteID, config['cloudRoot'], d21[i], itemIDList)

    logger.info("Upload Successed：" + str(uploadFileNum_success))
    logger.info("Upload Failed: " + str(uploadFileNum_fail))
    logger.info("Delete Successed: " + str(deleteFileNum_success))
    logger.info("Delete Failed: " + str(deleteFileNum_fail))

    # send result message to wechat webhook
    SPU.SendMessage(config, uploadFileNum_success, uploadFileNum_fail, deleteFileNum_success, deleteFileNum_fail)


    ##------------- followings for debug-------------------##

    ####Upload Small File####
    # res = UploadFile(headers, config, siteID, config['localRoot'], config['cloudRoot'], r"\IM-PYT\Health QR code 0201.jpg")
    ####Upload Large File####
    # rootPath = r"C:\Users\chen.zhiyuan\Desktop"
    # filePath = r"\FolderNo1\SunloginClient_11.0.0.33826_x64.exe"
    # result = UploadLargeFile(headers, config, siteID, rootPath, config['cloudRoot'],filePath)
    
    ####Upload File####
    # filePath = "C:/Users/chen.zhiyuan/Desktop"
    # filename = "1000000206.pdf"
    # result = UploadFile( headers, config, siteID, itemID, filePath, filename )
    # print(result)
