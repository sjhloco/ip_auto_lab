# Dynamic Inventory

Not sure which method will use yet so have tried all 3 types.

<br/> Option1: dyn_inv_script.py - A dynamic inventory script that is run with ansible cmd.
The following data-model elements are used to create the inventory

os = defaults['os']         Device type that will be used by NAPALM
base['mgmt_ip_subnet']      Network address device IP addresss are created from

ipfabric['num_spines']      Number of spine switches. Decremented in a loop to create device Bame and IP
defaults['spine_name']      Basis used to create the spines hostname
defaults['spine_ip']        A set value by which to increment the network address for these device types
Have the same 3 elements for border and leaf switches

The script can be run using any of these cmds
*./dyn_script.py --help*                                   See all the argunments possible
*./dyn_script.py --list*                                   Print to screen all groups, members and vars
*./dyn_script.py --host DC1-N9K-BORDER02*                  Print to screen all host_vars for a specific host
*ansible all -i dyn_script.py -m ping*                     Ansible logs into all hosts from specified invetory grp and pings
*ansible-playbook my_playbook.yml -i ./dyn_script.py*	    Run the playbook using the dynamic inventory

<br/> Option2: leaf_spine.py - An inventory plugin that uses the source config file leaf_spine_src_cfg.yml
The uses the same data-model elements are used except also has loopback subnet and they are stored as dictionaries:
Once again only spine has been shown for brevity

network_size:
  num_spines: 2

names:
  spine_name: DC1-N9K-SPINE

device_type:
  spine_os: nxos

addressing:
  mgmt_ip_subnet: '10.10.108.0/24'
  lp_ip_subnet: '192.168.100.0/32'

address_incre:
  spine_ip: 10

This is appraently the preferred method over scripts and it is slighlty easier as is already structured using Ansible class and methods.
Problem is either dupliacte dat or 2 places as not pulling from my Ansible variables. This would need ot be changed
Had to use ANSIBLE_INVENTORY_PLUGINS=$(pwd inventory_plugins)  as although stored in invetory_plugin dir in playbook dir, didnt work

ANSIBLE_INVENTORY_PLUGINS=$(pwd inventory_plugins) ansible-inventory -i leaf_spine_inventory.yml --graph			Just outputs all groups
ANSIBLE_INVENTORY_PLUGINS=$(pwd inventory_plugins) ansible-inventory -i leaf_spine_inventory.yml –list			Outputs all host_vars, groups and members
ANSIBLE_INVENTORY_PLUGINS=$(pwd inventory_plugins) ansible-inventory -i leaf_spine_inventory.yml –host DC1-N9K-SPINE01         	Outputs all host_vars for this specific host


