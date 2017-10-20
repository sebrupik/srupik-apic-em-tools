#!/usr/bin/env python3

import json
import time
from . import smalllogin


def get_response(response):
    return json.loads(response.text)["response"]


def get_task_progress(sl, task_id):
    res = sl.request("/api/v1/task/", {"get-plain": task_id})
    if res is not None:
        return get_response(res.text)["progress"]
    return None


def main():
    start_index = 1
    index_increment = 100
    task_ids = []

    sl = smalllogin.login()

    while True:
        response = sl.request("/api/v1/discovery/{0}/{1}".format(start_index, index_increment), {"get": {}})
        if len(get_response(response.text)) > 0:
            for discovery in get_response(response.text):
                if discovery["name"].find("Discovery_Settings_Id") != -1:
                    response2 = sl.request("/api/v1/discovery/{0}".format(discovery["id"]), {"delete": {}})

                    task_ids.append({"name": discovery["name"], "taskId": (get_response(response2.text))["taskId"]})

            start_index += index_increment
        else:
            break

    # Broken into two loops to allow the APIC-EM tasks to complete
    time.sleep(2)
    for task_id in task_ids:
        print("{0} : {1}".format(task_id["name"], get_task_progress(sl, task_id["taskId"])))


if __name__ == "__main__":
    main()
