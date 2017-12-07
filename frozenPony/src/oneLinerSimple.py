#!/usr/bin/env python3
import getpass
import csv
import netmiko
import paramiko
from argparse import ArgumentParser


def main():
    parser = ArgumentParser(description='Arguments for running oneLiner.py')
    parser.add_argument('-c', '--csv', required=True, action='store', help='Location of CSV file')
    args = parser.parse_args()

    ssh_username = input("SSH username: ")
    ssh_password = getpass.getpass('SSH Password: ')

    with open(args.csv, "r") as file:
        reader = csv.DictReader(file)
        for device_row in reader:
            try:
                ssh_session = netmiko.ConnectHandler(device_type='cisco_ios', ip=device_row['device_ip'],
                                                     username=ssh_username, password=ssh_password)

                print("+++++ {0} +++++".format(device_row['device_ip']))
                ssh_session.send_command("terminal length 0")
                print(ssh_session.send_command("sh ip int br"))
                ssh_session.send_command("terminal length 30")
                ssh_session.disconnect()

            except (netmiko.ssh_exception.NetMikoTimeoutException,
                    netmiko.ssh_exception.NetMikoAuthenticationException,
                    paramiko.ssh_exception.SSHException) as s_error:
                print(s_error)


if __name__ == "__main__":
    main()
