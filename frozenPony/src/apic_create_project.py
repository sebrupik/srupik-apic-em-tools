#!/usr/bin/env python3
import json
import time
import requests
from pathlib import Path
#from . import smalllogin
import smalllogin

CONFIG_DIR = "/home/srupik/apic-configs"
CONFIG_FILE_FORMAT = "{0}-config"


def get_tagged_devices(sl, tag):
    output = {}
    response = sl.request("/api/v1/tag", {"get": {}})

    for tag_object in response:
        if tag_object['tag'] == tag:
            assoc_devices = sl.request("/api/v1/tag/association",
                                       {"get": {"tag": tag, "resourceType": "network-device"}})

            output['id'] = tag_object['id']
            output["devices"] = []
            for device in assoc_devices:
                output["devices"].append(get_network_device_brief(sl, device["resourceId"]))

            return output

    return False


def get_network_device_brief(sl, resource_id):
    """
    Build a per-device dictionary with relevantly named keys which can be later used in the
    'add_devices_to_project' method
    """
    response = sl.request("/api/v1/network-device/", {"get-plain": resource_id})
    # resj = json.loads(response.text)["response"]

    image_details = get_default_image(sl, response["platformId"].split(",")[0])

    brief = {"id": response["id"],
             "hostName": response["hostname"].split(".")[0],
             "platformId": response["platformId"].split(",")[0],
             "serialNumber": response["serialNumber"].split(",")[0],
             "configId": find_device_config_file(sl, response["hostname"].split(".")[0]),
             "imageId": image_details[0],
             "imageName": image_details[1],
             "pnp_id": get_pnp_device_id(sl, response["serialNumber"].split(",")[0])}
    print(brief)
    return brief


#  Attempt to create a new project and return it's siteId if successful
def get_project_id(sl, sitename):
    response = sl.request("/api/v1/pnp-project",
                          {"post": [{"siteName": sitename}], "header": {"Content-Type": "application/json"}})
    print(response)

    # wait 10 seconds for the task to complete
    time.sleep(10)

    response = get_task_response(sl, response['taskId'])

    if (response["isError"]) is True:
        print(response["progress"])
        print(response["failureReason"])
        return None
    else:
        return response["siteId"]


def add_devices_to_project(sl, projectid, devices):
    for device in devices:
        res = sl.request("/api/v1/pnp-project/{0}/device".format(projectid),
                         {"post": [device], "header": {"Content-Type": "application/json"}})
        # print(res.text)
        print(get_task_response(sl, res["taskId"]))


def find_device_config_file(sl, hostname):
    """
    Check to see if an applicably names config file exists, and load it into APIC-EM,
    Return this APIC-EM fileId
    """
    try:
        filepath_u = CONFIG_DIR+"/"+CONFIG_FILE_FORMAT.format(hostname).upper()
        filepath_l = CONFIG_DIR+"/"+CONFIG_FILE_FORMAT.format(hostname).lower()

        if Path(filepath_u).is_file():
            file = open(filepath_u, "r")
            print(file)
        elif Path(filepath_l).is_file():
            file = open(filepath_l, "r")
            print(file)
        else:
            return None
    except:
        print("Could not open file " + CONFIG_DIR+"/"+CONFIG_FILE_FORMAT.format(hostname))
        return None

    delete_existing_config_file(sl, CONFIG_FILE_FORMAT.format(hostname))

    req = requests.Request("POST",
                           sl.fqdn_prefix+"/api/v1/file/config",
                           headers={"X-Auth-Token": sl.serviceTicket},
                           files={"uploadFile": file})

    try:
        response = sl.send_request(req)
    except requests.exceptions.RequestException as rerror:
        print("Error sending request object: ", rerror)
        return None

    if response is not None:
        # resj = json.loads(response.text)["response"]
        # print("******************* "+json.dumps(response, indent=2))
        if "errorCode" in response:
            print("{0} :: {1}".format(response["message"], hostname))
            return None
        else:
            return response["id"]

    return None


def get_pnp_device_id(sl, serial_number):
    response = sl.request("/api/v1/pnp-device", {"get": {"serialNumber": serial_number}})

    # pnp_list = json.loads(res.text)["response"]
    # print("PNP list "+pnp_list)

    if len(response) > 0:
        return response[0]["id"]

    return None


def delete_existing_pnp_device(sl, device_list):
    for device in device_list["devices"]:
        if device["pnp_id"] is not None:
            print("DELETING PnP device: "+device["pnp_id"])
            res = sl.request("/api/v1/pnp-device", {"delete-plain": device["id"]})


def delete_existing_config_file(sl, filename):
    ar = [filename.lower(), filename.upper()]

    for f in ar:
        response = sl.request("/api/v1/pnp-file/config",
                              {"get": {"offset": "1", "limit": "1", "name": f},
                               "header": {"Content-Type": "application/json"}})

        if len(response) > 0:
            print("FOUND : "+f+" and len is :"+str(len(response)))
            deleted_res = delete_file_id(sl, response[0]["id"])
            if deleted_res["isError"] is True:
                print("{0} :: {1}".format(deleted_res["progress"], f))
            else:
                print(deleted_res["progress"])


def delete_file_id(sl, fileid):
    print("DELETING fileId: {0}".format(fileid))
    response = sl.request("/api/v1/pnp-file/config", {"delete-plain": fileid})

    print(json.dumps(response, indent=2))
    return get_task_response(sl, response["taskId"])


def get_task_response(sl, task_id):
    print("TASK ID is : {0}".format(task_id))
    res = sl.request("/api/v1/task/", {"get-plain": task_id})
    return res


def get_default_image(sl, platform_id):
    response = sl.request("/api/v1/pnp-file/image/default",
                          {"get": {"productId": platform_id}, "header": {"Content-Type": "application/json"}})

    # resj = json.loads(response.text)["response"]
    if len(response) > 0:
        return [response[0]["imageId"], response[0]["imageName"]]

    return [None, None]


def main():
    """
    Check Tag exists: collect device details
    Create project, if siteId does not already exist
    Add collected devices to project
      -- specify config
      -- specify image
    Profit.
    """
    tag = None
    sl = smalllogin.login()

    tag_prompt = 'Tag[{}]: '.format(tag) if tag else 'Tag: '
    if not tag:
        tag = input(tag_prompt) or tag

    device_list = (get_tagged_devices(sl, tag))
    if device_list is not False:
        print("The tag {0} ({1}) has {2} associations.".format(tag, device_list['id'], len(device_list["devices"])))

        s = set()
        for dic in device_list["devices"]:
            s.add("{0} :: {1}".format(dic["platformId"], dic["imageId"]))

        print("Unique device types and default image")
        for d in s:
            print(d)
    else:
        print("Tag not found, exiting")
        exit(1)

    delete_existing_pnp_device(sl, device_list)

    project_id = get_project_id(sl, "blah4")
    if project_id is not None:
        print("The new projectId is: {0}".format(project_id))
        add_devices_to_project(sl, project_id, device_list["devices"])


if __name__ == "__main__":
    main()
