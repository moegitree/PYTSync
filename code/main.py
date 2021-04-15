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
    DT2 = SPU.GetDriveItem(headers, config, siteID, config["cloudRoot"])
    #DT3 = DT.File2DirectoryTree(config["readFileStructure"])
    DT.DirectoryTree2File(DT2, config["saveFileStructure"])

    [d12, f12, d21, f21] = DT.CmpDirectoryTree(DT1, DT2, config["noDeleteFolders"])
    uploadFileNum_success = 0
    uploadFileNum_fail = 0
    deleteFileNum_success = 0
    deleteFileNum_fail = 0

    itemIDList = {} # dict for storing item id

    for i in range(len(d12)):
        if d12[i] == "": continue
        folder_path = config['cloudRoot'] + d12[i]
        logger.info("Main process: " + folder_path)
        print(folder_path)
        SPU.CreateFolder(headers, config, siteID, config['cloudRoot'], d12[i], itemIDList)
    
    # Q_d12 = queue.Queue(10000)
    # for i in range(len(d12)):
    #     Q_d12.put(d12[i])

    # threadA = SPU.createFolderThread("Thread-A", headers=headers, config=config, siteID=siteID, cloudRoot=config['cloudRoot'], queue=Q_d12)
    # threadB = SPU.createFolderThread("Thread-B", headers=headers, config=config, siteID=siteID, cloudRoot=config['cloudRoot'], queue=Q_d12)
    # threadC = SPU.createFolderThread("Thread-C", headers=headers, config=config, siteID=siteID, cloudRoot=config['cloudRoot'], queue=Q_d12)
    # threadD = SPU.createFolderThread("Thread-D", headers=headers, config=config, siteID=siteID, cloudRoot=config['cloudRoot'], queue=Q_d12)
    # threadA.start()
    # threadB.start()
    # threadC.start()
    # threadD.start()

    # threadA.join()
    # threadB.join()
    # threadC.join()
    # threadD.join()

    # for i in range(len(f12)):
    #     file_path = config['cloudRoot']+f12[i]
    #     logger.info("Main process: " + file_path)
    #     print(file_path) 
    #     file_size = os.path.getsize(config['localRoot']+ f12[i])
    #     if file_size < int(config["size_threshold"]):
    #         r = SPU.UploadFile(headers, config, siteID, config['localRoot'], config['cloudRoot'], f12[i])
    #     else:
    #         r = SPU.UploadLargeFile(headers, config, siteID, config['localRoot'], config['cloudRoot'], f12[i])
        
    #     if r: uploadFileNum_success += 1
    #     else: uploadFileNum_fail += 1

    Q_f12 = queue.Queue(10000)
    for i in range(len(f12)):
        Q_f12.put(f12[i])
    
    thread1 = SPU.uploadFileThread("Thread-1", headers=headers, config=config, siteID=siteID, localRoot=config['localRoot'], cloudRoot=config['cloudRoot'], itemIDList=itemIDList, queue=Q_f12)
    thread2 = SPU.uploadFileThread("Thread-2", headers=headers, config=config, siteID=siteID, localRoot=config['localRoot'], cloudRoot=config['cloudRoot'], itemIDList=itemIDList, queue=Q_f12)
    thread3 = SPU.uploadFileThread("Thread-3", headers=headers, config=config, siteID=siteID, localRoot=config['localRoot'], cloudRoot=config['cloudRoot'], itemIDList=itemIDList, queue=Q_f12)
    thread4 = SPU.uploadFileThread("Thread-4", headers=headers, config=config, siteID=siteID, localRoot=config['localRoot'], cloudRoot=config['cloudRoot'], itemIDList=itemIDList, queue=Q_f12)
    thread1.start()
    thread2.start()
    thread3.start()
    thread4.start()

    thread1.join()
    thread2.join()
    thread3.join()
    thread4.join()

    uploadFileNum_success = thread1.success_count + thread2.success_count + thread3.success_count + thread4.success_count
    uploadFileNum_fail = thread1.fail_count + thread2.fail_count + thread3.fail_count + thread4.fail_count


    for i in range(len(f21)):
        file_path = config['cloudRoot'] + f21[i]
        logger.info("Main process: " + file_path)
        print(file_path)
        r = SPU.DeleteFile(headers, config, siteID, config['cloudRoot'], f21[i], itemIDList)

        if r: deleteFileNum_success += 1
        else: deleteFileNum_fail += 1

    for i in range(len(d21)):
        if d21[i] == "": continue
        folder_path = config['cloudRoot'] + d21[i]
        logger.info("Main process: " + folder_path)
        print(folder_path)
        SPU.DeleteFolder(headers, config, siteID, config['cloudRoot'], d21[i], itemIDList)

    # print("Upload Successed：" + str(uploadFileNum_success))
    # print("Upload Failed: " + str(uploadFileNum_fail))
    # print("Delete Successed: " + str(deleteFileNum_success))
    # print("Delete Failed: " + str(deleteFileNum_fail))

    # send result message to wechat bot
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
