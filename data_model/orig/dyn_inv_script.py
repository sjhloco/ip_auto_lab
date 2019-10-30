#!/usr/bin/env python

import yaml
from ipaddress import ip_network
import argparse
from pprint import pprint
import os

try:
    import json
except ImportError:
    import simplejson as json

# ============================ Instructions ==========================
# ./dyn_inv_script.py --help                               See all the argunments possible
# ./dyn_inv_script.py --list                               Print to screen all groups, members and vars
# ./dyn_inv_script.py --host DC1-N9K-BORDER02              Print to screen all host_vars for a specific host
# ansible all -i dyn_inv_script.py -m ping                 Ansible logs into all hosts from specified invetory grp and pings
# ansible-playbook my_playbook.yml -i ./dyn_inv_script.py	Run the playbook using the dynamic inventory


# ============================ Generates host details from data models ==========================
def gather_details():
    global spine, border, leaf, hosts_mgmt, hosts_lp, groups, spine_os, border_os, leaf_os   # Needed so these varaibles can be used in other functions

    # 2. Load the data models (as a nested dict) from Ansible variable files (yml)
    mydir = os.getcwd()     # Gets current directory
    with open(os.path.join(mydir, 'vars/') + 'defaults.yml', 'r') as x:
        defaults = yaml.load(x, Loader=yaml.FullLoader)
    with open(os.path.join(mydir, 'vars/') + 'base.yml', 'r') as y:
        base = yaml.load(y, Loader=yaml.FullLoader)
    with open(os.path.join(mydir, 'vars/') + 'fabric.yml', 'r') as z:
        fabric = yaml.load(z, Loader=yaml.FullLoader)

    device_name = defaults['device_name']
    address_incre = defaults['address_incre']
    device_type = defaults['device_type']
    addressing = base['addressing']
    network_size = fabric['network_size']

    spine, border, leaf, hosts_mgmt, hosts_lp = ([] for i in range(5))    # creates 5 new lists

    # 2a. Generate a lists of Spine switches from the data model
    num = 0
    while network_size['num_spines'] != 0:
        num += 1    # Increments by 1 for each device
        # Creates the name with the incremented in double-decimal format
        spine.append(device_name['spine_name'] + str("%02d" % num))
        # Creates the mgmt IP by adding the incr and device_ip incr to the network address
        hosts_mgmt.append(str(ip_network(addressing['mgmt_ip_subnet'], strict=False)[address_incre['spine_ip'] + num]))
        # Creates the loopback IP by adding the incr and device_ip_incr
        hosts_lp.append(str(ip_network(addressing['lp_ip_subnet'])[0] + address_incre['spine_ip'] + num))
        network_size['num_spines'] -= 1    # Reduces number of spines each iteration

    # 2b. Generate a lists of border switches from the data model
    num = 0
    while network_size['num_borders'] != 0:
        num += 1
        border.append(device_name['border_name'] + str("%02d" % num))
        hosts_mgmt.append(str(ip_network(addressing['mgmt_ip_subnet'], strict=False)[address_incre['border_ip'] + num]))
        hosts_lp.append(str(ip_network(addressing['lp_ip_subnet'])[0] + address_incre['border_ip'] + num))
        network_size['num_borders'] -= 1

    # 2c. Generate a lists of leaf switches from the data model
    num = 0
    while network_size['num_leafs'] != 0:
        num += 1
        leaf.append(device_name['leaf_name'] + str("%02d" % num))
        hosts_mgmt.append(str(ip_network(addressing['mgmt_ip_subnet'], strict=False)[address_incre['leaf_ip'] + num]))
        hosts_lp.append(str(ip_network(addressing['lp_ip_subnet'])[0] + address_incre['leaf_ip'] + num))
        network_size['num_leafs'] -= 1

    # Creates list of groups (from the device names) and the os variable to be used in next function
    groups = [device_name['spine_name'].split('-')[-1].lower(), device_name['border_name'].split('-')[-1].lower(),
              device_name['leaf_name'].split('-')[-1].lower()]
    spine_os = device_type['spine_os']
    border_os = device_type['border_os']
    leaf_os = device_type['leaf_os']


# ============================ Creates the group_var and host_var ==========================
# The format is: inventory = { "group": { "hosts": [], "vars": {} }, "_meta": {} } }

# 3. Create the groups and populate with the hosts
def group_info(groups, spine, border, leaf, hosts_mgmt, os):
    global inventory, hostnames
    hostnames = spine + border + leaf       # Joins all lists of hosts to be used by the all group
    inventory = {'all': { "hosts": hostnames, "vars": {}}}          # Create the 'all' group
    for gr in groups:
        if gr == 'spine':
            inventory.update({gr: {"hosts": spine, "vars": {'os': spine_os}}})
        elif gr == 'border':
            inventory.update({gr: {"hosts": border, "vars": {'os': border_os}}})
        elif gr == 'leaf':
            inventory.update({gr: {"hosts": leaf, "vars": {'os': leaf_os}}})

    # inventory.update({groups[0]: { "hosts": spine, "vars": {'os': 'nxos'}}})
    # inventory.update({groups[1]: { "hosts": border, "vars": {'os': 'nxos'}}})
    # inventory.update({groups[2]: { "hosts": leaf, "vars": {'os': 'nxos'}}})

# 4. Create the hosts and populate with the host_vars
def host_info(inventory, hostnames, hosts_mgmt):
    inventory['_meta'] = {'hostvars': {}}           # Adds a new key:value pair to dict
    for host, mgmt, lp in zip(hostnames, hosts_mgmt, hosts_lp):   # Uses zip to iterate therough 3 lists simultaneously
        # Adds a new key that is the host with the value being the host_var key:value pair
        inventory['_meta']['hostvars'][host] = {'ansible_host': mgmt, 'lp_addr': lp}

def empty_inventory():
    return {'_meta': {'hostvars': {}}}

# ============================ Runs the script ==========================
# 1. Takes input args and either prints group_var (list), prints host_var (host) or feeds inventory into Ansoble
def main():
    parser = argparse.ArgumentParser()      # Arguments it accepts
    parser.add_argument("--list", help="Ansible inventory of all of the groups", action="store_true"),
    parser.add_argument("--host", help="Ansible inventory of a particular host", action="store")
    cli_args = parser.parse_args()          # Variable that represents th eargse entered arg

    gather_details()            # 2. Generates group_var & host_var inputs from data models
    group_info(groups, spine, border, leaf, hosts_mgmt, os)     # 3. Generate group_var
    host_info(inventory, hostnames, hosts_mgmt)                  # 4. Generate host_var

    if cli_args.list:           # if list print group_vars
        pprint(inventory)
    elif cli_args.host:         # if host print that hosts host_var
        pprint(inventory['_meta']['hostvars'][cli_args.host])
    else:                       # if no input return group_var and host_var as a JSON
        return(json.dumps(inventory))

if __name__ == "__main__":
    main()
# gather_details()
