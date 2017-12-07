#!/usr/bin/env python3
import getpass
import re
import csv
import netmiko
import paramiko
from argparse import ArgumentParser


def remove_negation(c_command, c_negation):
    if c_negation:
        ar = c_command.split()
        if len(ar) > 2:
            return " ".join(ar[1:])
    return c_command


def check_command_entered(ssh_session, c_commands, stats, c_negation):
    # if re.search(c_commands,
    #              ssh_session.send_command(
    #                  "sh run | inc {0}".format(remove_negation(c_commands, c_negation)))):
    if check_for_command(ssh_session, c_commands, remove_negation(c_commands, c_negation)):
        if c_negation:
            stats[1] += 1
        else:
            stats[0] += 1
    else:
        if c_negation:
            stats[0] += 1
        else:
            stats[1] += 1

    return stats


def check_for_command(ssh_session, command, command2=None):
    if command2 is None:
        command2 = command

    if command is None:
        return False
    else:
        return re.search(command, ssh_session.send_command("sh run | inc {0}".format(command2)))


def main():
    parser = ArgumentParser(description='Arguments for running oneLiner.py')
    parser.add_argument('-c', '--csv', required=True, action='store', help='Location of CSV file')
    parser.add_argument('-f', '--conf_file', required=False, action='store', help='Location of config file')
    parser.add_argument('-v', '--validate', required=False, action='store',
                        help='check for presence of command string before applying config')
    args = parser.parse_args()

    ssh_username = input("SSH username: ")
    ssh_password = getpass.getpass('SSH Password: ')

    stats = [0, 0]
    failures = []
    c_negation = False
    p_error = ""

    with open(args.csv, "r") as file:
        reader = csv.DictReader(file)
        for device_row in reader:
            try:
                ssh_session = netmiko.ConnectHandler(device_type='cisco_ios', ip=device_row['device_ip'],
                                                     username=ssh_username, password=ssh_password)

                if args.conf_file is not None:
                    if check_for_command(ssh_session, args.validate):
                        ssh_session.send_config_from_file(args.conf_file)
                    else:
                        failures.append("{0} -- {1}".format(device_row["device_ip"], "validate string not found"))

                    stats[0] += 1
                else:
                    c_commands = device_row['config_command']
                    if c_commands.startswith("no "):
                        c_negation = True
                    ssh_session.send_config_set([c_commands])

                    check_command_entered(ssh_session, c_commands, stats, c_negation)

                ssh_session.send_command("wr mem")
                ssh_session.disconnect()
                print("+", end="", flush=True)
            except (netmiko.ssh_exception.NetMikoTimeoutException,
                    netmiko.ssh_exception.NetMikoAuthenticationException,
                    paramiko.ssh_exception.SSHException) as s_error:
                p_error += str(s_error)+"\n"
                stats[1] += 1
                failures.append("{0} -- {1}".format(device_row["device_ip"], s_error))
                print("!", end="", flush=True)

    print(p_error)
    print("{0} devices parsed, success/ failure: {1}/{2}".format(stats[0]+stats[1], stats[0], stats[1]))
    if len(failures) > 0:
        print("\n".join(failures))


if __name__ == "__main__":
    main()
