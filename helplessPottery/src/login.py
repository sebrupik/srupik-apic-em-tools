'''
login helper module.
'''
#import requests.exceptions

from uniq.apis.nb.client_manager import NbClientManager
from config.apic_config import APIC, APIC_USER, APIC_PASSWORD
from getpass import getpass
#from getpass import getuser


def login(interactive_login):
    """ Login to APIC-EM northbound APIs in shell.
    Returns:
        Client (NbClientManager) which is already logged in.
    """

    if interactive_login :
        print("\nEnter APIC-EM hostname or IP")
        server = input("Server: ")
        print("\nEnter APIC-EM Username")
        username = input("Username: ")
        print("\nEnter APIC-EM password")
        password = getpass(prompt='Your password: ')
    else :
        server = APIC,
        username = APIC_USER,
        password = APIC_PASSWORD

    try:
        client = NbClientManager(server, username, password, connect=True)
        return client
    except requests.exceptions.HTTPError as exc_info:
        if exc_info.response.status_code == 401:
            print('Authentication Failed. Please provide valid username/password.')
        else:
            print('HTTP Status Code {code}. Reason: {reason}'.format(
                    code=exc_info.response.status_code,
                    reason=exc_info.response.reason))
        exit(1)
    except requests.exceptions.ConnectionError:
        print('Connection aborted. Please check if the host {host} is available.'.format(host=server))
        exit(1)