#!/usr/bin/env python3
import getpass
from requests import Request, Session
import requests
import urllib.parse as ul
import urllib3
import json

TOKEN_URL_ASA = "https://{0}/api/tokenservices"
TOKEN_URL_APICEM = "https://{0}/api/v1/ticket"


class SmallLogin(object):
    def __init__(self, host, username, password, platform, debug):
        self.host = host
        self.username = username
        self.password = password
        self.platform = platform

        self.serviceTicket = None
        self.fqdn_prefix = "https://{0}".format(host)
        self.DEBUG = debug

        if platform == "ASA":
            self.serviceTicket = self.get_ticket_asa2(host, username, password)
        elif platform == "APIC-EM":
            self.serviceTicket = self.get_ticket_apicem(host, username, password)

        if self.serviceTicket is None:
            print("Unable to obtain service ticket. exiting")
            exit(1)

        print("Service ticket for {0} is : {1}".format(platform, self.serviceTicket))

    @staticmethod
    def get_basicauth_header(host, username, password):
        """
        Get request to create the base64 string for the basicauth header and return the tuple
        :param host:
        :param username:
        :param password:
        :return:
        """
        tempr = requests.Request("POST", "http://" + host, auth=requests.auth.HTTPBasicAuth(username, password))
        pr = tempr.prepare()

        return pr.headers['Authorization']

    def get_ticket_asa2(self, host, username, password):
        """
        The ASA returns the serviceticket in headers of the response
        Return the header value of X-Auth-Token
        :param host:
        :param username:
        :param password:
        :return:
        """
        url = TOKEN_URL_ASA.format(host)

        params = dict()
        params['post'] = {}
        params['header'] = {"Content-Type": "application/json",
                            "Authorization": self.get_basicauth_header(host, username, password)}

        response = self.request_url2(url, params)

        if response is not None:
            return response.headers['X-Auth-Token']

        return None

    def get_ticket_apicem(self, host, username, password):
        """
        APIC-EM returns the service ticket in the body of the response
        Return the body value of serviceTicket
        :param host:
        :param username:
        :param password:
        :return:
        """
        url = TOKEN_URL_APICEM.format(host)

        params = dict()
        params['post'] = {"username": username, "password": password}
        params['header'] = {"Content-Type": "application/json"}

        response = self.request_url2(url, False, params)

        if response is not None:
            # print(type(response.text))
            j = json.loads(response.text)
            return j['response']['serviceTicket']

        return None

    def request(self, path, params=None, get_response=True):
        if params is None:
            params = dict()
        res = None

        if self.platform == "ASA" or self.platform == "APIC-EM":
            if "header" not in params:
                params['header'] = {"X-Auth-Token": self.serviceTicket}
            else:
                params['header'].update({"X-Auth-Token": self.serviceTicket})

            url = self.fqdn_prefix+"{0}".format(path)
            res = self.request_url2(url, get_response, params)

        return res

    def request_url2(self, url, get_response, params=None):
        """
        Create a Request instance which we can interrogate before we send it to the server
        To cut down on the amount of "json.loads(res.text)['response']" boilerplate code for parsing
        returned Requests Response objects, by default we will parse and return the value in this
        method.
        """
        if params is None:
            params = dict()
        requests.packages.urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        # req = None

        if "post" in params:
            req = requests.Request("POST", url, data=json.dumps(params['post']), headers=params['header'])
            print(req)
        elif "delete-plain" in params:
            req = requests.Request("DELETE", url+"/{0}".format(params["delete-plain"]), headers=params['header'])
        elif "delete" in params:
            req = requests.Request("DELETE", url, data=json.dumps(params['delete']), headers=params['header'])
        elif "get-plain" in params:
            req = requests.Request("GET", url+"/{0}".format(params["get-plain"]), headers=params['header'])
        elif "get" in params:
            url += "?"+ul.urlencode(params['get'])
            req = requests.Request("GET", url, headers=params['header'])
        else:
            print("Expected REST verb was missing, returning None")
            return None

        if get_response is True:
            return json.loads(self.send_request(req).text)["response"]

        return self.send_request(req)

    def send_request(self, request):
        s = Session()
        pr = request.prepare()

        res = s.send(pr, verify=False)

        if self.DEBUG:
            if res.ok is not True:
                print("***** Something bad happened ****")
                print("We sent this: ")
                print("URL : {0}".format(res.url))
                for h in pr.headers:
                    print(" {0} : {1}".format(h, pr.headers[h]))
                print("Body : {0}".format(str(pr.body)))

                print("..and received this: ")
                print("Response status-code: {0}".format(res.status_code))
                print(res.headers)
                print(res.text)
                return None
            else:
                print("res is : {0}".format(res))

        return res


def login(ipaddress=None, username=None, password=None, platform=None, debug=None):
    sl = None

    while not sl:
        ipaddress_prompt = 'Host Address[{}]: '.format(ipaddress) if ipaddress else 'Host Address: '
        username_prompt = 'Username[{}]: '.format(username) if username else 'Username: '
        platform_prompt = 'Platform[{}]: '.format(platform) if platform else 'Platform: '

        if not ipaddress:
            ipaddress = input(ipaddress_prompt) or ipaddress
        if not username:
            username = input(username_prompt) or username
        if not password:
            password = getpass.getpass('Password: ') or password
        if not platform:
            platform = input(platform_prompt) or platform

        try:
            sl = SmallLogin(ipaddress, username, password, platform, debug)
            return sl
        except requests.exceptions.HTTPError as exc_info:
            if exc_info.response.status_code == 401:
                print('Authentication Failed. Please provide valid username/password.')
                continue
            else:
                print('HTTP Status Code {code}. Reason: {reason}'.format(
                    code=exc_info.response.status_code,
                    reason=exc_info.response.reason))
                exit(1)
