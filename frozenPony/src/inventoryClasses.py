
'''Have made these explicit new-style classes, so that they are compatitble between v2.7 and v3'''
class PlatformObj(object):
    def __init__(self, platform_id):
        self.platform_id = platform_id
        self.models = {}

    #def __repr_(self):
    #    return "{0}: {1} {2}".format(self.__class__.__name__, self.platformID, len.self(softwareVersion))

    #def __cmp__(self, other):
    #    if hasattr(other, 'platformID'):
    #        return self.platformID.__cmp__(other.platformID)


class SoftwareVersionObj(object):
    def __init__(self, software_version, hostname, device_id):
        self.software_version = software_version
        self.hostnames = []
        self.device_ids = []

        self.hostnames.append(hostname)
        self.device_ids.append(device_id)