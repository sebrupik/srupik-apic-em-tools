import re

#from config.cisco_apiconsole import CLIENT_ID, CLIENT_SECRET
#from openVulnQuery import query_client, advisory, authorization

#query_client = query_client.QueryClient(CLIENT_ID, CLIENT_SECRET)
#advisories = query_client.get_by_year(year = 2010, adv_format = "cvrf")
#advisories = query_client.get_by_ios_xe('3.16.1S')

SH_VER_IOS = ""
SH_INV_REGEX = ".*?PID: (?P<type>.*?)\s*,"

device_version = """Cisco IOS Software, s2t54 Software (s2t54-ADVENTERPRISEK9-M), Version 15.1(2)SY11, RELEASE SOFTWARE (fc3)
Technical Support: http://www.cisco.com/techsupport
Copyright (c) 1986-2017 by Cisco Systems, Inc.
Compiled Fri 21-Jul-17 05:57 by prod_rel_team

ROM: System Bootstrap, Version 12.2(50r)SYS3, RELEASE SOFTWARE (fc1)

 BLAH-GW uptime is 19 weeks, 45 minutes
Uptime for this control processor is 18 weeks, 6 days, 23 hours, 37 minutes
System returned to ROM by Stateful Switchover
System restarted at 15:00:32 UTC Wed Nov 29 2017
System image file is "bootdisk:s2t54-adventerprisek9-mz.SPA.151-2.SY11.bin"
Last reload reason: power-on



This product contains cryptographic features and is subject to United
States and local country laws governing import, export, transfer and
use. Delivery of Cisco cryptographic products does not imply
third-party authority to import, export, distribute or use encryption.
Importers, exporters, distributors and users are responsible for
compliance with U.S. and local country laws. By using this product you
agree to comply with applicable laws and regulations. If you are unable
to comply with U.S. and local laws, return this product immediately.

A summary of U.S. laws governing Cisco cryptographic products may be found at:
http://www.cisco.com/wwl/export/crypto/tool/stqrg.html

If you require further assistance please contact us by sending email to
export@cisco.com.

cisco WS-C6509-E (M8572) processor (revision ) with 1785856K/262144K bytes of memory.
Processor board ID SMC1443004C
 CPU: MPC8572_E, Version: 2.2, (0x80E80022)
 CORE: E500, Version: 3.0, (0x80210030)
 CPU:1500MHz, CCB:600MHz, DDR:600MHz
 L1:    D-cache 32 kB enabled
        I-cache 32 kB enabled

Last reset from power-on
81 Virtual Ethernet interfaces
204 Gigabit Ethernet interfaces
72 Ten Gigabit Ethernet interfaces
2543K bytes of non-volatile configuration memory.

Configuration register is 0x2102"""

device_inv = """NAME: "Chassis 1 WS-C6509-E", DESCR: "Chassis 1 Cisco Systems, Inc. Catalyst 6500 9-slot Chassis System"
PID: WS-C6509-E        ,                     VID: V05, SN: SMCxxx

NAME: "Chassis 1 WS-C6K-VTT-E 1", DESCR: "Chassis 1 VTT-E FRU 1"
PID: WS-C6K-VTT-E      ,                     VID:    , SN: SMTxxx

NAME: "Chassis 1 WS-C6K-VTT-E 2", DESCR: "Chassis 1 VTT-E FRU 2"
PID: WS-C6K-VTT-E      ,                     VID:    , SN: SMTxxx

NAME: "Chassis 1 WS-C6K-VTT-E 3", DESCR: "Chassis 1 VTT-E FRU 3"
PID: WS-C6K-VTT-E      ,                     VID:    , SN: SMTxxx

NAME: "Chassis 1 CLK-7600 1", DESCR: "Chassis 1 OSR-7600 Clock FRU 1"
PID: CLK-7600          ,                     VID:    , SN: SMTxxx

NAME: "Chassis 1 CLK-7600 2", DESCR: "Chassis 1 OSR-7600 Clock FRU 2"
PID: CLK-7600          ,                     VID:    , SN: SMTxxx

NAME: "Chassis 1 1", DESCR: "Chassis 1 WS-X6848-GE-TX CEF720 48 port 10/100/1000mb Ethernet Rev. 1.4"
PID: WS-X6848-GE-TX    ,                     VID: V02, SN: SALxxx
"""


def cleanupIOSXE(input_str):
    str1 = re.sub(r"[0]", "", input_str)

    if len(str1.split(".")) > 3:
        index = str1.rfind(".")
        new_str = str1[:index] + str1[index + 1:]
    else:
        new_str = str1

    return new_str

some_text = "line1 \n line2 \n line3\n"
some_text = "Application \n --------------------------------------- \n PFM \n --------------------------------------- \n"


array = some_text.splitlines()[2:-1]
#array = []
for i in array :
    print(type(i))


print(cleanupIOSXE("03.03.06.SE"))
print(cleanupIOSXE("16.3.3"))


print("CISCO7206VXR".replace(" ", "").split(","))


def remove_negation(c_command):
    ar = c_command.split()
    if len(ar) > 2:
        return " ".join(ar[1:])
    return c_command

print(remove_negation("no router ospf 100"))

c_negation = True
swap_str = "{2}/{1}" if c_negation else "{1}/{2}"
print(("{0} devices parsed, success/ failure: "+swap_str).format(1 + 1, 2, 0))
#


device_version_first = device_version.splitlines()[0].split(", ")
print(device_version_first)
if device_version_first[0] == "Cisco IOS Software":
    print(device_version_first[2].split(" ")[1])
    dv_flat = " ".join(device_version.splitlines())
    print(dv_flat)

match = re.search(SH_INV_REGEX, device_inv)
if match:
    print(match.group("type"))
