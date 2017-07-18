import re

#from config.cisco_apiconsole import CLIENT_ID, CLIENT_SECRET
#from openVulnQuery import query_client, advisory, authorization

#query_client = query_client.QueryClient(CLIENT_ID, CLIENT_SECRET)
#advisories = query_client.get_by_year(year = 2010, adv_format = "cvrf")
#advisories = query_client.get_by_ios_xe('3.16.1S')

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
