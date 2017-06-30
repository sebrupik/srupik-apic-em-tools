#from config.cisco_apiconsole import CLIENT_ID, CLIENT_SECRET
#from openVulnQuery import query_client, advisory, authorization

#query_client = query_client.QueryClient(CLIENT_ID, CLIENT_SECRET)
#advisories = query_client.get_by_year(year = 2010, adv_format = "cvrf")
#advisories = query_client.get_by_ios_xe('3.16.1S')


some_text = "line1 \n line2 \n line3\n"
some_text = "Application \n --------------------------------------- \n PFM \n --------------------------------------- \n"


array = some_text.splitlines()[2:-1]
#array = []
for i in array :
    print(type(i))