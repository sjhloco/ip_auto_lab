# Data Models - Deploy Leaf and Spine

The idea behind these data models is to deploy a leaf and spine architecture and its related services in a declarative manner. A dynamic inventory is created using either an inventory plugin or inventory script based on the information within the data models. Unless specifically stated all the elements of the data model can be changed as none of the scripting or templating logic uses the actual contents to make decisions.

This deployment will only scale upto 4 spines, 4 borders and 10 leafs. By default the following ports are used for inter-switch links, ideally these ranges would not be changed but can be done so within *fabric.yml*.

- SPINE-to-LEAF: Eth1/1 - 1/10
- SPINE-to-BORDER: Eth1/11 - 1/15
- LEAF-to-SPINE: Eth1/1 - 1/5
- BORDER-to-SPINE: Eth1/1 - 1/5
- VPC Peer-link: Eth1/127 - 128

## Core Data Model Elements

These core elements are the minimun requirements to create the declarative fabric. They are used for dynamic inventory creation as well as in some part by the majority of the Jinja2 templates.

**ansible.yml**\
*device_type:* Operating system of each device type (Spine, Leaf and Border)

**base.yml**\
*device_name:* The naming format that the automatically generated node number is added to in double decimal format (0x). The start of the name can be changed, but the last hyphen and name after it (SPINE, BORDER or LEAF) must not be changed the as that is what is used to in the scripting logic to generate the Ansible groups.

- spine_name: 'xx-SPINE'
- border_name: 'xx-BORDER'
- leaf_name: 'xx-LEAF'

*addressing:* Subnets from which device specific IP addresses are generated. The addresses assigned are based on the device role increment and the node number. These must have the mask in prefix format (/).

- *lp_ip_subnet: 'x.x.x.x/32'*        Core OSPF and BGP peerings. By default will use .10 to .37
- *mgmt_ip_subnet: 'x.x.x.x/27'*      Needs to be at least /27 to cover the maximum spine (4), leaf (10) and border (4)
- *vpc_peer_subnet: 'x.x.x.x/28'*     VPC peer-link addresses. At least /28 to cover the maximum leaf (10) and border (4)
- *srv_ospf_subnet: 'x.x.x.x/28'*     Non-core OSPF process peerings between the borders (4 IPs per-OSPF process)

**fabric.yml**«
*network_size:* How big the network is, so the number of each switch type. The border and leaf switches must be in increments of 2 as are in a VPC pair.

- *num_spines: x*                     Can have a maximum of 4
- *num_borders: x*                    Can have a maximum of 4
- *num_leafs: x*                      Can have a maximum of 10

*address_incre:* The increment that is added to the subnet and device hostname number to generate the unique IP addresses. Different increments are used dependant on the device role to keep the addresses unique.

- *spine_ip: 10*                      Spine IP addresses will be from .11 to .14
- *border_ip: 15*                     Border IP addresses will be from .16 to .19
- *leaf_ip: 20*                       Leaf IP addresses will be from .21 to .30
- *sec_leaf_lp: 30*                   A pair of Leaf secondary loopback IP addresses will be from .31 to .35
- *sec_border_lp: 35*                 A pair of B secondary loopback addresses will be from .36 to .37
- *vpc_leaf_ip: 0*                    Start IP for Leaf Peer Links, so Leaf1 is .1, Leaf2 is .2, Leaf3 is .3, etc
- *vpc_border_ip: 10*                 Start IP for Border Peer Links, so Border1 is .11, Border2 is .12, etc

## Dynamic Inventory

The *inventory script* the *inventory plugin* both achieve the same thing, to create a dynamic inventory from the core data model elements. The inventory script is better for trying things out to get the correct structure (lists and dictionaries) for the input as you are not constrained by Ansible when testing and for printouts. The inventory plugin is easier when building the actual inventory as it is already structured using pre-built Ansible classes and methods. Inventory plugins are the Ansible recommended way but I kept both as the inventory is good for troubleshooting when trying to add new variables to the inventory.

The only things required to build the inventories are the core data model elements.

The inventory script can be run using these cmds:\
**./dyn_inv_script.py --help**&emsp; &emsp; &emsp;                                       *See all the argunments possible*\
**./dyn_inv_script.py --list**&emsp; &emsp; &emsp;                                       *Print to screen all groups, members and vars*\
**./dyn_inv_script.py --host DC1-N9K-BORDER02**                      *Print to screen all host_vars for a specific host*\
**ansible-playbook playbook.yml -i dyn_inv_script.py**               *Run the playbook using the dynamic inventory*

When not running the inventory pluggin against a playbook you have to use *ANSIBLE_INVENTORY_PLUGINS=$(pwd inventory_plugins)* or you could probably set as env var or in config file.\
**ANSIBLE_INVENTORY_PLUGINS=$(pwd inventory_plugins) ansible-inventory -i inv_from_vars_cfg.yml --graph**\
**ANSIBLE_INVENTORY_PLUGINS=$(pwd inventory_plugins) ansible-inventory -i inv_from_vars_cfg.yml --list**\
**ANSIBLE_INVENTORY_PLUGINS=$(pwd inventory_plugins) ansible-inventory -i inv_from_vars_cfg.yml -host=DC1-N9K-SPINE01**\
**ansible-playbook playbook.yml -i inv_from_vars_cfg.yml**                                                  *To run against a playbook*

## Data Models

**ansible.yml -** Contains the login and Ansible settings that would normally be stored in *all.yml*. The reason I dont use  *group_vars* is that the inventory plugin would add each variable in *all.yml* to each devices *host_var* rather than the *group_var*.

- *ansible_python_interpreter:* Python location on the Ansible host (operating system specific)
- *dir_path:* Base directory location to store the generated configuration snippets
- *creds_all:* User credentials for connecting to devices
- *device_type:* Operating system of each device type (spine, leaf and border)

**base.yml -** These variables are used for creating the devices base configuration, so contains things such as naming, IP addressing, users, syslog, aaa, ACLs, etc. The naming format and addressing subnets are used by the inventory and all other templates as are part of the five core elements.

- *device_name:* Naming format for hostname (see core elements)
- *addressing:* Subnets from which device addressing is generated (see core elements)
- *bse.users:* List of device usernames
- *bse_services:* Dictionary of services consumed by the device such as dns, syslog, tacacs, snmp and logging
- *bse_acl:* Management ACLs for things such as snmp and ssh access
- *base_adv:* Configuration elements less likely to change such as the image and exec-timeout

**fabric.yml -** The variables that decide the size of the network and how the physical fabric topology will look. Although the majority of these options can be left the same the extra data models are included to provide additonal nerd knobs to further customize the setup if required.

- *network_size:*  How big the network is. The number of switches per network role (see core elements)
- *fbc:* The core routing options such as OSPF process, area and BGP AS number
- *fbc_adv.base_int:* Provides the ability to change the name and ranges of interfaces used for device interconnects
- *fbc_vpc:* VPC settings for leaf and border switches such as the domain and peerlink details. The keepalive link will always use the mgmt interface and that cant be changed using the data model
- *address_incre:* Increment used to ensure that all device IP addresses are unique (see core elements)

## Service Data Model

**services.yml -** The services that are delivered by the fabric. All are provided on leaf and border switches expect for BGP and OSPF which are only provisioned on the borders. Each service has the mandatory core elements required to provide the service and the optional advanced elements if customization is required.

### Tenants & VLANs

Used to create tenants (VRF), L3VNIs, SVIs, L2VNIs and VLANs. If it is a L3 tenant a VRF is created on the leaf and borders but the SVI and VLANs created only on the leafs. If it is not a L3 tenant no VRF is created and the VLANs are created on the leaf and borders as the default gateway will be on an external router or firewall attached to the borders.

- *srv_tenants:*
  - *tenant_name:*              Name of the VRF, only created if it is *l3_tenant*
  - *l3_tenant:*                If *yes* it will create a VRF, L3VNI and the associated VLAN and SVI
    - *vlans:*                  List of VLANs within this tenant
    - *num:*                    VLAN name
    - *name:*                   VLAN number
    - *ip_addr:*                Adding an IP makes it a L3 VLAN and creates the SVI
    - *ipv4_bgp_redist:*        *Yes* will redistribute the SVI into the BGP IPv4 address-family

The L3VNIs and L2VNIs are automatically generated from the base VNI values. By default the L3VNIs/SVIs start at 3001 and are incremented by 1 for each L3 tenant. The L2VNIs start at 10000, are created per-vlan by adding the vlan number to this value and are incremented by 10000 per tenant.

- *srv_tenants_adv.base_vni:*
  - *tn_vlan: 3001*      Transit L3VNI start VLAN number. Increments by 1 for each L3 tenant (VRF)
  - *l3vni: 3001*        Transit L3VNI start VNI number. Increments by 1 for each L3 tenant (VRF)
  - *l2vni: 10000*       Start L2VNI and range to add to each tenant vlan. Increments by 10000 for each tenant

- *srv_tenants_adv.bgp:* Options to change the redistribution route-map name and tag value

### Interfaces

Used to create the single and dual homed interfaces. Any interface can be delegated as a *trunk*, *access* or *layer3* with each having its own *port_variable*. *single-homed* and *dual-homed* are dictionary keys with the values being lists of interfaces and their parameters. The port-channel mode is only available on dual-homed interfaces and OSPF can only be enabled on a border switch layer3 interface.

- *srv_ports:*
  - *single_homed:*          For devices only attached to one switch
    - *description:*         Interface description
    - *port_type:*           Can be *access*, *trunk* or *layer3*
    - *port_variable:*       If *access* is the vlan, if *trunk* the allowed vlans (seperated by ,) and if *layer3* the IP address
    - *ospf:*                Optionally enable OSPF. Specify process and hello, area is automatically worked out
    - *switch:*              Name of the switch to which the port is added
  - *dual_homed:*            For devices attached in a port-channel to two switches
    - *description:*
    - *port_type:*
    - *port_variable:*
    - *ospf:*
    - *po_mode:*             Whether is static, LACP, PAGP and the mode
    - *switch:*              Only specify the odd numbered switch, it will automatically be created on the VPC pair

Modify which interfaces are reserved for single and dual-homed port assignment as well the port-channel and vpc ranges used. This applies to all leaf and border switches.

- *srv_ports_adv:*
  - *dual_homed:*
    - *first_int: Ethernet1/21*      First interface
    - *last_int: Ethernet1/50*       Last interface
    - *po: 21*                                 First PortChannel used
    - *vpc: 21*                                First VPC used
  - *single_homed:*
    - *first_int: Ethernet1/51*      First interface
    - *last_int: Ethernet1/60*       Last interface

### Routing Protocols

Creates the BGP peerings or non-backbone OSPF process only on the border switches. For redistribution and filtering (*allowed_in* and *allowed_out*) can list the required networks or use the pre-built ALLOW-ALL, DENY-ALL and DEFAULT prefix-lists.

- *srv_routing:*
  - *tenant:*                                    The VRF that all the routing protocols are within
    - *bgp:*
      - *inet_peerings:*                ISP peerings which only accept a default-route in
        - *name:*                       Short name used in route-map prefix-list names
        - *remote_as:*
        - *peer_ip:*
        - *description:*
        - *allowed_out:*              Specify the networks or use ALLOW-ANY, DENY-ANY or DEFAULT
        - *timers: [3, 9]*              Uses the default of 3 and 9 unless unhased and specified
      - *bgp_peerings:*                   BGP peerings which can advertise and receive anything
        - *name:*
        - *remote_as:*
        - *peer_ip:*
        - *description:*
        - *allowed_in: [ALLOW-ANY]*
        - *allowed_out: [DENY-ALL]*
        - *timers: [3, 9]
    - *ospf:*                                      Only creates the process, interfaces are added using *srv_ports*
      - *pro:*                                   The same process number is used on all borders
      - *area: 0.0.0.1*                        First area, BORDER1/2 would be 0.0.0.1 and BORDER3/4 0.0.0.2
      - *inter_sw_vlan:*                     VLAN used for OSPF peering between border leafs (IP got from *base.yml*)
      - *default_orig: no*                 Use *'yes'* or *'always'* to advertise a default route
      - *bgp_redist_in: yes*             Redistributes based on the tenant RT (are the SVIs redist into BGP with a tag)
      - *bgp_redist_out: [ALLOW-ANY]*     The network/prefix (seperated by ,) redist into this tenant (into BGP)

- *srv_routing_adv.bgp:* Use to change the naming format for the BGP route-maps and prefix-lists
- srv_routing_adv.ospf:* Use to change the naming format for the BGP route-maps, prefix-list and community list

## Rendering the Templates

Simple playbook that runs the different plays to create the seperate configuration snippets and store them in a folder specifically for that device. The default location for this is *~/device_configs* but can be changed in *ansible.yml*. Each play can be run individually using the following tags:

- **dir**             Deletes the base directory (*device_configs*) and recreates it
- **base**          Renders *base_template.j2* with *base.yml* and stores the generated output in *base.cfg*
- **fabric**        Renders *fabric_template.j2* with *fabric.yml* and stores the generated output in *fabric.cfg*
- **services**    Renders *services_template.j2* with *services.yml* and stores the generated output in *services.cfg*

## Notes and Improvements

Improve the naming format for elements within files and those gained from filter plugins. This will make it easier to see where they are from in the templates.\
Pass all the data model files through python plugins to create the complete data models to be used in the templates. By doing that it will simplify the templates and get rid of some of the nesting.\
The templates needs to be simpler so that it is easy for people with little coding knowledge to be able to update.

The services data model is not as simple and declaritive as I would like. Rather than editing this to add to these services should probably add another layer of abstraction by creating new plays so that when a service is to be added that play makes the changes to the services.yml file.

How to integrate with IPAM (netbox)?\
-Do you use the netbox inventory plugin to pull the elements down for interfaces, subnet ranges and IPs?\
-Alternatively do you build the API calls to do this into your own inventory plugin?\
-Do you continue to auto-generate the interfaces and addressing and then push that config info to IPAM?

When I run playbook it fails sometimes on directory deletion so have to rerun. Need to investigate why.

Want to deploy by replacing the whole configuration on a device. It will be difficult to do as the device configs have to be in the exact correct order. How do you handle:\
-The OS config re-orders some elements by lower numeric or alphabetic value such as VLANs or VNIs.\
-Configuration where a hyphen is used, for example the VLANs list.\
-Joining together the config snipets when you have different config elements in one snippets that need to be in different locations in the config file?

Going to need to have two types of validation:\
-Sanity check the input. Make sure all formating is correct and the entered values are legitimate before it tries to build the config snippets.\
-Once deployed need to make sure connnections are as expected (LLDP), protocols up (BGP, OSPF) and services functioning (VXLAN, port-channels).
