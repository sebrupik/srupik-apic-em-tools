#!/usr/bin/env python3

import calendar
import csv
import time
import uniqLogin
import sqlite3
from datetime import date


def cleanUpResponse(_alldevicesreponse):
    newlist = []
    for device in _alldevicesresponse.response:
        if device.hostname is not None:
            if len(device.hostname.strip()) != 0:
                newlist.append(device)

    return newlist


def outputDeviceToCSV(csvfileurl, _alldevicesresponse):

    with open(csvfileurl, 'w') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

        for device in _alldevicesresponse.response:
            print("Checking: {0}, ID: {1}, Location: {2}, Contact: {3}".format(device.hostname, device.id, device.snmpLocation, device.snmpContact))
            csvwriter.writerow([device.hostname, device.platformId.split(",")[0], device.softwareVersion, device.role, device.managementIpAddress])


def outputToDB(_cursor, _alldevicesresponse, now):
    outputvalues = [0, 0]
    for device in _alldevicesresponse.response:
        _cursor.execute("SELECT * FROM devices WHERE id=?", (device.id,))
        row = _cursor.fetchone()
        if row is None:
            _cursor.execute("INSERT INTO devices VALUES (?,?,?)", (device.id, device.hostname, device.managementIpAddress,))
            _cursor.commit()
            outputvalues[0] += 1

        _cursor.execute("INSERT INTO snapshot VALUES (?,?,?,?,?,?)", (int(now), device.id, device.reachabilityStatus, device.platformId, device.softwareVersion, device.role)
        outputvalues[1] += 1


def createTables(_cursor):
    _cursor.execute("'SELECT name FROM sqlite_master WHERE type='table' AND name='devices'")
    row = _cursor.fetchone()
    if row is None:
        #let's assume if one table is missing they all are
        _cursor.execute("CREATE TABLE devices (id text PRIMARY KEY, hostname text, managementIpAddress text)")
        _cursor.execute("CREATE TABLE snapshot (pk integer PRIMARY KEY, timestamp int, id text, reachabilityStatus text, platformId text, softwareVersion text, role text")
        _cursor.commit()


def main():
    d = date.today()
    now = calendar.timegm(time.gmtime())
    print("{0} ##########################".format(d.isoformat()))

    _apic = uniqLogin.login()

    _alldevicesresponse = cleanUpResponse(_apic.networkdevice.getAllNetworkDevice())

    outputDeviceToCSV("./test.csv", _alldevicesresponse)

    con = sqlite3.connect('test.db')
    cur = con.cursor()
    createTables(cur)

    stats = outputToDB(cur, _alldevicesresponse, now)
    print("New devices added: {0}, device snapshots taken: {1}".format(stats[0], stats[1]))


if __name__ == "__main__":
    main()