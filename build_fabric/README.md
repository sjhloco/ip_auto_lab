# Deploy Leaf and Spine

This playbook will deploy a leaf and spine fabric and its related services in a declarative manner. You only have to define a few key values such as *naming convention*, *number of devices* and *addresses ranges*, the playbook will do the rest.
If you wish to have a more custom build the majority of the elements (unless specifically stated) in the variable files can be changed as none of the scripting or templating logic uses the actual contents to make decisions.

This deployment will only scale upto 4 spines, 4 borders and 10 leafs. By default the following ports are used for inter-switch links, ideally these ranges would not be changed but can be done so within *fabric.yml* (*fbc.adv.bse_intf*).

- SPINE-to-LEAF: Eth1/1 - 1/10
- SPINE-to-BORDER: Eth1/11 - 1/15
- LEAF-to-SPINE: Eth1/1 - 1/5
- BORDER-to-SPINE: Eth1/1 - 1/5
- VPC Peer-link: Eth1/127 - 128

==ADD A DIAGRAM==

## Dynamic Inventory

A custom inventory plugin is used to create the dynamic inventory and *host_vars* of all the interfaces and IP addresses needed for the fabric. By doing this in the inventory it abstracts the complexity from the *base* and *fabric* templates keeping them clean and simple which makes it easier to expand this playbook build templates for other brands.

```bash
ansible-inventory --playbook-dir=$(pwd) -i inv_from_vars_cfg.yml --host=DC1-N9K-SPINE01     Host attributes
ansible-inventory --playbook-dir=$(pwd) -i inv_from_vars_cfg.yml --graph          Groups and members
ansible-inventory --playbook-dir=$(pwd) -i inv_from_vars_cfg.yml --list           All devices and host_vars
ansible-playbook playbook.yml -i inv_from_vars_cfg.yml                            Run against a playbook
```

## Core variable Elements

These core elements are the minimum requirements to create the declarative fabric as are used for dynamic inventory creation as well by the majority of the Jinja2 templates. All variables are preceeded by *ans*, *bse* or *fbc* to make it easier to identify within the templates which variable file the variable came from.

**ansible.yml** *(ans)*\
*device_type:* Operating system of each device type (Spine, Leaf and Border)\
*creds_all:* Hostname, username and password

**base.yml** *(bse)*\
*device_name:* The naming format that the automatically generated node ID is added to (double decimal format 0x) and the group name created from. The only limitation on the name is that it must contain a hyphen and the characters after that hyphen must be either letters, digits or underscore as this is used as the group name.

- spine: 'xx-xx'
- border: 'xx-xx'
- leaf: 'xx-xx'

*addr:* Subnets from which device specific IP addresses are generated. The addresses assigned are based on the device role increment and the node number. These must have the mask in prefix format (/).

- *lp_net: 'x.x.x.x/32'*                 Core OSPF and BGP peerings. By default will use .11 to .59
- *mgmt_net: 'x.x.x.x/27'*          Needs to be at least /27 to cover the maximum spine (4), leaf (10) and border (4)
- *mlag_net: 'x.x.x.x/28'*             MLAG peer-link addresses. At least /28 to cover the maximum leaf (10) and border (4)
- *srv_ospf_net: 'x.x.x.x/28'*        Non-core OSPF process peerings between the borders (4 IPs per-OSPF process)

**fabric.yml** *(fbc)*\
*network_size:* How big the network is, so the number of each switch type. At a minimum must have 1 spine, 2 leafs. The border and leaf switches must be in increments of 2 as are in a MLAG pair.

- *num_spines: x*                       Can have a maximum of 4
- *num_borders: x*                     Can have a maximum of 4
- *num_leafs: x*                          Can have a maximum of 10

*address_incre:* Increment that is added to the subnet and device hostname number to generate the unique IP addresses. Different increments are used dependant on the device role to keep the addressing unique.

- *spine_ip: 11*.                       Spine mgmt IP and routing loopback addresses will be from .11 to .14
- *border_ip: 16*                     Border mgmt IP and routing loopback addresses will be from .16 to .19
- *leaf_ip: 21*                           Leaf mgmt IP and routing loopback addresses will be from .21 to .30
- *border_vtep_lp: 36*           Border VTEP loopback addresses will be from .36 to .39
- *leaf_vtep_lp: 41*                 Leaf VTEP loopback addresses will be from .41 to .50
- *border_mlag_lp: 56*         Pair of border shared loopback addresses (VIP) will be from .56 to .57
- *leaf_mlag_lp: 51*               Pair of leaf MLAG shared loopback addresses (VIP) will be from .51 to .55
- *border_bgw_lp: 58*            Pair of border  BGW shared anycast loopback addresses will be from .58 to .59
- *mlag_leaf_ip: 0*               Start IP for Leaf Peer Links, so LEAF1 is .0, LEAF2 is .1, LEAF3 is .2, etc
- *mlag_border_ip: 10*          Start IP for border  Peer Links, so BORDER1 is .10, BORDER2 is .11, etc

Before any tasks are run input data from the variable files is validated to ensure it is of the correct format and meets the rules of playbook (number of devices, addresisng format, etc). It doesnt validate every single variable in the var files, just the core things that will definately break the playbook functionality or fabric.

Validates the core fabric variables in the base and fabric files are of the correct
format to be able to run the playbook and build a fabric.
A pass or fail is returned to the Ansible Assert module, if it fails the full output is also
returned for the failure message. The following methods check:

## Directory Structure
By default the following directory structure is created within *~/device_configs*, this base location can be changed using *ans.dir_path*.

```bash
~/device_configs/
├── DC1-N9K-BORDER01
│   ├── config
│   │   ├── base.conf
│   │   ├── config.conf
│   │   └── fabric.cfg
│   └── validate
│       ├── napalm_desired_state.yml
│       └── nxos_desired_state.yml
├── diff
│   ├── DC1-N9K-BORDER01.txt
└── reports
    ├── DC1-N9K-BORDER01_fbc_compliance_report.json
```

## Installation and Prerequisites

It using a virtual env change the NAPLAM library and plugin locations in the *ansible.cfg* to match your environment.

```bash
library = /home/ste/virt/ansible_2.8.4/lib/python3.6/site-packages/napalm_ansible/modules
action_plugins = /home/ste/virt/ansible_2.8.4/lib/python3.6/site-packages/napalm_ansible/plugins/action
```

The following base configuration needs to be manually added on all the devices.\
Features *nxapi* and *scp-server* are required for Naplam *config_replace* so must be enabled beforehand.\
Image validation can take a while on vNXOS so it is also best to do so beforehand.

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

Optionally run *ssh_key_playbook.yml* to automatically add all the new devices SSH keys to the *~/.ssh/known_hosts* file on the ansible host. Before running add the device IPs to the *ssh_hosts* file and install *ssh-keygen*. 

```bash
sudo apt install ssh-keyscan
ansible-playbook ssh_keys/ssh_key_add.yml -i ssh_keys/ssh_hosts
```

## Running playbook

The playbook can be run with any number of the following tags. The device configuration is applied using NAPLAM with the change differences always saved to file (in */device_configs/diff*) and optionally printed to screen.\
Naplalm *commit_changes* is set to true meaning that Anisible *check-mode* is used for dry-runs.

**--pre_val**             Checks var_file contents are valid and conform to script rules (network_size, address format, etc)\
**--dir**                    Deletes and recreates the file struture to save configs, diffs and reports

**--bse**                 Generates the base configuration snippet and saves it to file\
**--fbc**                    Generates the fabric configuration snippet and saves it to file\
**--bse_fbc**          Generates the base and fabric config snippets and joins them together\

**--cfg**                  Apply the configuration to devices (diffs are saved to file)\
**--cfg_diff**          Apply the config and print the differences to screen (also still saved to file)\
**--rb**                    Reverses the changes by applying the rollback configuration\

**--val_temp**        Generates desired state validation files for *napalm_validate* and *custom_validate*\
**--nap_val**           Generates validation file and runs generic *napalm_validate* to check LLDP, BGP and ping\
**--cus_val**           Generates validation file and runs device type specific *custom_validate* to check OSPF, LAG and MLAG\
**--post_val**         Runs nap_val and cus_val

**--full**                  Runs everything except cfg_diff

If the playbook is run in check-mode the post_validation tasks will not be run.
```bash
ansible-playbook playbook.yml -i inv_from_vars_cfg.yml --tag "full, cfg_diff" -C
ansible-playbook playbook.yml -i inv_from_vars_cfg.yml --tag "full"
```

## Post Validation checks

Post Validation checks create a validation file from the configuration variables (desired state) and compare that against the  actual state. *Napalm_validate* can only perform a compliance on anything that has a getter, it is used to validate BGP, connections (LLDP) and rachability between loopback addresses. A *custom_validate* pluggin uses napalm_validate framework inputting its own desired_state and actual state_files on which a compliance report is generated. This validates OSPF, LAG and MLAG. The results of these two tasks are joined to create the one compliance report stored in */device_configs/reports*.

```bash
cat ~/device_configs/reports/DC1-N9K-SPINE01_fbc_compliance_report.json | python -m json.tool
```
The main *custom_validate* method is called as a filter pluggin by Ansible. In the pluggin it has other device specific methods to create the data model that is complaince checked, these are called by the *custom_validate* method. Therefore to expand this to other device types just need to add a new device specific method within the pluggin. 

## Notes and Improvements
Have disabled ping from the napalm valdiation as took too long, loopbacks with secondary IP address can take 3 mins to come up. If fabric wasnt up BGP and OSPF wouldnt be up, can check other loopbacks as part of services.
Not sure about rollback, all though says all worked odd switch didnt rollback (full config, not sure if would be same with smaller bits of config).

1. Add simple diagram
2. Add servicess config replace
3. Add services as seperate playbook that is merge

Nice to have
1. Create a seperate playbook to update Netbox with information used to build the fabric
1. Add fabric vPC (dont think possible) and multisite
2. Add templates for Arista
