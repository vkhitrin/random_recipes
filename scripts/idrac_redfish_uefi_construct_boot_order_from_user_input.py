#!/usr/bin/env python3

import argparse
import json
import os
import requests # library: requests
import sys
import re
import urllib3
import yaml  # library: pyyaml

from requests.adapters import HTTPAdapter, Retry
from yaml.loader import SafeLoader

# Constants that as far as I know are consistent with all iDRAC Redfish systems
REDFISH_ENDPOINT = 'redfish/v1'
REDFISH_SYSTEM_ID = 'System.Embedded.1'
REGEX_BOOT_SOURCE_ID = re.compile(r'.*(Boot[\d\w]{4})')


def parse_args():
    """
    Parse arguments provided to argparse from CLI

    :return : dictionary of parsed arguments
    """
    parser = argparse.ArgumentParser(description="Polarion test run results "
                                                 "to HTML report")
    parser.add_argument('-c', '--config', required=True,
                        help="path to YAML config file")
    parser.add_argument('-u', '--username', required=True,
                        help="iDRAC username")
    parser.add_argument('-p', '--password', required=True,
                        help="iDRAC password")
    return parser.parse_args()


def parse_config(conf):
    """
    Parse provided YAML configuration file

    Example of YAML config:
    # List of iDRAC hosts
    idrac_hosts:
      - host01.acme.com
      - host02.acme.com
    # List of boot devices' displayname.
    # Boot order will be generated based on the order of this list.
    # If device is not present in host, it will be omitted from generated list
    boot_devices_displayname_regex:
      - 'PXE Device 3: Integrated NIC 1 Port 3 Partition 1'
      - 'PXE Device \d: Integrated NIC 1 Port 2 Partition 1'
      - 'PXE Device .*: Integrated NIC 1 Port 1 Partition 1'
      - '.* Optical Drive .*'

    :param conf: Path to configuration file

    :return config: Dictionary of loaded configuration
    """
    if not os.path.exists(conf):
        print(f"Config file '{conf} does not exist")
        sys.exit(1)
    try:
        with open(conf) as f:
            config = yaml.load(f, Loader=SafeLoader)
    except yaml.YAMLError:
        print('Failed to parse YAML file, exiting')
        raise
    print(f"Config '{conf}' was loaded successfully")
    return config


def authenticate_with_idrac(idrac_url, user, passwd, sub_url=''):
    response = None
    url = f"{idrac_url}/{REDFISH_ENDPOINT}/Systems/{REDFISH_SYSTEM_ID}/{sub_url}"
    try:
        sess = requests.Session()
        # Add a retry machanisem for temporary 500 from Redfish API
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[500])
        sess.mount('http://', HTTPAdapter(max_retries=retries))
        req = sess.get(
               url,
               auth=(user, passwd),
               verify=False)
        response = req.json()
    except Exception:
        raise

    return response


def main():
    # Supress SSL insecure warning
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    args = parse_args()
    username = args.username
    password = args.password
    config = parse_config(args.config)
    try:
        idrac_hosts = config['idrac_hosts']
        boot_devices = config['boot_devices_displayname_regex']
    except KeyError as e:
        print(f"Key {e} is required and not present in config")
        sys.exit(1)
    results = dict()
    for host in idrac_hosts:
        boot_sources = list()
        boot_order = list()
        results[host] = dict()
        # Check connection
        print("="*len(host))
        print(host)
        print("="*len(host))
        system_details = authenticate_with_idrac(idrac_url=host,
                                                 user=username,
                                                 passwd=password)
        boot_mode = system_details['Boot']['BootSourceOverrideMode']
        if boot_mode != "UEFI":
            print('Host boot mode is not set to UEFI, skipping')
            results.pop(host)
            continue
        system_boot_sources = authenticate_with_idrac(idrac_url=host,
                                                      sub_url='BootOptions',
                                                      user=username,
                                                      passwd=password)
        try:
            for source in system_boot_sources['Members']:
                boot_source_string = source['@odata.id']
                boot_source = re.sub(REGEX_BOOT_SOURCE_ID, r'\1', boot_source_string)
                boot_sources.append(boot_source)
            # Not efficient but working
            for device in boot_devices:
                device_regex = re.compile(device)
                for boot in boot_sources:
                    try:
                        boot_source_info = \
                                authenticate_with_idrac(idrac_url=host,
                                                        sub_url=f"BootOptions/{boot}",
                                                        user=username,
                                                        passwd=password)
                        if re.search(device_regex, boot_source_info['DisplayName']):
                            print(boot_source_info)
                            boot_order.append(boot)
                    except ValueError:
                        continue
        except KeyError:
            print('Failed to parse boot sources, missing \'Members\' key. JSON:')
            print(system_boot_sources)

        results[host]['boot_order'] = boot_order
    output = yaml.dump(results, explicit_start=False,
                       default_flow_style=False)
    print(output)


if __name__ == '__main__':
    main()
