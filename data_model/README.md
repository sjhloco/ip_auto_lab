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

ANSIBLE_INVENTORY_PLUGINS=$(pwd inventory_plugins) ansible-inventory -i inv_from_vars_cfg.yml --graph			Just outputs all groups
ANSIBLE_INVENTORY_PLUGINS=$(pwd inventory_plugins) ansible-inventory -i inv_from_vars_cfg.yml --list			Outputs all host_vars, groups and members
ANSIBLE_INVENTORY_PLUGINS=$(pwd inventory_plugins) ansible-inventory -i inv_from_vars_cfg.yml -host=DC1-N9K-SPINE01         	Outputs all host_vars for this specific host


!!!!! Notes
The only things to go in host VARs are things that are node specific.
Anything that is accross all does not get a host var
May have to create group_vars for some things, not sure about that

Sometimes when run playbook wiht full ammount it skips one, for exampel fails to make the directory so have to rerun - Guess is forks????
Still dont know how can create complete config out of it with my formatting as config has to be in order (i.e. all interfaces together)
Need to decide on where defaults go, do we just put in with same section are defaults for and sperate file???
How do you add services int he future, have a playbook that edits the variable fiels
Need to build in some type of IP checking
Need to integrate IPAM, either use that to assign IPs, or check agaisnt it and update when deploy the fabric

Ordering things by number, for example nve interface. NXOS autoamtically reorders s, need to make my config exact
Gets lengthy as have to keep splitting logic up to keep order corrrect (as did to lkeep NVE interface)

Hvae ended up with more duplicate date, like for exampel VRFs

Got oput of control, too many duplicate data
Need better naming for the variables to know what file there from
Need better naming to know if they came from python plugin filter
Probably need to put all var files though python to create the full data-model, will make the  jinja2 neater
-provides a layer of abstraction - keep jinja very simple, less nested for and if statements