import openVulnQuery


class platformObj:
    def __init__(self, platformID, softwareVersion, hostname, ID):
        self.platformID = platformID
        self.softwareVersion = []
        self.softwareVersion.append(softwareVersionObj(softwareVersion, hostname, ID))

    #def __repr_(self):
    #    return "{0}: {1} {2}".format(self.__class__.__name__, self.platformID, len.self(softwareVersion))

    #def __cmp__(self, other):
    #    if hasattr(other, 'platformID'):
    #        return self.platformID.__cmp__(other.platformID)


class softwareVersionObj:
    def __init__(self, softwareVersion, hostname, ID):
        self.softwareVersion = softwareVersion
        self.hostnames = []
        self.IDs = []

        self.hostnames.append(hostname)
        self.IDs.append(ID)


def addPlatform(polist, platformid, softwareversion, hostname, id):
    createNew = True
    for po in polist:
        if po.platformID == platformid:
            createNew = False
            addSoftwareVersion(po, softwareversion, hostname, id)

    if createNew:
        polist.append(platformObj(platformid, softwareversion, hostname, id))


def addSoftwareVersion(platformobject, softwareversion, hostname, id):
    createNew = True
    for sv in platformobject.softwareVersion:
        if sv.softwareVersion == softwareversion:
            createNew = False
            sv.hostnames.append(hostname)
            sv.IDs.append(id)

    if createNew:
        platformobject.softwareVersion.append(softwareVersionObj(softwareversion, hostname, id))


def printPlatformObjectCount(poList):
    print("Platforms: {0}".format(len(poList)))

    for po in poList:
        print("Platform {0} has {1} software versions.".format(po.platformID, len(po.softwareVersion)))


def printPlatformObj(po):
    print("** {0}".format(po.platformID))
    for svo in po.softwareVersion:
        print("    {0}".format(svo.softwareVersion))
        for i, host in enumerate(svo.hostnames):
            print("      {0} -- {1}".format(host, svo.IDs[i]))


def printPlatformObjList(poList):
    #sorted(poList, key=lambda platformObj: platformObj.platformID)
    for po in poList:
        printPlatformObj(po)


def main():
    apic = uniq_login.login()

    platformObjList = []

    allDevicesResponse = apic.networkdevice.getAllNetworkDevice()
    for device in allDevicesResponse.response:
        if device.platformId is not None:
            addPlatform(platformObjList, device.platformId.split(",")[0], device.softwareVersion, device.hostname, device.id)

    printPlatformObjList(platformObjList)
    printPlatformObjectCount(platformObjList)


if __name__ == "__main__":
    main()