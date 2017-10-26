#!/usr/bin/env python3
import getpass
import re
import csv
from argparse import ArgumentParser
from netmiko import ConnectHandler

if __name__ == "__main__":
    parser = ArgumentParser(description='Arguments for running oneLiner.py')
    parser.add_argument('-c', '--csv', required=True, action='store', help='Location of CSV file')
    args = parser.parse_args()

    ssh_username = input("SSH username: ")
    ssh_password = getpass.getpass('SSH Password: ')

    stats = [0, 0]

    with open(args.csv, "r") as file:
        reader = csv.DictReader(file)
        for device_row in reader:
            ssh_session = ConnectHandler(device_type='cisco_ios', ip=device_row['device_ip'],
                                         username=ssh_username, password=ssh_password)
            c_commands = device_row['config_command']
            ssh_session.send_config_set([c_commands])

            if re.search(c_commands, ssh_session.send_command("sh run | inc {0}".format(c_commands))):
                stats[0] += 1
            else:
                stats[1] += 1

    print("{0} devices parsed, success/ failure: {1}/{2}".format(stats[0]+stats[1], stats[0], stats[1]))
