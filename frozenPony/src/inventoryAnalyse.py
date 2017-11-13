#!/usr/bin/env python2

import requests
import re
import pickle
import json
from openVulnQuery import query_client
from config.cisco_apiconsole import CLIENT_ID, CLIENT_SECRET


def merge_two_dicts(x, y):
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z


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


def get_software_versions(platform_object):
    output = {}

    for model_type_full in platform_object.models.keys():
        sv_list = platform_object.models.get(model_type_full)
        for sv in sv_list:
            if sv.software_version in output:
                output[sv.software_version].extend(sv.hostnames)
            else:
                output[sv.software_version] = sv.hostnames

    return output


def build_dictionary_relevant_advisories(advisories):
    adv_list = []
    for adv in advisories:
        adv_dict = dict()
        adv_dict["advisory_id"] = adv.advisory_id
        adv_dict["advisory_title"] = adv.advisory_title
        adv_dict["bug_ids"] = adv.bug_ids
        adv_dict["first_fixed"] = adv.first_fixed
        adv_list.append(adv_dict)

    return adv_list


def build_dictionary_relevant_cvrf(advisories, platform_id):
    adv_list = []
    for adv in advisories:
        if any(platform_id in p for p in adv.product_names):
            adv_dict = dict()
            adv_dict["advisory_id"] = adv.advisory_id
            adv_dict["advisory_title"] = adv.advisory_title
            adv_dict["bug_ids"] = adv.bug_ids
            adv_list.append(adv_dict)

    return adv_list


def build_dictionary_relevant(advisories, platform_id, cvrf=False):
    relevant = dict()
    relevant["advisory_count"] = len(advisories)

    if cvrf:
        relevant["advisories"] = build_dictionary_relevant_cvrf(advisories, platform_id)
    else:
        relevant["advisories"] = build_dictionary_relevant_advisories(advisories)

    return relevant


def build_dictionary_platform(query_client, po):
    platform = dict()
    platform["platform_id"] = po.platform_id
    platform["os"] = po.os_type
    platform["software_version"] = []

    device_dict = get_software_versions(po)
    for sv in device_dict.keys():
        sv_dict = dict()
        hostnames = device_dict[sv]

        try:
            sv_dict["version"] = sv
            sv_dict["device_count"] = len(hostnames)
            sv_dict["hostnames"] = hostnames
            if po.os_type == "IOS":
                sv_dict = merge_two_dicts(sv_dict,
                                          build_dictionary_relevant(query_client.get_by_ios(sv), po.platform_id))
            elif po.os_type == "IOS-XE":
                sv_dict = merge_two_dicts(sv_dict,
                                          build_dictionary_relevant(query_client.get_by_ios_xe(cleanup_ios_xe(sv)),
                                                                    po.platform_id))
            elif po.os_type == "NX-OS":
                sv_dict = merge_two_dicts(sv_dict,
                                          build_dictionary_relevant(query_client.get_by_product("cvrf", "NX-OS"),
                                                                    po.platform_id, True))
            else:
                print("Can't help you with this OS type: {0}".format(po.os_type))

        except requests.exceptions.HTTPError as exc_info:
            print(exc_info)

        platform["software_version"].append(sv_dict)

    return platform


def build_dictionary(query_client, po_list):
    platforms = []
    for po in po_list:
        platforms.append(build_dictionary_platform(query_client, po))

    return platforms


def insert_offender(offenders_list, offender_dict):
    if len(offenders_list) <= 0:
        offenders_list.append(offender_dict)
    else:
        for i, offender in enumerate(offenders_list):
            if offender_dict["advisory_count"] > offender["advisory_count"]:
                offenders_list.insert(i, offender_dict)
                break

        offenders_list.insert(len(offenders_list) - 1, offender_dict)


def print_dictionary(platforms_dictionary, brief=True, raw=False):
    offenders_list = []

    if raw:
        print(json.dumps(platforms_dictionary, indent=2))
    else:
        for platform in platforms_dictionary:
            print("{0} has {1} software versions in use".format(platform["platform_id"],
                                                                len(platform["software_version"])))

            for software_version in platform["software_version"]:
                print("  {0} used by {1} devices".format(software_version["version"],
                                                         len(software_version["hostnames"])))
                print("    {0}".format(", ".join(software_version["hostnames"])))
                if "advisories" in software_version:
                    insert_offender(offenders_list, {"advisory_count": len(software_version["advisories"]),
                                                     "version": software_version["version"],
                                                     "hostnames": ", ".join(software_version["hostnames"])})

                    if brief:
                        print("    Number of advisories {0}".format(len(software_version["advisories"])))
                    else:
                        for adv in software_version["advisories"]:
                            print("      ID {0} -- {1}".format(adv["advisory_id"], adv["advisory_title"]))
                            print("      First fixed: {0}".format(", ".join(adv["first_fixed"])))
                            print("      Bug IDs: {0}".format(", ".join(adv["bug_ids"])))
                else:
                    print("    No advisories :)")

    print("\n")
    index = 0
    top = 5
    print("Worst offenders - Top {0}".format(top))
    while index <= top:
        print("Advisory count: {0}".format(offenders_list[index]["advisory_count"]))
        print("  {0}".format(offenders_list[index]["version"]))
        print("  {0}".format(offenders_list[index]["hostnames"]))
        index = index + 1


def main():
    ovq_client = query_client.OpenVulnQueryClient(CLIENT_ID, CLIENT_SECRET)

    with open("data.dmp", "rb") as input_file:
        platform_ibj_list = pickle.load(input_file)

    print_dictionary(build_dictionary(ovq_client, platform_ibj_list))


if __name__ == "__main__":
    main()
