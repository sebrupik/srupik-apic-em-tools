import getpass
import argparse
import re
from netmiko import ConnectHandler

from uniq_login import login

platform_nxos = ["N1K-", "N2K-", "N5K-", "N7K-"]
platform_iosxe = ["WS-C3850"]
platform_ios = ["WS-C2960", "WS-C3750"]


class NetworkDevice:
    def __init__(self, id, hostname):
        self.id = id
        self.hostname = hostname
        self.licences = []

    def __str__(self):
        output = "Hostname: {0}, ID: {1}, number of licenses: {2} \n".format(self.hostname, self.id, len(self.licences))
        for l in self.licences:
            output += str(l)

        return output


class IOSXELicence :
    def __init__(self, ar):
        self.name = ar[0]
        self.type = ar[1]
        self.count = ar[2]
        self.period = ar[3]

    def __str__(self):
        return "  "+self.name+" "+self.type+" "+self.count+" "+self.period+"\n"


class NXLicence:
    def __init__(self, name):
        self.name = name
        self.features = []

    def __str__(self):
        output = "  Filename: {0}, number of features: {1} \n".format(self.name, len(self.features))
        for f in self.features:
            output += str(f)

        return output


class NXLicenceFeature:
    def __init__(self, feature_name):
        self.feature_name = feature_name
        self.applications = []

    def __str__(self):
        output = "    Feature: {0}, number of applications: {1} \n".format(self.feature_name, len(self.applications))
        for a in self.applications:
            output += "      Application: {0} \n".format(a)

        return output


def build_device_dict():
    dict = {}

    dict['IOS'] = platform_ios
    dict['IOS-XE'] = platform_iosxe
    dict['NX-OS'] = platform_nxos

    return dict

def determine_platform(ssh_session):
    output = ssh_session.send_command("sh ver")
    line = output.splitlines()[0]
    #print(line)
    if line.find("IOS") != -1:
        if output.find("ROM: IOS-XE ROMMON") != -1:
            return "IOS-XE"
        return "IOS"
    elif line.find("NX-OS") != -1:
       return "NX-OS"


def determine_platform2(platformId, dict):
    keys = dict.keys()

    for k in keys:
        for e in dict[k]:
            if re.search(e, platformId):
                return k

    return None


def determine_ip_vrf(ssh_session, ip_address):
    output_vrf = ssh_session.send_command("show vrf")
    for line in output_vrf.splitlines()[1:]:
        vrf = line.split()[0]
        output_ipint = ssh_session.send_command("show ip int br vrf {0}".format(vrf))

        for i in output_ipint :
            if i.find(ip_address):
                return vrf

    return "default"  # how did we end here?!

def get_license_state(ssh_session, current_device, platform_type, vrf):
    #print("get_license_state :: {0}, {1}, {2}".format(current_device.hostname, platform_type, vrf))

    if platform_type == "IOS":
        print("IOS")
    elif platform_type == "IOS-XE":
        print("IOS-XE")
        output_lic_rtu = ssh_session.send_command("sh license right-to-use summary | inc Lifetime").splitlines()
        for l in output_lic_rtu:
            ar = l.split()
            license_obj = IOSXELicence(ar)
            current_device.licences.append(license_obj)


    elif platform_type == "NX-OS" :
        output_lic_file = ssh_session.send_command("show license br").splitlines()

        for line in output_lic_file:
            #print("print line value ", line)
            license_obj = NXLicence(line)
            output_lic_file_detail = ssh_session.send_command("show license file {0}".format(line)).splitlines()
            for l in output_lic_file_detail:
                if l.find("INCREMENT") != -1:
                    license_feature = NXLicenceFeature(l.split()[1])
                    output_lic_feature = ssh_session.send_command("show license usage {0}".format(license_feature.feature_name))
                    #print("output_lic_feature: ", output_lic_feature, len(output_lic_feature), type(output_lic_feature))
                    if len(output_lic_feature) > 0:
                        license_feature.applications = output_lic_feature.splitlines()[2:-1]

                    license_obj.features.append(license_feature)

            current_device.licences.append(license_obj)

        if len(current_device.licences) > 0:
            print("we have licenses, lets back them up!")
            #ssh_session.send_command("copy licenses bootflash:///all_licenses.tar")
            #ssh_session.send_command("copy bootflash:all_licenses.tar ftp://{0}@{1} vrf {2}".format(FTP_USERNAME, FTP_IP, vrf))


def set_apic_em_license_flag(apic, device_id, licenses):
    print("Set device tag")


def argparser():
    """ Returns an argparser instance (argparse.ArgumentParser) to support command line options."""

    parser = argparse.ArgumentParser(description='Arguments for logging in APIC-EM cluster.')
    parser.add_argument('-c', '--cluster',
                        required=False,
                        action='store',
                        help='cluster ip/name of APIC-EM.')
    parser.add_argument('-u', '--username',
                        required=False,
                        action='store',
                        help='Username to login.')
    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        help='Password to login.')
    return parser


def main() :
    parser = argparser()
    args = parser.parse_args()
    apic = login(args)

    using_parser = False
    if args.cluster or args.username or args.password:
        using_parser = True

    ssh_username = args.username or None
    ssh_password = args.password or None
    client = None

    ssh_username_prompt = 'SSH Username[{}]: '.format(ssh_username) if ssh_username else 'SSH Username: '
    ssh_password_prompt = 'SSH password[{}]: '.format(ssh_password) if ssh_password else 'SSH Password: '

    if not using_parser or not ssh_username:
        ssh_username = input(ssh_username_prompt) or ssh_username
    if not using_parser or not ssh_password:
        ssh_password = getpass.getpass('Password: ') or ssh_password
    using_parser = False



    network_device_list = []
    device_dictionary = build_device_dict()


    allDevicesResponse = apic.networkdevice.getAllNetworkDevice()
    for device in allDevicesResponse.response:
        #if device.platformId is not None:
        if device.platformId.find("N5K-") != -1 :
        #if device.platformId.find("WS-C3850") != -1:
         #if device.hostname.find("CHAN02-ACCESS-01") != -1:

            ssh_session = ConnectHandler(device_type='cisco_ios', ip=device.managementIpAddress, username=ssh_username, password=ssh_password)

            current_device = NetworkDevice(device.id, device.hostname)

            vrf = determine_ip_vrf(ssh_session, device.managementIpAddress)
            if vrf != "ERROR":
                #get_license_state(ssh_session, current_device, determine_platform(ssh_session), vrf)
                get_license_state(ssh_session, current_device, determine_platform2(device.platformId, device_dictionary), vrf)

                print(current_device)

                #if len(current_device.licences)>0 :
                #    set_apic_em_license_flag(apic, current_device.id, True)

                network_device_list.append(current_device)
            else:
                print("Could not find the VRF used by the management IP, aborting device")




if __name__ == "__main__":
    main()