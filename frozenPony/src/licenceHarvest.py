import getpass
import argparse

import re
import io
import pexpect
import os
from ftplib import FTP, all_errors
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
            self.ssh_session = pexpect.spawnu('ssh -l {0} {1}'.format(self.username, self.ip_address))

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
            return "FAILED TO ESTABLISH SSH CONNECTION"


    def _tidy_output(self, output):
        #ugh this is basic! just remove the command supplied and the prompt!
        output_list = output.split("\n")[1:-1]

        return ("\n").join(output_list)


    def send_command(self, commands=[]):
        self.output_buffer = io.StringIO()
        for c in commands:
            self.output_buffer.write(self.send_command(c))

        try:
            return self.output_buffer.getvalue()
        finally:
            self.output_buffer.close()


    def send_command(self, command, expect_string=None):
        try:
            self.ssh_session.sendline(command)
            if not expect_string:
                self.ssh_session.expect("#")
            else:
                self.ssh_session.expect(expect_string)

            return self._tidy_output(self.ssh_session.before)
        except pexpect.TIMEOUT:
            return "TIMEOUT"




def build_device_dict():
    dict = {'IOS': platform_ios, 'IOS-XE': platform_iosxe, 'NX-OS': platform_nxos}

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


def create_ftp_connection(ftp_ip, ftp_username, ftp_password):
    ftp_session = FTP(ftp_ip)  # connect to host, default port
    ftp_session.login(ftp_username, ftp_password)

    return ftp_session


def prepare_ftp_destination2(ftp_session, target_dir):
    folders = target_dir.split("/")

    for f in folders:
        if not f in ftp_session.nlst():
            print("Creating directory: {0}".format(f))
            ftp_session.mkd(f)

        ftp_session.cwd(f)


def backup_licenceFiles(ssh_session, current_device, ftp_ip, ftp_username, ftp_password, ftp_directory_root, ftp_directory_cur):
    if current_device.platform_type == "NX-OS":
        print(ssh_session.send_command("copy licenses bootflash:///{0}_all_licenses.tar".format(current_device.hostname)))
        print(ssh_session.send_command("copy bootflash:///{0}_all_licenses.tar ftp://{1}@{2}/{3}/{4}/ vrf {5}".format(current_device.hostname, ftp_username, ftp_ip, ftp_directory_root, ftp_directory_cur, current_device.vrf), expect_string="Password:"))
        ssh_session.send_command(ftp_password)

        ssh_session.send_command("delete bootflash:///{0}_all_licenses.tar no-prompt".format(current_device.hostname))
    elif current_device.platform_type == "IOS-XE":
        print("IOS-XE")


def apply_apic_device_tag(apic, device, tag_id):
    apic.tag.addTagToResource(tagDto={"id": tag_id, "resourceId": device.id, "resourceType": "network-device"})


def create_apic_device_tag(apic, tag_name):
    tag_id = get_apic_tag_id(apic, tag_name)
    if tag_id is None:
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


def argparser():
    """ Returns an argparser instance (argparse.ArgumentParser) to support command line options."""
    parser = argparse.ArgumentParser(description='Arguments for logging in APIC-EM cluster.')
    parser.add_argument('-c', '--cluster', required=False, action='store', help='cluster ip/name of APIC-EM.')
    parser.add_argument('-u', '--username', required=False, action='store', help='Username to login.')
    parser.add_argument('-p', '--password', required=False, action='store', help='Password to login.')
    parser.add_argument('-fi', '--ftpip', required=False, action='store', help='FTP server IP.')
    parser.add_argument('-fu', '--ftpusername', required=False, action='store', help='FTP username.')
    parser.add_argument('-fp', '--ftppassword', required=False, action='store', help='FTP password.')
    return parser


def main() :
    parser = argparser()
    args = parser.parse_args()
    apic = login(args)
    d = date.today()
    device_str = ""

    refresh = False
    using_parser = False
    if args.cluster or args.username or args.password:
        using_parser = True

    ssh_username = args.username or None
    ssh_password = args.password or None
    ftp_ip = args.ftpip or None
    ftp_username = args.ftpusername or None
    ftp_password = args.ftppassword or None

    #client = None

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

    network_device_list = []
    device_dictionary = build_device_dict()
    #ftp_session = prepare_ftp_destination(ftp_ip, ftp_username, ftp_password, "licenceHarvest", d.isoformat())
    ftp_session = create_ftp_connection(ftp_ip, ftp_username, ftp_password)
    prepare_ftp_destination2(ftp_session, "licenceHarvest/{0}".format(d.isoformat()))

    tag_id = create_apic_device_tag(apic, "licensed")
    print("TAG name: {0}, Tag ID: {1}".format("licensed", tag_id))

    if refresh:
        device_ids = get_apic_tag_association(apic, "licensed")
        print("Performing a refresh for {0} APIC-EM network devices".format(len(device_ids)))
    else:
        device_ids = get_apic_tag_association(apic, None)
        print("Performing a complete audit of {0} APIC-EM network devices".format(len(device_ids)))

    for device_id in device_ids:
        apicResponse = apic.networkdevice.getNetworkDeviceById(id=device_id)
        device = apicResponse.response

        if device.platformId is None:
            break

        if device.platformId.find("N5K-") != -1:
        # if device.platformId.find("WS-C3850") != -1:
            ssh_session = SSHSession(ip_address=device.managementIpAddress, username=ssh_username, secret=ssh_password, enable=None)

            current_device = NetworkDevice(device.id, device.hostname,
                                           determine_platform2(device.platformId, device_dictionary),
                                           determine_ip_vrf(ssh_session, device.managementIpAddress))

            get_license_state(ssh_session, current_device)
            print(current_device)
            device_str += str(current_device)+"\n"

            if len(current_device.licences) > 0:
                backup_licenceFiles(ssh_session, current_device, ftp_ip, ftp_username, ftp_password, "licenceHarvest",
                                    d.isoformat())
                apply_apic_device_tag(apic, device, tag_id)


            network_device_list.append(current_device)
    try:
        ftp_session.voidcmd("NOOP")
    except all_errors as e:
        print(e)
        print("Retrying FTP connection...")
        ftp_session = create_ftp_connection(ftp_ip, ftp_username, ftp_password)
        ftp_session.cwd("licenceHarvest/{0}".format(d.isoformat()))

    try:
        print(ftp_session.pwd())

        with open("temp.txt", "w") as text_file:
            text_file.write(device_str)

        ftp_session.storlines("STOR device_details.txt", open("temp.txt", "br"))

    finally:
        os.remove("temp.txt")
        ftp_session.quit()



if __name__ == "__main__":
    main()