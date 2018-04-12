#!/usr/bin/env python3

import getpass
import pickle
import re
import csv
import netmiko
import paramiko

from argparse import ArgumentParser
from inventoryClasses import PlatformObj, SoftwareVersionObj
from uniq_login import login

platform_nxos = ["N1K-", "N2K-", "N5K-", "N7K-"]
platform_iosxe = ["C3850"]
platform_ios = ["C2960", "C3560", "C3750", "C650", "CISCO72"]

SH_INV_REGEX = ".*?PID: (?P<type>.*?)\s*,"

def build_device_dict():
    device_dict = {'IOS': platform_ios, 'IOS-XE': platform_iosxe, 'NX-OS': platform_nxos}

    return device_dict


def determine_platform2(platform_id, device_dict):
    keys = device_dict.keys()

    for k in keys:
        for e in device_dict[k]:
            if re.search(e, platform_id):
                return k

    return None


def add_platform(polist, model_type_full_list, software_version, hostname, device_id, os_type):
    for model_type_full in model_type_full_list:
        create_new = True
        model_type_brief = retreive_platform_line(model_type_full, os_type)
        for po in polist:
            if po.platform_id == model_type_brief:
                create_new = False
                add_model(po, model_type_full, software_version, hostname, device_id)

        if create_new:
            new_po = PlatformObj(model_type_brief, os_type)
            add_model(new_po, model_type_full, software_version, hostname, device_id)
            polist.append(new_po)


def add_model(platform_object, model_type_full, software_version, hostname, device_id):
    create_new = True
    if model_type_full not in platform_object.models:
        platform_object.models[model_type_full] = []

    for po_model in platform_object.models.keys():
        if po_model == model_type_full:
            create_new = False
            add_software_version(platform_object.models.get(po_model), software_version, hostname, device_id)

    if create_new:
        platform_object.models[model_type_full] = [SoftwareVersionObj(software_version, hostname, device_id)]


def add_software_version(sv_list, software_version, hostname, device_id):
    create_new = True
    for sv in sv_list:
        if sv.software_version == software_version:
            create_new = False
            if hostname not in sv.hostnames:
                sv.hostnames.append(hostname)
                sv.device_ids.append(device_id)

    if create_new:
        sv_list.append(SoftwareVersionObj(software_version, hostname, device_id))


def retreive_platform_line(platform_name_full, os_type):
    name_elements = platform_name_full.split("-")
    if len(name_elements) > 1:
        if os_type == "NX-OS":
            return list(name_elements[1])[1].ljust(4, "0")
        else:
            return name_elements[1]
    else:
        return platform_name_full


def print_platform_object_count(po_list):
    print("Platforms: {0}".format(len(po_list)))

    for po in po_list:
        print("Platform {0} has {1} models.".format(po.platform_id, len(po.models)))
        for model_type_full in po.models.keys():
            print("  "+model_type_full)
            for sv in po.models.get(model_type_full):
                print("    {0} used by {1} devices, {2}".format(sv.software_version, len(sv.hostnames), ", ".join(sv.hostnames)))


def process_csv_device(device_row, ssh_username, ssh_password):
    device_detail = [None]*4
    try:
        ssh_session = netmiko.ConnectHandler(device_type='cisco_ios', ip=device_row['device_ip'],
                                             username=ssh_username, password=ssh_password)

        print("+++++ {0} +++++".format(device_row['device_ip']))
        ssh_session.send_command("terminal length 0")
        device_version = ssh_session.send_command("sh ver")
        device_inventory = ssh_session.send_command("sh inv")
        hostname = ssh_session.find_prompt()[:-1]
        ssh_session.send_command("terminal length 30")
        ssh_session.disconnect()

        device_version_first = device_version.splitlines()[0].split(", ")
        print(device_version_first)
        if device_version_first[0].startswith("Cisco IOS Software"):
            device_detail[1] = device_version_first[2].split(" ")[1]
            print("**** "+device_detail[1])
            device_detail[3] = device_version_first[0].split(" ")[1]
        elif device_version_first[0].startswith("Cisco IOS XE Software"):
            device_detail[1] = device_version_first[1].split(" ")[1]
            device_detail[3] = "-".join([device_version_first[0].split(" ")[1], device_version_first[0].split(" ")[2]])

        match = re.search(SH_INV_REGEX, device_inventory)
        if match:
            device_detail[0] = [match.group("type")]

        device_detail[2] = hostname

        print(device_detail)
        return device_detail

    except (netmiko.ssh_exception.NetMikoTimeoutException,
            netmiko.ssh_exception.NetMikoAuthenticationException,
            paramiko.ssh_exception.SSHException) as s_error:
        print(s_error)

    return None


def main():
    platform_obj_list = []
    device_dictionary = build_device_dict()

    parser = ArgumentParser(description='Arguments for running oneLiner.py')
    parser.add_argument('-c', '--csv', required=False, action='store', help='Location of CSV file')
    args = parser.parse_args()

    if args.csv:
        ssh_username = input("SSH username: ")
        ssh_password = getpass.getpass('SSH Password: ')

        with open(args.csv, "r") as file:
            reader = csv.DictReader(file)
            for device_row in reader:
                device_detail = process_csv_device(device_row, ssh_username, ssh_password)
                if device_detail is not None:
                    add_platform(platform_obj_list, device_detail[0], device_detail[1], device_detail[2], None,
                                 device_detail[3])

    else:
        apic = login()

        all_devices_response = apic.networkdevice.getAllNetworkDevice()
        for device in all_devices_response.response:
            if device.platformId is not None:
                os_type = determine_platform2(device.platformId.split()[0], device_dictionary)
                add_platform(platform_obj_list, device.platformId.replace(" ", "").split(","),
                             device.softwareVersion, device.hostname, device.id, os_type)

    print_platform_object_count(platform_obj_list)
    print("Pickle the data!")

    with open("data.dmp", "wb") as output:
        pickle.dump(platform_obj_list, output, 2)


if __name__ == "__main__":
    main()
