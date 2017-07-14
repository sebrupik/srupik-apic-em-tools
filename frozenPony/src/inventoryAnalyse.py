#!/usr/bin/env python2

import requests
import re
import pickle
from openVulnQuery import query_client
from config.cisco_apiconsole import CLIENT_ID, CLIENT_SECRET


def escapeBrackets(inputStr):
    return re.sub(r'([\( \)])', r'\\\1', inputStr)

def printRelevantAdvisories(advisories, productid):
    print(type(advisories))
    for adv in advisories:
        print(adv.advisory_id)
        print(adv.summary)
        print(type(adv))

def printPlatformObjectCount(poList):
    print("Platforms: {0}".format(len(poList)))

    for po in poList:
        print("Platform {0} has {1} software versions.".format(po.platformID, len(po.softwareVersion)))


def printPlatformObj(query_client, po):
    print("** {0}".format(po.platform_id))
    for sv in get_software_versions(po):
        print("    {0} becomes {1}".format(sv, escapeBrackets(sv)))

        # now print the relevant vulns
        #printRelevantAdvisories(query_client.get_by_ios_xe("cvrf", escapeBrackets(sv), product_names=po.platform_id))

        try:
            printRelevantAdvisories(query_client.get_by_ios(escapeBrackets(sv)), po.platform_id)
        except requests.exceptions.HTTPError as exc_info:
            print(exc_info)

        '''
        except requests.exceptions.HTTPError as exc_info:
            if exc_info.response.status_code == 406:
                print('Something not found')
                continue
            else:
                print("HTTP Status Code {0} Reason: {1}".format(exc_info.response.status_code, exc_info.response.reason))
                continue
        '''


def get_software_versions(platform_object):
    output = []
    for model_type_full in platform_object.models.keys():
        sv_list = platform_object.models.get(model_type_full)
        for sv in sv_list:
            if sv.software_version not in output:
                output.append(sv.software_version)

    return output


def printPlatformObjList(query_client, poList):
    #sorted(poList, key=lambda platformObj: platformObj.platformID)
    for po in poList:
        printPlatformObj(query_client, po)


def main():
    ovq_client = query_client.OpenVulnQueryClient(CLIENT_ID, CLIENT_SECRET)

    with open("data.dmp", "rb") as input:
        platform_ibj_list = pickle.load(input)

    printPlatformObjList(ovq_client, platform_ibj_list)
    # printPlatformObjectCount(platformObjList)



if __name__ == "__main__":
    main()