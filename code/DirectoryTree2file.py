#!/usr/bin/python
# -*- coding: UTF-8 -*-
import os

def DirectoryTree2File( paths, save_File ):
    if not os.path.exists( save_File ):
        f = open( save_File, 'w' )
        f.close()

    fo = open(save_File, "w", encoding='utf-8')

    for i in range(len(paths)):
        fo.write(paths[i] + "\n")

    fo.close()
    return

def File2DirectoryTree( target_File ):
    if not os.path.exists( target_File ):
        f  = open( target_File, 'w' )
        f.close()

    fi = open(target_File, 'r', encoding='utf-8-sig') # use utf-8-sig in case of files encoded as utf-8 BOM 

    data = fi.read()
    paths = data.splitlines()

    # for i in range(len(paths)):
    #     [Path, Type] = paths[i].split("\t",2)
    #     print(Path, " ", Type)

    fi.close()
    return paths

def GetDirectroyTree( rootFolder, subFolders ):
    paths = []

    for i in range(len(subFolders)):
        dir_iter = os.walk(rootFolder+"\\"+subFolders[i])
        flag = True

        while flag:
            try: 
                [root, __, files] = next(dir_iter)
                [__, __, post_str] = root.partition(rootFolder)
                paths.append(post_str + "\tDirectory")
                for j in range(len(files)):
                    paths.append(post_str + "\\" + files[j] + "\tFile")
            except StopIteration:
                flag = False
    return paths

def CmpDirectoryTree( DT1, DT2, noDeleteList ):
    s1 = set(DT1)
    s2 = set(DT2)
    D1_2 = list(s1 - s2)
    D2_1 = list(s2 - s1) 

    dir1_2 = []
    file1_2 = []
    dir2_1 = []
    file2_1 = []

    for i in range(len(D1_2)):
        [path, Ftype] = D1_2[i].split("\t", 2)
        if Ftype == "Directory":
            dir1_2.append(path)
        if Ftype == "File":
            file1_2.append(path)
    
    for j in range(len(D2_1)):
        [path, Ftype] = D2_1[j].split("\t", 2)
        
        head = path.split("\\", 2)[1]
        if head in noDeleteList:
            continue

        if Ftype == "Directory":
            dir2_1.append(path)
        if Ftype == "File":
            file2_1.append(path)

    return [dir1_2, file1_2, dir2_1, file2_1]


# rootPath = r"C:\ScanCache"
# savePath = r"C:\Users\chen.zhiyuan\Documents\Python\pyt\FoldStructure.txt"
# readPath = r"C:\Users\chen.zhiyuan\Documents\Python\pyt\FoldStructure.txt"

# DT1 = GetDirectroyTree(rootPath)
# DT2 = File2DirectoryTree(readPath)

# [d12, f12, d21, f21] = CmpDirectoryTree(DT1, DT2)

# print(d12)
# print(f12)
# print(d21)
# print(f21)

