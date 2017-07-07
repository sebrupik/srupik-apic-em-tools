import getpass
import argparse

import re
import io
import pexpect
from netmiko import ConnectHandler
from ftplib import FTP
from datetime import date

from uniq_login import login

platform_nxos = ["N1K-", "N2K-", "N5K-", "N7K-"]
platform_iosxe = ["WS-C3850"]
platform_ios = ["WS-C2960", "WS-C3750"]


class NetworkDevice:
    def __init__(self, id, hostname, platform_type, vrf):
        self.id = id
        self.hostname = hostname
        self.platform_type = platform_type
        self.vrf = vrf
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


class SSHSession:
    def __init__(self, ip_address, username, secret, enable):
        self.ip_address = ip_address
        self.username = username
        self.secret = secret

        if not enable:
            self.enable = secret
        else:
            self.enable = enable

        self._gen_ssh_connection()


    def _gen_ssh_connection(self):
        try:
            self.ssh_session = pexpect.spawnu('ssh -l {0}@{1}'.format(self.username, self.ip_address))

            i = self.ssh_session.expect(["assword:", "yes"])
            if i == 0:
                self.ssh_session.sendline(self.secret)
            elif i == 1:
                self.ssh_session.sendline("yes")
                self.ssh_session.expect("assword:")
                self.ssh_session.sendline(self.secret)

            i = self.ssh_session.expect([">", "#"])
            if i == 0:
                self.ssh_session.sendline("en")
                self.ssh_session.expect("assword:")
                self.ssh_session.sendline(self.enable)

                self.ssh_session.expect("#")
                self.ssh_session.sendline("terminal length 0")
        except pexpect.TIMEOUT:
            exit()
            return "FAIL"


    def send_command(self, commands=[]):
        self.output_buffer - io.StringIO()
        for c in commands:
            self.output_buffer.write(self.send_command(c))

        try:
            return self.output_buffer.getvalue()
        finally:
            self.output_buffer.close()


    def send_command(self, command):
        self.ssh_session.sendline(command)
        self.ssh_session.expect("#")

        return self.ssh_session.before




def build_device_dict():
    dict = {}

    dict['IOS'] = platform_ios
    dict['IOS-XE'] = platform_iosxe
    dict['NX-OS'] = platform_nxos

    return dict

def determine_platform(ssh_session):
    output = ssh_session.send_command("sh ver")
    line = output.splitlines()[0]
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


def prepare_ftp_destination(ftp_ip, ftp_username, ftp_password, ftp_directory_root, ftp_directory_cur):
    ftp = FTP(ftp_ip)  # connect to host, default port
    ftp.login(ftp_username, ftp_password)

    if not ftp_directory_root in ftp.nlst():
        ftp.mkd(ftp_directory_root)
        ftp.cwd(ftp_directory_root)
        ftp.mkd(ftp_directory_cur)
    else:
        print("The licenceHarvest FTP root dir already exists")


def determine_ip_vrf(ssh_session, ip_address):
    output_vrf = ssh_session.send_command("show vrf")
    for line in output_vrf.splitlines()[1:]:
        vrf = line.split()[0]
        output_ipint = ssh_session.send_command("show ip int br vrf {0}".format(vrf)).splitlines()

        for i in output_ipint :
            if i.find(ip_address) != -1:
                print("VRF is: {0}".format(vrf))
                return vrf

    return "default"  # how did we end here?!


def get_license_state(ssh_session, current_device):
    if current_device.platform_type == "IOS":
        print("IOS")
    elif current_device.platform_type == "IOS-XE":
        print("IOS-XE")
        output_lic_rtu = ssh_session.send_command("sh license right-to-use summary | inc Lifetime").splitlines()
        for l in output_lic_rtu:
            ar = l.split()
            license_obj = IOSXELicence(ar)
            current_device.licences.append(license_obj)


    elif current_device.platform_type == "NX-OS" :
        output_lic_file = ssh_session.send_command("show license br").splitlines()

        for line in output_lic_file:
            license_obj = NXLicence(line)
            output_lic_file_detail = ssh_session.send_command("show license file {0}".format(line)).splitlines()
            for l in output_lic_file_detail:
                if l.find("INCREMENT") != -1:
                    license_feature = NXLicenceFeature(l.split()[1])
                    output_lic_feature = ssh_session.send_command("show license usage {0}".format(license_feature.feature_name))
                    if len(output_lic_feature) > 0:
                        license_feature.applications = output_lic_feature.splitlines()[2:-1]

                    license_obj.features.append(license_feature)

            current_device.licences.append(license_obj)


def backup_licenceFiles(ssh_session, current_device, ftp_username, ftp_password, ftp_ip, ftp_directory_root, ftp_directory_cur):
    if current_device.platform_type == "NX-OS":
        print(ssh_session.send_command("copy licenses bootflash:///{0}_all_licenses.tar".format(current_device.hostname)))
        print("copy licenses bootflash:///{0}_all_licenses.tar".format(current_device.hostname))
        print(ssh_session.send_command("copy bootflash:///{0}_all_licenses.tar ftp://{1}@{2}/{3}/{4} vrf {5}".format(current_device.hostname, ftp_username, ftp_ip, ftp_directory_root, ftp_directory_cur, current_device.vrf), expect_string="Password:"))
        print("copy bootflash:///{0}_all_licenses.tar ftp://{1}@{2}/{3}/{4} vrf {5}".format(current_device.hostname, ftp_username, ftp_ip, ftp_directory_root, ftp_directory_cur, current_device.vrf))
        print("the prompt now says: {0}".format(ssh_session.find_prompt()))
        ##if ssh_session.find_prompt() == "Password:":
        ##    print("we've got the password prompt")
        ssh_session.send_command(ftp_password)

        ssh_session.send_command("delete bootflash:///{0}_all_licenses.tar".format(current_device.hostname))
    elif current_device.platform_type == "IOS-XE":
        print("IOS-XE")


def apply_apic_device_tag(apic, device, tag_id):
    apic.tag.addTagToResource(tagDto={"id": tag_id, "resourceId": device.id, "resourceType": "network-device"})


def create_apic_device_tag(apic, tag_name):
    tag_id = get_apic_tag_id(apic, tag_name)
    if tag_id is None:
        #print("lets add it...")
        task = apic.tag.addTag(tagDto={"tag": tag_name, "resourceType": "network-device"})
        task_response = apic.task_util.wait_for_task_complete(task, timeout=5)
        return get_apic_tag_id(apic, tag_name)
    else:
        return tag_id


def get_apic_tag_id(apic, tag_name):
    #allTagsResponse = apic.tag.getTags(resourceType="network-device")
    allTagsResponse = apic.tag.getTags()
    for tag in allTagsResponse.response:
        if tag.tag == tag_name:
            return tag.id

    return None


def get_apic_tag_association(apic, tag_name):
    if tag_name is None:
        apicResponse = apic.networkdevice.getAllNetworkDevice()
    else:
        apicResponse = apic.tag.getTagsAssociation(tag=tag_name)

    all_ids = []
    for tag in apicResponse.response:
        all_ids.append(tag.id)

    return all_ids

#def process_device(apic, device_id):



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
    parser.add_argument('-fi', '--ftpip',
                        required=False,
                        action='store',
                        help='FTP server IP.')
    parser.add_argument('-fu', '--ftpusername',
                        required=False,
                        action='store',
                        help='FTP username.')
    parser.add_argument('-fp', '--ftppassword',
                        required=False,
                        action='store',
                        help='FTP password.')
    return parser


def main() :
    parser = argparser()
    args = parser.parse_args()
    apic = login(args)
    d = date.today()

    refresh = False
    using_parser = False
    if args.cluster or args.username or args.password:
        using_parser = True

    ssh_username = args.username or None
    ssh_password = args.password or None
    ftp_ip = args.ftpip or None
    ftp_username = args.ftpusername or None
    ftp_password = args.ftppassword or None

    client = None

    ssh_username_prompt = 'SSH Username[{}]: '.format(ssh_username) if ssh_username else 'SSH Username: '
    ssh_password_prompt = 'SSH password[{}]: '.format(ssh_password) if ssh_password else 'SSH Password: '
    ftp_ip_prompt = 'FTP IP address[{}]: '.format(ftp_ip) if ftp_ip else 'FTP IP address: '
    ftp_username_prompt = 'FTP username[{}] '.format(ftp_username) if ftp_username else 'FTP Username: '
    ftp_password_prompt =  'FTP password[{}] '.format(ftp_password) if ftp_password else 'FTP Password: '

    if not using_parser or not ssh_username:
        ssh_username = input(ssh_username_prompt) or ssh_username
    if not using_parser or not ssh_password:
        ssh_password = getpass.getpass('Password: ') or ssh_password
    if not using_parser or not ftp_ip:
        ftp_ip = input(ftp_ip_prompt) or ftp_ip_prompt
    if not using_parser or not ftp_username:
        ftp_username = input(ftp_username_prompt) or ftp_username_prompt
    if not using_parser or not ftp_password:
        ftp_password  = getpass.getpass('Password: ') or ftp_password

    using_parser = False

    network_device_list = []
    device_dictionary = build_device_dict()

    prepare_ftp_destination(ftp_ip, ftp_username, ftp_password, "licenceHarvest", d.isoformat())

    tag_id = create_apic_device_tag(apic, "licensed")
    print("TAG name: {0}, Tag ID: {1}".format("licensed", tag_id))

    if refresh:
        device_ids = get_apic_tag_association(apic, "licensed")
    else:
        device_ids = get_apic_tag_association(apic, None)

    for device_id in device_ids:
        apicResponse = apic.networkdevice.getNetworkDeviceById(id=device_id)
        device = apicResponse.response

        # if device.platformId is not None:
        #if device.platformId.find("N5K-") != -1:
        # if device.platformId.find("WS-C3850") != -1:
        if device.hostname.find("CHAN02-INT-NOX-SW18") != -1:
            #ssh_session = ConnectHandler(device_type='cisco_ios', ip=device.managementIpAddress, username=ssh_username, password=ssh_password)
            ssh_session = SSHSession(ip_address=device.managementIpAddress, username=ssh_username, secret=ssh_password, enable=None)

            current_device = NetworkDevice(device.id, device.hostname,
                                           determine_platform2(device.platformId, device_dictionary),
                                           determine_ip_vrf(ssh_session, device.managementIpAddress))

            get_license_state(ssh_session, current_device)
            print(current_device)

            if len(current_device.licences) > 0:
                backup_licenceFiles(ssh_session, current_device, ftp_username, ftp_password, ftp_ip, "licenceHarvest",
                                    d.isoformat())
                apply_apic_device_tag(apic, device, tag_id)

            ssh_session.send_command("exit")

            network_device_list.append(current_device)


if __name__ == "__main__":
    main()