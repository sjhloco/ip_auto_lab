# Deploy Leaf and Spine
This playbook will deploy a leaf and spine fabric and its related services in a declarative manner. You only have to define a few key values such as *naming convention*, *number of devices* and *addresses ranges*, the playbook will do the rest. It is structured into the following 5 roles giving you the option to deploy part or all of the fabric using the playbook

- base: None fabric specific core configuration such as hostname, address ranges, users, acls, ntp, etc 
- fabric: Fabric specific elements such as fabric size, interfaces, OSPF, BGP and MLAG
- services: Services provided by the fabric split into three sub-roles:
    - tenant: VRFs, SVIs and VLANs on the fabric and their associated VNIs 
    - interface: Access ports connecting to compute or other non-fabric network devices
    - routing: BGP (address-families), OSPF (additional non-fabric process) and static routes

If you wish to have a more custom build the majority of the elements in the variable files (unless specifically stated) can be changed as none of the scripting or templating logic uses the actual contents to make decisions.

This deployment will only scale upto 4 spines, 4 borders and 10 leafs. By default the following ports are used for inter-switch links, these can be changed within *fabric.yml* (*fbc.adv.bse_intf*).

- SPINE-to-LEAF:                *Eth1/1 - 1/10*
- SPINE-to-BORDER:         *Eth1/11 - 1/14*
- LEAF-to-SPINE:                *Eth1/49 - 1/52*
- BORDER-to-SPINE:         *Eth1/49 - 1/52*
- MLAG Peer-link:               *Eth1/53 - 54*

![image](https://user-images.githubusercontent.com/33333983/83332342-9b246500-a292-11ea-9455-7cbe56e0d701.png)

This playbook is based on using the one module for all the connections. I have not tested how it will work with multiple modules, the role *intf_cleanup* will likely not work. This role ensures interface configuration is declarative by defaulting non-used interfaces, therefore could be excluded without breaking the playbook.

As Python is a lot more flexible than Ansible the dynamic inventory and custom filter plugins (within the roles) do the manipulating of the data in the variable files to create the data models that are used by the templates. This helps to abstract a lot of the complexity out of the jinja templates making it easier to create new templates for different vendors as you only have to deal with the device configuration rather than data manipulation.

## Dynamic Inventory

A custom inventory plugin is used to create the dynamic inventory and *host_vars* of all the interfaces and IP addresses needed for the fabric. By doing this in the inventory it abstracts the complexity from the *base* and *fabric* templates keeping them clean and simple which makes it easier to expand this playbook build templates for other brands.

```sh
ansible-inventory --playbook-dir=$(pwd) -i inv_from_vars_cfg.yml --host=DC1-N9K-SPINE01     Host attributes
ansible-inventory --playbook-dir=$(pwd) -i inv_from_vars_cfg.yml --graph                    Groups and members
ansible-inventory --playbook-dir=$(pwd) -i inv_from_vars_cfg.yml --list                     All devices and host_vars
ansible-playbook playbook.yml -i inv_from_vars_cfg.yml                                      Run against a playbook
```

With the exception of *intf_mlag* and *mlag_peer_ip* (not on spines) all of the following *host_vars* are created for every host. 
- ansible_host:                       *string*
- ansible_network_os:         *string*
- num_intf:                             *Number of the first and last interface on the switch*
- intf_fbc:                               *Dictionary with interface the keys and description the values*
- intf_lp:                                 *List of dictionaries with the keys name, ip and descr*
- intf_mlag:                           *Dictionary with interface the keys and description the values*
- mlag_peer_ip:                   *string in the format x.x.x.x*

An example of the host_vars for a leaf switch:
```json
{
    "ansible_host": "10.10.108.21",
    "ansible_network_os": "nxos",
    "intf_fbc": {
        "Ethernet1/1": "UPLINK > DC1-N9K-SPINE01 Eth1/1",
        "Ethernet1/2": "UPLINK > DC1-N9K-SPINE02 Eth1/1"
    },
    "intf_lp": [
        {
            "descr": "LP > Routing protocol RID and peerings",
            "ip": "192.168.100.21/32",
            "name": "loopback1"
        },
        {
            "descr": "LP > VTEP Tunnels (PIP) and MLAG (VIP)",
            "ip": "192.168.100.41/32",
            "mlag_lp_addr": "192.168.100.51/32",
            "name": "loopback2"
        }
    ],
    "intf_mlag": {
        "Ethernet1/11": "MLAG peer-link > DC1-N9K-LEAF02 Eth1/11",
        "Ethernet1/12": "MLAG peer-link > DC1-N9K-LEAF02 Eth1/12",
        "Port-channel1": "MLAG peer-link > DC1-N9K-LEAF02 Po1"
    },
    "mlag_peer_ip": "10.255.255.0/31",
    "num_intf": "1,128"
}
```

## Fabric Core Variable Elements

These core elements are the minimum requirements to create the declarative fabric. They are used for the dynamic inventory creation as well by the majority of the Jinja2 templates. All variables are preceeded by *ans*, *bse* or *fbc* to make it easier to identify within the playbook, roles and templates which variable file the variable came from.

##### ansible.yml *(ans)*
***device_type:*** Operating system of each device type (spine, leaf and border)\
***creds_all:*** hostname, username and password

##### base.yml *(bse)*
***device_name:*** The naming format that the automatically generated node ID is added to (double decimal format) and group name created from (in lowercase). The Ansible group name is created from characters after the last hyphen. The only limitation on the naming is that it must contain a hyphen and the characters after that hyphen must be either letters, digits or underscore. This is a limitaiton of Ansible as these are the only characters that Ansible accepts for group names.

| Key      | Value | Information                                                             |
|----------------|----------|-------------------------------------------------------------------------------|
| spine          | xx-xx    | Name of the spine switch. For example with DC1-N9K-SPINE01 the group would be *'spine'*   |
| border         | xx-xx    | Name of the border switch. Using DC1-N9K-BORDER01 the group would be *'border'*        |
| leaf           | xx-xx    | Name of the leaf switch. Using DC1-N9K-LEAF01 the group would be *'leaf'*          |

***addr:*** The subnets from which the device specific IP addresses are generated. The addresses assigned are based on the *device role increment* and the *node number*. These must have the mask in prefix format (/x).

| Key      | Value | Information                                                                    |
|----------------|-------|-------------------------------------------------------------------------------|
| lp_net | x.x.x.x/32 | *Core OSPF and BGP peerings. By default will use .11 to .59*
| mgmt_net | x.x.x.x/27 | *Management network. Needs to be at least /27 to cover the maximum spine (4), leaf (10) and border (4)*
| mlag_net | x.x.x.x/28 | *MLAG peer-link addresses. At least /28 to cover the maximum leaf (10) and border (4)*
| srv_ospf_net | x.x.x.x/28 | *Non-core OSPF process peerings between the borders (4 IPs per-OSPF process)*

##### fabric.yml *(fbc)*
***network_size:*** How big the network is, so the number of each switch type. At a minimum must have 1 spine and 2 leafs. The border and leaf switches must be in increments of 2 as are an MLAG pair.

| Key      | Value | Information                                                                   |
|----------------|----------|-------------------------------------------------------------------------------|
| num_spines | 2 | *Number of spine switches, can have a maximum of 4*
| num_borders | 2 | *Number of border switches, can have a maximum of 4*
| num_leafs | 4 | *Number of leaf switches, can have a maximum of 10*

***num_intf:*** Defines the total number of interfaces on the device type by specifying the first and last interface. This required to make interfaces declarative so that if you change an interface the old interface is reset to the default settings.

| Key      | Value | Information                                                                    |
|----------------|----------|-------------------------------------------------------------------------------|
| spine | 1,128 | *The first and last interface for a spine switch*
| border | 1,128 | *The first and last interface for a border switch*
| leaf | 1,128 | *The first and last interface for a leaf switch*

***address_incre:*** Increment that is added to the subnet and device hostname node ID to generate the unique IP addresses. Different increments are used dependant on the device role to keep the addressing unique.

| Key      | Value | Information                                                                    |
|----------------|-------|-------------------------------------------------------------------------------|
| spine_ip       | 11    | Spine mgmt IP and routing loopback addresses will be from .11 to .14          |
| border_ip      | 16    | Border mgmt IP and routing loopback addresses will be from .16 to .19         |
| leaf_ip        | 21    | Leaf mgmt IP and routing loopback addresses will be from .21 to .30           |
| border_vtep_lp | 36    | Border VTEP loopback addresses will be from .36 to .39                        |
| leaf_vtep_lp   | 41    | Leaf VTEP loopback addresses will be from .41 to .50                          |
| border_mlag_lp | 56    | Pair of border shared loopback addresses (VIP) will be from .56 to .57        |
| leaf_mlag_lp   | 51    | Pair of leaf MLAG shared loopback addresses (VIP) will be from .51 to .55     |
| border_bgw_lp  | 58    | Pair of border  BGW shared anycast loopback addresses will be from .58 to .59 |
| mlag_leaf_ip   | 0     | Start IP for Leaf Peer Links, so LEAF1 is .0, LEAF2 is .1, LEAF3 is .2, etc   |
| mlag_border_ip | 10    | Start IP for border  Peer Links, so BORDER1 is .10, BORDER2 is .11, etc       |

## Services - Tenant Variables

Tenants, SVIs, VLANs and VXLANs are entered based on the variables stored in the *services_tenant.yml* file. At a minimun the following values need to be defined per-tenant.

- tenant_name: string                   *Name of the VRF*
- l3_tenant: True or False             *Does it need SVIs or is routing done on a device external (i.e router)*
  - vlans:                                    *List of VLANs within this tenant*
    - num: integrar               
    - name: string               

Tenants (VRFs) will only be created on a border or leaf if a VLAN within that tenant is to be created on that device. Even if it is not a L3 tenant a VRF will still be created and a L3VNI/VLAN number reserved.\

Unless an IP address is assigned to a VLAN (*ip_addr*) it will only be Layer 2 VLAN. If the VLAN is L3 it will automatically be redistributed into BGP, this can be disabled (*ipv4_bgp_redist: False*) on a per-vlan basis.\
By default VLANs will only be created on the leaf switches (*create_on_leaf*). This can be changed on a per-vlan basis so that they are created only on borders (*create_on_border*) or are created on both leafs and borders.

To change these settings add any of the following extra dictionaries to the tenant. 
- tenant
  - vlans:
    - ip_addr: x.x.x.x/24                              *Adding an IP address makes it a L3 VLAN (default L2 only)*
    - ipv4_bgp_redist: True or False          *Whether the SVI is redistributed into IPv4 BGP addr-fam (default True)*
    - create_on_leaf: True or False             *Whether this VLAN is created on the leafs (default True)*
    - create_on_border: True or False       *Whether this VLAN is created on the borders (default False)*
    
If the tenant is a L3_tenant the route-map for redistribution is always created and attached to the BGP peer. By default *ipv4_bgp_redist* is set to True meaning that the route-map will be empty (*permit all*). The name of this route_map can be changed, although it does have a few restrictions on the naming format.
- ipv4_redist_rm_name:        *To change the redistribution route-map name, it MUST still include 'vrf' and 'as'*

### L2VNI and L3VNI numbers
The *services_tenant* variables are passed through a filter_plugin (*format_dm.py*) that creates a per device_role (border or leaf) data-model that includes the L2VNI and L3VNI numbers. These values are derived from base settings which are incremneted on a per-tenant basis.\
These starting values and increments can be changed in the advanced section of the *services_tenant.yml* variable file.

- bse_vni:
  - tnt_vlan: 3001              *Starting VLAN number for the transit L3VNI*
  - l3vni: 3001                   *Starting VNI number for the transit L3VNI*
  - l2vni: 10000                 *Starting L2VNI number, the VLAN number is added to this*
- vni_incre:
  - tnt_vlan: 1                    *Value by which to increase transit L3VNI VLAN number for each tenant*
  - l3vni: 1                         *Value by which to increase transit L3VNI VNI number for each tenant*
  - l2vni: 10000               *Value by which to increase the L2VNI range (range + vlan) for each tenant*

An example of a data model created by the *format_dm.py* custom filter plugin. These are created on a device_role basis, so for all leaf switches and for all border switches.
```bash
{
    "bgp_redist_tag": 3001,
    "l3_tnt": true,
    "l3vni": 3001,
    "tnt_name": "BLU",
    "tnt_redist": true,
    "tnt_vlan": 3001,
    "vlans": [
        {
            "create_on_border": false,
            "create_on_leaf": true,
            "ip_addr": "10.10.10.1/24",
            "ipv4_bgp_redist": true,
            "name": "data",
            "num": 10,
            "vni": 10010
        },
        {
            "ip_addr": "l3_vni",
            "ipv4_bgp_redist": false,
            "name": "BLU_L3VNI",
            "num": 3001,
            "vni": 3001
        }
    ]
}

{
    "bgp_redist_tag": 3004,
    "l3_tnt": false,
    "l3vni": 3004,
    "tnt_name": "RED",
    "tnt_redist": false,
    "tnt_vlan": 3004,
    "vlans": [
        {
            "create_on_border": true,
            "create_on_leaf": false,
            "ip_addr": null,
            "ipv4_bgp_redist": false,
            "name": "red-ctt1",
            "num": 90,
            "vni": 40090
        },
        {
            "ip_addr": "l3_vni",
            "ipv4_bgp_redist": false,
            "name": "RED_L3VNI",
            "num": 3004,
            "vni": 3004
        }
    ]
}
```

## Services - Interface Variables
Interfaces are configured based on the variables specified in the *services_interfaces.yml* file. They can be single or dual-homed with the interface and port-channel number either entered manually or dynamically chosen from a range. 

By default all interfaces are *dual-homed* with an LACP state of 'active'. The interface details only need to be defined for the odd numbered switch, configuration for both members for the MLAG pair is automatically generated.\
The VPC number can not be changed, it will always be the same as the port-channel number.\
If not defining any single or dual-homed interfaces, the relevant dictionary (*single_homed* or *dual_homed*) must be hashed out.

There are 5 types of interface that can be defined:
- **access:** A single VLAN Layer2 access port. STP is set to 'edge'
- **stp_trunk:** A L2 trunk going to a device that supports STP. STP is set to 'network' meaning the other device must support *Bridge Assurance*
- **stp_trunk_non_ba:** Same as stp_trunk except that STP is set to 'normal' to support devices that dont use BA
- **non_stp_trunk:** A L2 trunk port going to a device that doesnt support BPDU. STP set to 'edge' with *BPDU Guard* enabled
- **layer3:** A non-switchport L3 interface with an IP address. Must be single-homed as MLAG not supported for L3 interfaces

At a minimum the following settings need to be configured:

- single_homed: *or* dual-homed:           *Hash out if not used*
  - descr: string
  - type: specific_type                       *Either access, stp_trunk, stp_trunk_non_ba, non_stp_trunk or layer3*
  - ip_vlan: vlan or ip                          *Depends on the type, either ip/prefix (string), vlan (integrar) or multiple vlans separated by , (string)*
  - switch: string                                *Switch creating on. If dual-homed needs to be odd switch number from MLAG pair*
  - tenant: string                                *Layer3 interfaces only, is the VRF the interface will be in*

To statically assign the interface and/or port-channel number (default is dynamic) add either of these 2 extra dictionaries to the interface. The values used can overlap with the dynamic interface range however for simplicty it is probably advisable to use a separate range for the dynamic and static assignments. 
  - intf_num: integrar          *Only specify the number, name is got from the fbc.adv.bse_intf.intf_fmt variable*
  - po_num: integrar           *Only specify the number, name is got from the fbc.adv.bse_intf.ec_fmt variable*
  - po_mode: string           *Optionally set the Port-channel mode to on, passive or active*

Under the advanced (*tnt.adv*) section of the variable file set the reserved range of interfaces to use for dynamic assignment:
- adv:                            
  - single_homed:                      *Range used for single-homed interfaces*
    - first_intf: integrar
    - last_intf: integrar
  - dual_homed:                       *Range used for dual-homed interfaces*
    - first_intf: integrar
    - last_intf: integrar
    - first_po: integrar
    - last_po: integrar

From the values in the *services_interface.yml* file a new per-device data model is created by the *format_dm.py* custom filter plugin. An example of the data model is shown below:
```bash
{
    "descr": "L3 > DC1-SRV-MON01 nic1",
    "dual_homed": false,
    "intf_num": "Ethernet1/33",
    "ip_vlan": "10.10.10.20/30",
    "tenant": "BLU",
    "type": "layer3"
},
{
    "descr": "UPLINK > DC1-VIOS-MGMT01",
    "dual_homed": true,
    "intf_num": "Ethernet1/16",
    "ip_vlan": "10,20,24,30,40",
    "po_mode": "active",
    "po_num": 66,
    "stp": "network",
    "type": "stp_trunk"
},
{
    "descr": "UPLINK > DC1-VIOS-MGMT01",
    "intf_num": "Port-channel66",
    "ip_vlan": "10,20,24,30,40",
    "stp": "network",
    "type": "stp_trunk",
    "vpc_num": 66
}
```

## Interface Cleanup - Defaulting Interfaces
The interface cleanup role is required to make sure any interfaces not assigned by the fabric or the services (svc_intf) role have a default configuration. Without this if an interface was to be changed (for example a server moved to different interface) the old interface would not have its configuration put back to the default values.

This role goes through the interfaces assigned by the fabric and services_interface role producing a list of used interfaces which are then subtracted from the list of all the switches interfaces (*fbc.num_intf*). It has to be run after either of these roles as it needs to know what interfaces have been assigned, therefore uses tags to ensure it is run any time either of these roles are run.

## Input validation
Rather than validating configuration on devices it runs before any device configuration and validate the details entered in the variable files are correct. The idea of this pre-validation is to ensure the values in the variable files are in the correct format, have no typos and conform to the rules of the playbook. Catching these errors early allows the playbook to failfast before device connection and configuration.\
They are run as part of the playbook pre-tasks with the rules on what defines a pass or failure defined within the filter_plugin *input_validate.py*. The plugin does the actual validation with a result returned to the Anisble Asset module which decides if the playbook fails.

A full list of what variables are checked and the expected input can be found in the header notes of *input_validate.py*.

## Playbook Structure

The playbook is divided into 3 sections with roles used to do all the templating and validation.

- pre_tasks: Creates the file structure and runs the pre validation tasks
- task_roles: Roles are used to to create the templates and in some cases use pluggins to create new data models
  - base: From templates and base.yml creates the base configuration snippets (aaa,  logging, mgmt, ntp, etc)
  - fabric: From templates and fabric.yml creates the fabric configuration snippets (connections, OSPF, BGP)
  - services: Has per-service type tasks and templates for the services to run on top of the fabric 
    - svc_tnt: From templates and services_tenant.yml creates the tenant config snippets (VRF, SVI, VXLAN, VLAN)
    - svc_intf: From templates and services_interface.yml creates the interface config snippets (routed, access, trunk)
-intf_cleanup: Based on interfaces used in fabric and svc_intf defaults all other interfaces      
- task_config: Assembles the config snippets into the one file and applies as a config_replace
- post_tasks: A validate role creates and compares *desired_state* (built from variables) against *actual_state*    
  - validate: custom_validate uses naplam_validate feed with device output to validate things not covered by naplam
    - nap_val: For elements covered by naplam_getters creates desired_state and compares against actual_state 
    - cus_val: For elements not covered by naplam_getters creates desired_state and compares against actual_state 
    
## Directory Structure

The following directory structure is created within *~/device_configs* to hold the configuration snippets, validation desired_state files,  and compliance reports. The base location can be changed using *ans.dir_path*.

```bash
~/device_configs/
├── DC1-N9K-BORDER01
│   ├── config
│   │   ├── base.conf
│   │   ├── config.conf
│   │   ├── svc_tnt.conf
│   │   └── fabric.cfg
│   └── validate
│       ├── napalm_desired_state.yml
│       └── nxos_desired_state.yml
├── diff
│   ├── DC1-N9K-BORDER01.txt
└── reports
    ├── DC1-N9K-BORDER01_compliance_report.json
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
Changing the *hardware access-list tcam region* requires a reboot to take effect

```bash
interface mgmt0
  ip address 10.10.108.11/24
vrf context management
  ip route 0.0.0.0/0 10.10.108.1
feature nxapi
feature scp-server
boot nxos bootflash:/nxos.9.2.4.bin
hardware access-list tcam region racl 512
hardware access-list tcam region arp-ether 256 double-wide
```

Optionally run *ssh_key_playbook.yml* to automatically add all the new devices SSH keys to the *~/.ssh/known_hosts* file on the ansible host. Before running add the device IPs to the *ssh_hosts* file and install *ssh-keygen*. 

```bash
sudo apt install ssh-keyscan
ansible-playbook ssh_keys/ssh_key_add.yml -i ssh_keys/ssh_hosts
```

## Running playbook

The playbook can be run with any number of the following tags. The device configuration is applied using NAPLAM with the change differences always saved to file (in */device_configs/diff*) and optionally printed to screen.\
Naplalm *commit_changes* is set to true meaning that Anisible *check-mode* is used for dry-runs.

As the playbook has got bigger I found it confusing when run in one go so maybe easier if done so in stages:

1. Pre-checks: Ensure that all the values in the variable conform to the playbook rules and standards. No point running the playbook if the variables are going to make it fail.
    - `ansible-playbook playbook.yml -i inv_from_vars_cfg.yml --tag pre_val`
2. Generate the configuration: Creates the config snippets and compares against what is on the device to see what will be change. *bse_fbc_svc* does the whole configuration but use any combination of the snippets (*bse*, *fbc*, *bse_fbc*, *tnt*, *intf*, *svc*)
    - `ansible-playbook playbook.yml -i inv_from_vars_cfg.yml --tag "dir, bse_fbc_svc, cfg_diff" -C`
 
3. Apply the configuration: Replaces current config on the device. The output is by default automatically saved to file (*/device_configs/diff*) so no real need to print to screen again.
    - `ansible-playbook playbook.yml -i inv_from_vars_cfg.yml --tag cfg`

4. Post-checks: Uses napalm-validate and custom-validate to ensure that the actual-state (from device) matches the expected state (got from variables files)
    - `ansible-playbook playbook.yml -i inv_from_vars_cfg.yml --tag post_val`
 
| tag             | Description                                                                                         |
|-----------------|-----------------------------------------------------------------------------------------------------|
| pre_val         | Checks var_file contents are valid and conform to script rules (network_size, address format, etc)  |
| dir             | Deletes and re-creates the file struture to save configs, diffs and reports                         |
| bse             | Generates the base configuration snippet                                                            |
| fbc             | Generates the fabric configuration snippet                                                          |
| tnt             | Generates the fabric configuration snippet                                                          |
| intf            | Generates the interface config snippet                                                              |
| cln             | Generates the configuration snippet to reset all the none used interfaces to the defaults           |
| bse_fbc         | Generates and joins the base, fabric and inft cleanup configuration snippet                         |
| bse_fbc_svc     | Generates and joins the base, fabric, all services and inft cleanup configuration snippet           |
| cfg             | Applies the configuration to the devices (diffs are saved to file)                                  |
| cfg_diff        | Applies the configuration and prints the differences to screen (is still also saved to file)        |
| rb              | Reverses the changes by applying the rollback configuration                                         |
| rb_diff         | Reverses the changes by applying the rollback configuration and prints the diffs to screen          |
| nap_val_fbc_bse | Runs napalm-validation against the *desired state* from the base and fabric variable files          |
| nap_val_tnt     | Runs napalm-validation against the *desired state* from the services_tenant variable file           |
| nap_val_svc     | Runs napalm-validation against the *desired state* from all the services variable files             |  
| nap_val         | Runs napalm-validation against the *desired state* from all variable files                          | 
| cus_val_fbc_bse | Runs custom-validation against the *desired state* from the base and fabric variable files          |
| cus_val_tnt     | Runs custom-validation against the *desired state* from the services_tenant variable file           |
| cus_val_intf    | Runs custom-validation against the *desired state* from the services_interface variable file        |
| cus_val_svc     | Runs custom-validation against the *desired state* from all the services variable files             |  
| cus_val         | Runs custom-validation against the *desired state* from all variable files                          | 
| post_val        | Runs napalm and custom-validation against the *desired state* from all variable files               | 
| full            | Runs pre_val, bse_fbc_svc, cfg and post_val                                                         | 

## Post Validation checks

A validation file is built from the contents of the var files (*desired state*) and compared against the *actual state* of the device. *Napalm_validate* can only perform a compliance on anything that has a getter so for anything not covered by this the *custom_validate* plugin is used. The custom plugin uses the napalm_validate framework to create the same format of compliance report but uses an input file (generated from device output) rather than napalm_validate.

Both validation engines are within the same role with seperate template and task files. The templates generate the desired state which is a combination of the commmands to run and the expected returned values. As the same command can be used to validate multiple roles Jinja template inheritance (using *extend* and *block*) is used to keep the templating DRY and not test roles that have not been provisioned yet.

The results of the naplam_validate (*nap_val.yml*) and custom_validate (*cus_val.yml*) tasks are joined together to create the one compliance report stored in */device_configs/reports*.

```bash
cat ~/device_configs/reports/DC1-N9K-SPINE01_compliance_report.json | python -m json.tool
```

By default the post-check assert play has *quiet_mode* enabled as it can be very noisy even for a successfuly validation. If anything fails it is easier to go through the report rather than Ansible output to find out exactly what failed.

### napalm_validate
Napalms very nature is to abstract the vendor so along as the vendor is supported and the getter exists the template files are the same for all vendors. The following elements are checked by naplam_validate post validation.
- hostname: *Automatically created device names are correct*
- bgp_neighbors: *Overlay neighbors are all up and at least one prefix received*
- lldp_neighbors: *Device connections are correct*

Note: I did try ICMP but takes too long, the lines for this are hashed out

### custom_validate
*custom_validate* requires a per-OS type template file and per-OS type method within the *custom_validate.py* filter_plugin. The command output can be collected via Naplam or Ansible Network modules, ideally as JSON or you could use NTC templates or the genieparse collection to do this. Within *custom_validate.py* it matches based on the command and creates a new data model that matches the format of the desired state. Finally the *actual_state* and *desired_state* are fed into napalm_validate using its *compliance_report* method. The following elements are checked, the roles that use these checks are in brackets

- show ip ospf neighbors detail (fbc): *Underlay neighbors are all up*
- show port-channel summary (fbc, intf): *Port-channel state and members (strict) are up*
- show vpc (fbc, tnt, intf): *MLAG peer-link, keep-alive state, vpc status and active VLANs*
- show interfaces trunk	(fbc, tnt, intf): *Allowed vlans and stp forwarding vlans*
- show ip int brief include-secondary vrf all (fbc, tnt, intf): *L3 interfaces in fabric and tenants*
- show nve peers (tnt): *All VTEP tunnels are up*
- show nve vni (tnt): *All VNIs are up, have correct VNI number and VLAN mapping*
- show interface status	(intf): *State and port type*

To aid with creating new validations the custom_val_builder is a stripped down version of custom_validate to use to build new validations. The README has the process but can basically feed in either feed in static dictionary file or device output to aid in the creation of the method code and template snippet before testing and then movign to the main playbook.

## Building a new service

Process for building a new service:
1. vars.yml: Build the input variable file. It should be nested dictionary with the root being a short acronym as helps identify which files variables come from
2. format_dm.py: Add a method to this to create the per-device_role DM. Python is more flexibale that jinaj for formatting so helps to keep the template a lot cleaner.
3. tasks.yml: Create a new task that will hold 2 plays, one to generate the new DM and one to render the template
4. tmpl.j2: Create the template that has logic to decide flt_vars based on device_role. 
5. tasks_from: Under tasks of the main playbook import the role and the name of this new task.
6. input_validation.py: Add a new method that uses try/except asser statements to validate the input variables.
7. pre_tasks: Add a new Ansible assert module play that references the new input_val method
8. post_checks: use custom_val_builder to build validation tests and then add to 'roles/validate/filter_plugin/custom_validate.py' and 'roles/validate/templates/nxos/val_tmpl.j2'

## Notes and Improvements
Have disabled ping from the napalm validation as took too long, loopbacks with secondary IP address can take 3 mins to come up. If fabric wasnt up BGP and OSPF wouldnt be up, can check other loopbacks as part of services.
Not sure about rollback, all though says all worked odd switch didnt rollback (full config, not sure if would be same with smaller bits of config).

1. Add routing  services

Nice to have
1. Create a seperate playbook to update Netbox with information used to build the fabric
1. Add multi-site
2. Add templates for Arista

## Caveats
NXOS API can sometimes stop working if reboot a device or push config. Not sure if is just happens on virtual devices. In the CLI it will say it is runnign and listening but you cant connect on port 443 to the device. To fix disable and renable the feature nxapi
-Note about how when reboot a device NXAPI stops working (even though it shows as listneing). Disable/ renable the feature
