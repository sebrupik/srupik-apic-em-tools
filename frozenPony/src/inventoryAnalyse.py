#!/usr/bin/env python2

import requests
import re
import pickle
from openVulnQuery import query_client
from config.cisco_apiconsole import CLIENT_ID, CLIENT_SECRET


def cleanup_ios_xe(input_str):
    str1 = re.sub(r"[0]", "", input_str)

    if len(str1.split(".")) > 3:
        index = str1.rfind(".")
        new_str = str1[:index] + str1[index + 1:]
    else:
        new_str = str1

    return new_str


def escape_brackets(input_str):
    return re.sub(r'([\( \)])', r'\\\1', input_str)


def print_relevant_advisories(advisories):
    for adv in advisories:
        print("      {0} - {1}".format(adv.advisory_id, adv.advisory_title))
        print("        BUGIDs:")
        for bug in adv.bug_ids:
            print("         {0}".format(bug))

        print("      First fixed")
        for fixed in adv.first_fixed:
            print("         {0}".format(fixed))

def print_relevant_cvrf(advisories, platform_id):
    for adv in advisories:
        if any(platform_id in p for p in adv.product_names):
            print("      {0} - {1}".format(adv.advisory_id, adv.advisory_title))
            print("        BUGIDs:")
            for bug in adv.bug_ids:
                print("         {0}".format(bug))


def print_relevant(advisories, sv, hostnames, platform_id, cvrf=False):
    print("  Running version: {0} , {1} advisories, {2} devices".format(sv, len(advisories), len(hostnames)))
    print("    Devices effected: {0}".format(", ".join(hostnames)))
    if cvrf:
        print_relevant_cvrf(advisories, platform_id)
    else:
        print_relevant_advisories(advisories)


def print_platform_object_count(po_list):
    print("Platforms: {0}".format(len(po_list)))

    for po in po_list:
        print("Platform {0} has {1} software versions.".format(po.platformID, len(po.softwareVersion)))


def print_platform_obj(query_client, po):
    print("Platform: {0}".format(po.platform_id))
    device_dict = get_software_versions(po)
    for sv in device_dict.keys():
        hostnames = device_dict[sv]
        try:
            if po.os_type == "IOS":
                print_relevant(query_client.get_by_ios(sv), sv, hostnames, po.platform_id)
            elif po.os_type == "IOS-XE":
                print_relevant(query_client.get_by_ios_xe(cleanup_ios_xe(sv)), sv, hostnames, po.platform_id)
            elif po.os_type == "NX-OS":
                print_relevant(query_client.get_by_product("cvrf", "NX-OS"), sv, hostnames, po.platform_id, True)
            else:
                print("Can't help you with this OS type: {0}".format(po.os_type))

        except requests.exceptions.HTTPError as exc_info:
            print(exc_info)


def get_software_versions(platform_object):
    output = {}

    for model_type_full in platform_object.models.keys():
        sv_list = platform_object.models.get(model_type_full)
        for sv in sv_list:
            #if output.has_key(sv.software_version):
            if sv.software_version in output:
                output[sv.software_version].extend(sv.hostnames)
            else:
                output[sv.software_version] = sv.hostnames

    return output


def print_platform_obj_list(query_client, po_list):
    for po in po_list:
        print_platform_obj(query_client, po)


def main():
    ovq_client = query_client.OpenVulnQueryClient(CLIENT_ID, CLIENT_SECRET)

    with open("data.dmp", "rb") as input_file:
        platform_ibj_list = pickle.load(input_file)

    print_platform_obj_list(ovq_client, platform_ibj_list)


if __name__ == "__main__":
    main()
