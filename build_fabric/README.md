# Deploy Leaf and Spine

This playbook will deploy a leaf and spine fabric and its related services in a declarative manner. You only have to define a few key values such as *naming convention*, *number of devices* and *addresses ranges*, the playbook will do the rest.
If you wish to have a more custom build the majority of the elements (unless specifically stated) in the variable files can be changed as none of the scripting or templating logic uses the actual contents to make decisions.

This deployment will only scale upto 4 spines, 4 borders and 10 leafs. At a minimum must have 1 spine, 2 leafs, with the leafs and broders needing to even numbers. By default the following ports are used for inter-switch links, ideally these ranges would not be changed but can be done so within *fabric.yml* (*fbc.adv.bse_intf*).

- SPINE-to-LEAF: Eth1/1 - 1/10
- SPINE-to-BORDER: Eth1/11 - 1/15
- LEAF-to-SPINE: Eth1/1 - 1/5
- BORDER-to-SPINE: Eth1/1 - 1/5
- VPC Peer-link: Eth1/127 - 128

## Dynamic Inventory

A custom inventory plugin is used to create the dynamic inventory and *host_vars* of all the interfaces and IP addresses needed for the fabric. By doing this in the inventory it abstracts the complexity from the *base* and *fabric* templates keeping them clean and simple which makes it easier to expand this playbook build templates for other brands.

When not running the inventory pluggin against a playbook you have to use *ANSIBLE_INVENTORY_PLUGINS=$(pwd inventory_plugins)* or you could probably set as env var or in config file.

```bash
ansible-inventory --playbook-dir=$(pwd) -i inv_from_vars_cfg.yml --host=DC1-N9K-SPINE01     Hosts attributes
ansible-inventory --playbook-dir=$(pwd) -i inv_from_vars_cfg.yml --graph          Groups and members

ansible-inventory --playbook-dir=$(pwd) -i inv_from_vars_cfg.yml --list           All devices and host_vars

ansible-playbook playbook.yml -i inv_from_vars_cfg.yml                            Run against a playbook
```

## Core variable Elements

These core elements are the minimun requirements to create the declarative fabric. They are used for dynamic inventory creation as well as in some part by the majority of the Jinja2 templates. All variables are preceeded by *ans*, *bse* or *fbc* to make it easy to identify within the templates which variable file they came from.

**ansible.yml**\
*device_type:* Operating system of each device type (Spine, Leaf and Border)

**base.yml**\
*device_name:* The naming format that the automatically generated node number is added to in double decimal format (0x). The start of the name can be changed, but the last hyphen and name after it (SPINE, BORDER or LEAF) must not be changed the as that is what is used in the scripting logic to generate the Ansible groups.

- spine_name: 'xx-SPINE'
- border_name: 'xx-BORDER'
- leaf_name: 'xx-LEAF'

*addr:* Subnets from which device specific IP addresses are generated. The addresses assigned are based on the device role increment and the node number. These must have the mask in prefix format (/).

- *lp_net: 'x.x.x.x/32'*           Core OSPF and BGP peerings. By default will use .10 to .37
- *mgmt_net: 'x.x.x.x/27'*         Needs to be at least /27 to cover the maximum spine (4), leaf (10) and border (4)
- *mlag_net: 'x.x.x.x/28'*         MLAG peer-link addresses. At least /28 to cover the maximum leaf (10) and border (4)
- *srv_ospf_net: 'x.x.x.x/28'*     Non-core OSPF process peerings between the borders (4 IPs per-OSPF process)

**fabric.yml**«
*network_size:* How big the network is, so the number of each switch type. The border and leaf switches must be in increments of 2 as are in a MLAG pair.

- *num_spines: x*                     Can have a maximum of 4
- *num_borders: x*                    Can have a maximum of 4
- *num_leafs: x*                      Can have a maximum of 10

*address_incre:* The increment that is added to the subnet and device hostname number to generate the unique IP addresses. Different increments are used dependant on the device role to keep the addresses unique.

- *spine_ip: 11*. &emsp;&emsp;&emsp;  Spine mgmt IP and routing loopback addresses will be from .11 to .14
- *border_ip: 16* &emsp;&emsp;&emsp;  Border mgmt IP and routing loopback addresses will be from .16 to .19
- *leaf_ip: 21* &emsp;&emsp;&emsp;  Leaf mgmt IP and routing loopback addresses will be from .21 to .30
- *border_vtep_lp: 36* &emsp;&emsp;&emsp;  Border VTEP loopback addresses will be from .36 to .39
- *eaf_vtep_lp: 41* &emsp;&emsp;&emsp;  Leaf VTEP loopback addresses will be from .41 to .50
- *border_mlag_lp: 56* &emsp;&emsp;&emsp;  Pair of border shared loopback addresses (VIP) will be from .56 to .57
- *leaf_mlag_lp: 51* &emsp;&emsp;&emsp;  Pair of leaf MLAG shared loopback addresses (VIP) will be from .51 to .55
- *border_bgw_lp: 58* &emsp;&emsp;&emsp;  Pair of border  BGW shared anycast loopback addresses will be from .58 to .59
- *mlag_leaf_ip: 1* &emsp;&emsp;&emsp;  Start IP for Leaf Peer Links, so LEAF1 is .1, LEAF2 .2, LEAF3 .3, etc
- *mlag_border_ip: 11* &emsp;&emsp;&emsp;  Start IP for border  Peer Links, so BORDER1 is .11, BORDER2 .12, etc

## Installation and Prerequisites

It you are using a virtual environment change the NAPLAM library and plugin locations in the *ansible.cfg* to match your environment

```bash
library = /home/ste/virt/ansible_2.8.4/lib/python3.6/site-packages/napalm_ansible/modules
action_plugins = /home/ste/virt/ansible_2.8.4/lib/python3.6/site-packages/napalm_ansible/plugins/action
```

The following base configuration needs to be manually added on all the devices.\
Features *nxapi* and *scp-server* are required for NAPALM config_replace and nxapi vrf would break the NAPALM session so is done beforehand.
Image validation can take overa while on vNXOS so is best to do beforehand.

```bash
interface mgmt0
  ip address 10.10.108.11/24
vrf context management
  ip route 0.0.0.0/0 10.10.108.1
feature nxapi
nxapi use-vrf management
feature scp-server
boot nxos bootflash:/nxos.9.2.4.bin
```

Can optionally run the *ssh_key_playbook.yml* script to automatically add all the new devices SSH keys to the *~/.ssh/known_hosts* file on the ansible host. You first need to install ssh-keygen and added the device IPs to the *ssh_hosts* file.

```bash
sudo apt install ssh-keyscan
ansible-playbook ssh_keys/ssh_key_add.yml -i ssh_keys/ssh_hosts
```

## Running playbook

When the playbook runs it creates the *device_configs* folder in your home directory and wihin here a directory for each device that stores the *base.cfg* and *fabric.cfg* which are then joined together using *assemble*. A *device_configs/diff* folder is also created that stores the differences for each device in seperate device files in the format *device_name.cfg*.
NAPALM *commit_changes* is set to *True* so use Ansible *check_mode* to do a dry run.
Wihtin the diff folder the config differences for each device are stored in file wiht the devices name.
Commit changes is always set to true, usee Ansible check mode to deide whetehr do or not

```bash
ansible-playbook playbook.yml -i inv_from_vars_cfg.yml --tag "dir,base,fabric,config" -C
ansible-playbook playbook.yml -i inv_from_vars_cfg.yml --tag "dir,base,fabric,config" -C
```

## Caveats

The following caveats cameout of building templates for NXOS config_replace:\
*feature interface-vlan* &emsp;&emsp;&emsp;&emsp;&emsp;&emsp;    Need to make sure also have *interface vlan1* in your config file\
*logging source-interface loopback1* &emsp;&emsp;&emsp;  Order specifc so the loopback intefrace must be before it in the template

The following lines to need to be at the top of the config_replace template:\
*!Command: Checkpoint cmd vdc 1* &emsp;&emsp;&emsp;  The nexus wont recognise candidate_config.txt as a checkpoint file without it\
*version 9.2(4) Bios:version* &emsp;&emsp;&emsp;&emsp;&emsp;&emsp;  Without it does "no hostname" which causes a failure due to 'Syntax error while parsing 'vdc DC1-N9K-LEAF01 id 1'

If configuration application fails the following cmds are useful to tshoot on the NXOS device:\
*show account log* &emsp;&emsp;&emsp;&emsp;  See the cmds run by NAPALM\
*show rollback status* &emsp;&emsp;&emsp;  Check whether the install failed or not, sometimes NAPALM session can close or timeout but the config still be applied
*show rollback log exec* &emsp;&emsp;&emsp;  Show the cmds run, can workout from this what cmd caused it to fail

If the install fails the files will be left on the NXOS so you can manually attempt the change.\
*show diff rollback-patch file sot_file file canadiate* &emsp;&emsp;&emsp;&emsp;  Check the config difference on the device\
*rollback running-config file candidate_config.txt verbose* &emsp;&emsp;&emsp;  Manually do the config_replace, verbose shows \cmds entered
*rollback running-config file rollback_config.txt* &emsp;&emsp;&emsp;  To rollback the config changes

## Notes and Improvements

Tested on lab of 6 devices running code 9.2(4)

1. Improvemtns to current version\
Fix MLAG interfaces, either make /30 or change ips as are 1 out (i.e 0 and 1 rather than 1 and 2)\
Add a flag to easily toggle on/off print diffs to screen\
Improve the tags\
Add a rolback play for NAPALM\
Add simple example Diagram for 2 sp, 2 bdr, 2 lf

2. Add validation checks\
-Validate input data is correct (addresses valid, follows naming formats, intergrars, etc), based on my compliance requirements\
-Output is expected, compared to what expect from the input file\
-Validate LLDP to check cabling correct, BGP peerings, what else???\

3. Update Netbox with information used to build the fabric

4. Redo services data models and add:\
Remove complexity from the templates, put into jinja2 filters isntead\
Have options to deploy as replace config or as merge config. Maybe sperate playbooks?\
Validation checks for services

5. Nice to have\
Add fabric vPC and multisite\
Add templates for Arista
