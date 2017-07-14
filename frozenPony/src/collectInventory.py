#!/usr/bin/env python3
from uniq_login import login


class PlatformObj:
    def __init__(self, platform_id):
        self.platform_id = platform_id
        self.models = {}

    #def __repr_(self):
    #    return "{0}: {1} {2}".format(self.__class__.__name__, self.platformID, len.self(softwareVersion))

    #def __cmp__(self, other):
    #    if hasattr(other, 'platformID'):
    #        return self.platformID.__cmp__(other.platformID)


class SoftwareVersionObj:
    def __init__(self, software_version, hostname, device_id):
        self.softwareVersion = software_version
        self.hostnames = []
        self.device_ids = []

        self.hostnames.append(hostname)
        self.device_ids.append(device_id)


def add_platform(polist, model_type_full_list, software_version, hostname, device_id):

    for model_type_full in model_type_full_list:
        create_new = True
        model_type_brief = retreive_platform_line(model_type_full)
        for po in polist:
            if po.platform_id == model_type_brief:
                create_new = False
                add_model(po, model_type_full, software_version, hostname, device_id)

        if create_new:
            new_po = PlatformObj(model_type_brief)
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
        if sv.softwareVersion == software_version:
            create_new = False
            sv.hostnames.append(hostname)
            sv.device_ids.append(device_id)

    if create_new:
        sv_list.append(SoftwareVersionObj(software_version, hostname, device_id))


def retreive_platform_line(platform_name_full):
    name_elements = platform_name_full.split("-")
    if len(name_elements) > 1:
        return name_elements[1]
    else:
        return name_elements


def print_platform_object_count(po_list):
    print("Platforms: {0}".format(len(po_list)))

    for po in po_list:
        print("Platform {0} has {1} models.".format(po.platform_id, len(po.models)))
        for model_type_full in po.models.keys():
            print("  "+model_type_full)
            for sv in po.models.get(model_type_full):
                print("    {0} used by {1} devices".format(sv.softwareVersion, len(sv.hostnames)))


def main():
    apic = login()

    platform_obj_list = []

    all_devices_response = apic.networkdevice.getAllNetworkDevice()
    for device in all_devices_response.response:
        if device.platformId is not None:
            add_platform(platform_obj_list, device.platformId.replace(" ", "").split(","),
                         device.softwareVersion, device.hostname, device.id)

    print_platform_object_count(platform_obj_list)


if __name__ == "__main__":
    main()
