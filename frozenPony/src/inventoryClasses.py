

# Have made these explicit new-style classes, so that they are compatitble between v2.7 and v3
class PlatformObj(object):
    def __init__(self, platform_id, os_type):
        self.platform_id = platform_id
        self.os_type = os_type
        self.models = {}

        print("new platformObj {0}, {1}".format(platform_id, os_type))


class SoftwareVersionObj(object):
    def __init__(self, software_version, hostname, device_id):
        self.software_version = software_version
        self.hostnames = []
        self.device_ids = []

        self.hostnames.append(hostname)
        self.device_ids.append(device_id)
