#!/usr/bin/env python3

import json
import time
from . import smalllogin


def check_tag_exists(sl, tag):
    output = {}
    response = sl.request("/api/v1/tag", {"get": {}})

    for tag_object in json.loads(response.text)['response']:
        if tag_object['tag'] == tag:
            res2 = sl.request("/api/v1/tag/association", {"get": {"tag": tag, "resourceType": "network-device"}})

            output['id'] = tag_object['id']
            output["devices"] = []
            for device in json.loads(res2.text)['response']:
                output["devices"].append(get_network_device_brief(sl, device["resourceId"]))
                print(device['resourceId'])

            return output

    return False


def get_network_device_brief(sl, resource_id):
    response = sl.request("/api/v1/network-device/", {"get-plain": resource_id})
    resj = json.loads(response.text)["response"]

    brief = {"id": resj["id"],
             "hostName": resj["hostname"].split(".")[0],
             "platformId": resj["platformId"].split(",")[0],
             "serialNumber": resj["serialNumber"].split(",")[0]}
    print(brief)
    return brief


#  Attempt to create a new project and return it's siteId if successful
def get_project_id(sl, sitename):
    res = sl.request("/api/v1/pnp-project",
                     {"post": [{"siteName": sitename}], "header": {"Content-Type": "application/json"}})
    print(res.text)

    # wait 10 seconds for the task to complete
    time.sleep(10)

    res = sl.request("/api/v1/task/", {"get-plain": json.loads(res.text)['response']['taskId']})
    # print(res.text)

    resj = json.loads(res.text)["response"]

    if (resj["isError"]) is True:
        print(resj["progress"])
        print(resj["failureReason"])
        # exit(1)
        return None
    else:
        return json.loads(resj["progress"])["siteId"]


def add_devices_to_project(sl, projectid, devices):
    for device in devices:
        res = sl.request("/api/v1/pnp-project/{0}/device".format(projectid),
                         {"post": [device],
                         "header": {"Content-Type": "application/json"}})
        print(res.text)


def main():
    tag = None
    sl = smalllogin.login()

    tag_prompt = 'Tag[{}]: '.format(tag) if tag else 'Tag: '
    if not tag:
        tag = input(tag_prompt) or tag

    tag_dict = (check_tag_exists(sl, tag))
    if tag_dict is not False:
        print("The tag {0} ({1}) has {2} associations.".format(tag, tag_dict['id'], len(tag_dict["devices"])))
    else:
        print("Tag not found, exiting")
        exit(1)

    project_id = get_project_id(sl, "blah4")
    if project_id is not None:
        print("The new projectId is: {0}".format(project_id))
        add_devices_to_project(sl, project_id, tag_dict["devices"])


if __name__ == "__main__":
    main()
