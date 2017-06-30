#!/usr/bin/env python2

import re
from openVulnQuery import query_client
from config.cisco_apiconsole import CLIENT_ID, CLIENT_SECRET


def escapeBrackets(inputStr):
    return re.sub(r'([\( \)])', r'\\\1', inputStr)

def printRelevantAdvisories(advisories, productid):
    print(advisories)

def printPlatformObjectCount(poList):
    print("Platforms: {0}".format(len(poList)))

    for po in poList:
        print("Platform {0} has {1} software versions.".format(po.platformID, len(po.softwareVersion)))


def printPlatformObj(query_client, po):
    print("** {0}".format(po.platformID))
    for svo in po.softwareVersion:
        print("    {0}".format(svo.softwareVersion))
        for i, host in enumerate(svo.hostnames):
            print("      {0} -- {1}".format(host, svo.IDs[i]))

        # now print the relevant vulns
        printRelevantAdvisories(query_client.get_by_IOS("cvrf", escapeBrackets(svo.softwareVersion), product_names=po.platformID))


def printPlatformObjList(query_client, poList):
    #sorted(poList, key=lambda platformObj: platformObj.platformID)
    for po in poList:
        printPlatformObj(query_client, po)


def main():
    query_clientX = query_client.QueryClient(CLIENT_ID, CLIENT_SECRET)

    printPlatformObjList(query_client, platformObjList)
    # printPlatformObjectCount(platformObjList)



if __name__ == "__main__":
    main()