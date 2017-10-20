#!/usr/bin/env python3
from uniq_login import login


def get_apic_tag_association(apic, tag_name):
    all_ids = []
    if tag_name is None:
        apic_response = apic.networkdevice.getAllNetworkDevice()
    else:
        apic_response = apic.tag.getTagsAssociation(tag=tag_name)

    for tag in apic_response.response:
        all_ids.append(tag.id)

    return all_ids


def main():
    apic = login()

    device_ids = get_apic_tag_association(apic, "desktop-switch")

    for device_id in device_ids:
        apic_response = apic.networkdevice.getNetworkDeviceById(id=device_id)
        device = apic_response.response

        if device.platformId is None:
            break




if __name__ == "__main__":
    main()
