#!/usr/bin/env python3
import sqlite3

from uniq_login import login


def query_time(_cursor, _cursorInner):
    _cursor.execute("SELECT DISTINCT(vlanNumber) FROM vlans")
    print("Unique VLANS: {0}".format(_cursor.fetchone()))

    for row in _cursor.execute("SELECT vlanNumber, COUNT(vlanNumber), networkAddress, prefix FROM vlans GROUP BY vlanNumber"):
        print("VLAN ID/ Occurances: {0} / {1} -- {2} /{3}".format(row[0], row[1], row[2], row[3]))
        if row[2] is not None:
            for row2 in _cursorInner.execute("SELECT ipAddress, hostname FROM vlans WHERE vlanNumber='{0}'".format(row[0])):
                print("  {0}  -- {1}".format(row2[0], row2[1]))

    print("----- These must be routers -----")
    for row in _cursor.execute("SELECT hostname, COUNT(DISTINCT vlanNumber) AS count, networkAddress, prefix FROM vlans GROUP BY hostname HAVING count > 2"):
        print("{0}   ---- SVIs : {1}".format(row[0], row[1]))
        for row2 in _cursorInner.execute("SELECT vlanNumber, ipAddress FROM vlans WHERE hostname='{0}' ORDER BY vlanNumber".format(row[0])):
            print("  {0} - {1}".format(row2[0], row2[1]))

    print("----- the following VLANs have multiple names----")
    for row in _cursor.execute("SELECT vlanNumber, vlanType, COUNT(DISTINCT vlanType) AS x FROM vlans GROUP BY vlanNumber HAVING x > 1"):
        print("{0} - {1}".format(row[0], row[1]))
        for row2 in _cursorInner.execute("SELECT vlanNumber, vlanType, COUNT(vlanType) FROM vlans WHERE vlanNumber='{0}' GROUP BY vlanType ORDER BY vlanNumber".format(row[0])):
            print("  {0}  -- {1}".format(row2[1], row2[2]))


def insert_vlan_response(response, hostname, _cursor):
    # print("Hostname :{0} ".format(hostname))
    for vlan_svi in response:
        # print("  {0}, {1}, {2}".format(vlan_svi.vlanNumber, vlan_svi.vlanType, vlan_svi.ipAddress))
        _cursor.execute("INSERT INTO vlans VALUES (?,?,?,?,?,?,?)", (None,
                                                                     hostname, int(vlan_svi.vlanNumber),
                                                                     vlan_svi.vlanType, vlan_svi.ipAddress,
                                                                     vlan_svi.networkAddress, vlan_svi.prefix))


def main():
    con = sqlite3.connect('test.db')
    _cursor = con.cursor()
    _cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vlans'")
    row = _cursor.fetchone()

    if row is None:
        apic = login()

        con = sqlite3.connect('test.db')
        _cursor = con.cursor()
        _cursor.execute("CREATE TABLE vlans (pk INTEGER PRIMARY KEY," +
                        "hostname TEXT, vlanNumber INTEGER, vlanType TEXT, " +
                        "ipAddress TEXT, networkAddress TEXT, prefix TEXT)")
        con.commit()

        all_devices_response = apic.networkdevice.getAllNetworkDevice()
        for device in all_devices_response.response:
            if device.platformId is not None:
                vlan_svi_response = apic.networkdeviceidvlan.getDeviceVLANData(id=device.id)
                if len(vlan_svi_response.response) > 0:
                    insert_vlan_response(vlan_svi_response.response, device.hostname, _cursor)
                    con.commit()

    query_time(_cursor, con.cursor())


if __name__ == "__main__":
    main()
