#!/usr/bin/env python

import csv
import json
import os
import os.path
import sys
import hashlib
from pathlib import Path
import pymysql as mdb
from zipfile import ZipFile
from datetime import date
from difflib import SequenceMatcher
from argparse import ArgumentParser
import uniq_login
#from login import login
from config.db_config import DB_IP, DB_USERNAME, DB_PASSWORD, DB_SCHEMA


def getCurrentApicDeviceInventory(apic, namespace):
    file_list = apic.file.getFilesByNamespace(nameSpace=namespace)

def connectToDB():
    try:
        con = mdb.connect(DB_IP, DB_USERNAME, DB_PASSWORD, DB_SCHEMA);

        cur = con.cursor()
        cur.execute("SELECT VERSION()")

    except mdb.Error as e:

        print("Error %d: %s" % (e.args[0], e.args[1]))
        sys.exit(1)

def fileExists(config_filename):
    file = Path(config_filename)
    return file.is_file()


def hashIsSame(new_file, old_file):
    digests = []

    for filename in [new_file, old_file] :
        hasher = hashlib.md5()
        with open(filename, 'rb') as f:
            hasher.update(f.read())
            hd = hasher.hexdigest()
            digests.append(hd)

    return digests[0] == digests[1]


def diffTheFiles(new_file, old_file):
    s = SequenceMatcher(None, new_file, old_file)

    return s.ratio() != 1


def zipThisFile(filepath, timestamp):
    newFileName = os.path.basename(filepath+"-"+timestamp)

    if fileExists(filepath+".zip"):
        source = ZipFile(filepath+".zip", 'r')
        target = ZipFile(filepath+"-new.zip", 'w')

        for file in source.infolist():
            target.writestr(file.filename, source.read(file.filename))

        matching = [s for s in source.infolist() if newFileName in s.filename]
        target.writestr(newFileName + "--" + str(len(matching) + 1), open(filepath, "rb").read())

        source.close()
        target.close()

        os.remove(filepath + ".zip")
        os.rename(filepath+"-new.zip", filepath+".zip")
    else:
        with ZipFile(filepath+'.zip', 'w') as myzip:
            myzip.write(filepath, newFileName)

        myzip.close()

    os.remove(filepath)


def outputFile(config_filename, deviceConfigResponse):
    with open(config_filename, 'w') as config_file:
        config_file.write(deviceConfigResponse)
    #print("wrote file: {0}".format(config_filename))


if __name__ == "__main__":
    d = date.today()
    print("{0} ##########################".format(d.isoformat()))

    apic = uniq_login.login()

    allDevicesResponse = apic.networkdevice.getAllNetworkDevice()
    for device in allDevicesResponse.response:
        print("Checking: {0}, ID: {1}".format(device.hostname, device.id))

        if device.hostname is not None:
            if len(device.hostname.strip()) != 0:
                deviceConfigResponse = apic.networkdevice.getRunningConfigById(networkDeviceId=device.id).response

                config_filename = "configs/" + device.hostname.split('.')[0] + "-config"
                tmp_filename = "configs/tmp_file"

                if not fileExists(config_filename):
                    print(config_filename, " DOESN'T EXIST!! write it")
                    outputFile(config_filename, deviceConfigResponse)
                else:
                    #print(config_filename, " ALREADY EXISTS!! is it differnet??")
                    outputFile(tmp_filename, deviceConfigResponse)
                    #if hashIsSame(tmp_filename, config_filename):
                    if diffTheFiles(tmp_filename, config_filename):
                        print("\t {0} ALREADY EXISTS - CONTENTS DIFFERENT!! zip it and write a new one".format(config_filename))
                        zipThisFile(config_filename, d.isoformat())
                        outputFile(config_filename, deviceConfigResponse)
                    else:
                        print("\t {0} ALREADY EXISTS - CONTENTS THE SAME!! leave it alone".format(config_filename))

        else:
            print("\t", "Device has no hostname?!")
