# Data Models - Deploy Leaf and Spine

The idea behind these data models is to deploy a leaf and spine architecture and its related services in a declarative manner. A dynamic inventory is created using either an inventory plugin or dynamic inventory script based on the information within the data models. Unless specifically stated all the elements of the data model can be changed as the none of the scripting or templating uses the actual contents to make decisions.

This deployment will only scale upto 4 spines, 4 borders and 10 leafs. By default the following ports are used for inter-switch links, ideally these ranges would not be changed but if need be can be done so within *fabric.yml*.
- SPINE-to-LEAF = Eth1/1 - 1/10     
- SPINE-to-Border = Eth1/11 - 1/15
- BORDER-to-SPINE = Eth1/1 - 1/5
- LEAF-to-SPINE = Eth1/1 - 1/5      
- VPC Peer-link = Eth1/127 - 128

## Core Data Model Elements
These core elements are what is required to make this declarative and are used for the dynamic inventory creation as well as by the majority of the templates.

**ansible.yml**
<br/>*device_type:* Operating system of each device type (Spine, Leaf and Border)

**base.yml**
<br/>*device_name:* The naming format that the automatically generated node number is added to (in the format 0x). The names can be changed, but the last hyphen and name after it (SPINE, BORDER or LEAF) MUST not be changed the as that is what is used to in the scripting logic to generate the Ansible groups.
- spine_name: 'xx-SPINE'
- border_name: 'xx-BORDER'
- leaf_name: 'xx-LEAF'

*addressing:* Subnets from which device specific IP addresses are generated. The addresses assigned are based on the device role specific increment and the node numbe. These must have the mask in prefix format (/). 
- *lp_ip_subnet: 'x.x.x.x/32'* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Core OSPF and BGP peerings. By default will use .10 to .37
- *mgmt_ip_subnet: 'x.x.x.x/27'* &nbsp;&nbsp;&nbsp; Needs to be at least /27 to cover max spine (4), leafs (10) and borders (4)
- *vpc_peer_subnet: 'x.x.x.x/28'* &nbsp;&nbsp; VPC peer-link addresses. At least /28 to cover max leafs (10) and borders (4)
- *srv_ospf_subnet: 'x.x.x.x/28'* &nbsp;&nbsp;&nbsp; Non-core OSPF process peerings between borders (4 IPs per-OSPF process)

**fabric.yml**
<br/>*network_size:* How big the network is, so the number of each switch type. border/leaf must be in increments of 2 as are in a VPC pair.
- *num_spines: x* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Can have a maximum of 4
- *num_borders: x* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Can have a maximum of 4
- *num_leafs: x* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Can have a maximum of 10

*address_incre:* # The increment that is added to the subnet and device hostname number to generate the unique last octet of the IP addresses. Different increments are used dependant on the device role to keep the addresses unique. The below IP addesses are based on the default values
- *spine_ip: 10* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Spine IP addresses will be from .11 to .14
- *border_ip: 15* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Border IP addresses will be from .16 to .19
- *leaf_ip: 20* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Leaf IP addresses will be from .21 to .30
- *sec_leaf_lp: 30* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Pair of Leaf secondary loopback IP addresses will be from .31 to .35
- *sec_border_lp: 35* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Pair of BORDER secondary loopback addresses will be from .36 to .37
- *vpc_leaf_ip: 0* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Start IP for Leaf Peer Links, so Leaf1 is .1, Leaf2 is .2, Leaf3 is .3, etc
- *vpc_border_ip: 10* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Start IP for Border Peer Links, so Border1 is .11, Border2 is .12, etc

## Dynamic Inventory
Have a dynamic inventory script and as well as an inventory plugin which both do the same thing. Dynamic inventory is better for trying things out to get the code correct as not constrained by Ansible in testing and printouts. The inventory plugin is easier when building the actaul inventory as it is already structured using Ansible class and methods. Inventory plugins is the recomended way but kept both as dynamic inventory is good for troublehsooting and trying out new elements in the invtory.

The only things required to build the invnetorires are the core data model elements.

The dynamic script can be run using these cmds:
**./dyn_inv_script.py --help** &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; *See all the argunments possible*
**./dyn_inv_script.py --list** &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; *Print to screen all groups, members and vars*
**./dyn_inv_script.py --host DC1-N9K-BORDER02**&nbsp;&nbsp;&nbsp;&nbsp; *Print to screen all host_vars for a specific host*
**ansible-playbook playbook.yml -i dyn_inv_script.py** &nbsp;&nbsp;&nbsp; *Run the playbook using the dynamic inventory*

The inventory pluggin can be run using these cmds. When not running against a playbook have to use this *ANSIBLE_INVENTORY_PLUGINS=$(pwd inventory_plugins)*, guess can set as env var or set in config file.
**ANSIBLE_INVENTORY_PLUGINS=$(pwd inventory_plugins) ansible-inventory -i inv_from_vars_cfg.yml --graph** &nbsp;&nbsp; *Just outputs all groups*
**ANSIBLE_INVENTORY_PLUGINS=$(pwd inventory_plugins) ansible-inventory -i inv_from_vars_cfg.yml --list** &nbsp;&nbsp; *All host_vars, groups and members*
**ANSIBLE_INVENTORY_PLUGINS=$(pwd inventory_plugins) ansible-inventory -i inv_from_vars_cfg.yml -host=DC1-N9K-SPINE01**         
**ansible-playbook playbook.yml -i inv_from_vars_cfg.yml** &nbsp;&nbsp;&nbsp;&nbsp; *To run against a playbook*

## Data Models
**ansible.yml -** Contains the login and Ansible settings that would normally be stored in *all.yml*. The reason I dont use  *group_vars* is that the inventory plugin would add each variable in *all.yml* to every devices *host_var*.

- *ansible_python_interpreter:* Python location on the Ansible host (operating system specific)           
- *dir_path:* Base directory Location to store the generated configuration snippets
- *creds_all:* User credentials for connecting to devices
- *device_type:* Operating system of each device type (Spine, Leaf and Border)

**base.yml -** These varaibles are used for creating the devices base configuration, so contains things such as naming, IP addressing, users, syslog, aaa, ACLs, etc. The naming format and addressing subnets are used by the inventory and all other templates as are part of the 5 core elements needed to make this declaritive.

- *device_name:* Naming format for hostname (see core elements)
- *addressing:* Subnets from which device addressing is generated (see core elements)
- *bse.users:* List of device usernames
- *bse_services:* Dictionary of services consumed by the device such as dns, syslog, tacacs, snmp and logging
- *bse_acl:* Management ACLs for things such as snmp and ssh access
- *base_adv:* Configuration elements less likely to change such as the image and exec-timeout

**fabric.yml -** The variables that decide the size of the network and how the physical fabric topology will look. Although the majority of these options can be left the same the data models are included to provide additonal nerd knobs to further customize the setup if required.

- *network_size:*  How big the network is, the number of switches per network role (see core elements)
- *fbc:* The core routing options such as OSPF process, area and BGP AS number
- *fbc_adv.base_int:* Provides the ability to change the name and ranges of interfaces used for the different device inter-connects (e.g. spine to leafs)
- *fbc_vpc:* VPC settings for leaf and border switches such as the domain and peer link details. The keepalive will always use the mgmt interface and cant be changed using the data model
- *address_incre:* Increment used to ensure that all device IP addresses are unique (see core elements)

## Service Data Model

**services.yml -** All the services that are delivered by the fabric. These are the provision of tenants, vlans, interfaces, external BGP peerings and non-core OSPF domains. All are provided on leaf and border switches expect for BGP and OSPF which are only provisioned on the borders. 
<br/><br/>Each service has the manadatory core elements required to provide the service and the optional advanced elements if customization is required.

### Tenants & VLANs
- *srv_tenants:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Used to create tenants (VRF), L3VNIs, SVIs, L2VNIs and VLANs
  - *tenant_name:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Name of the VRF, it will only be created if it is *l3_tenant*
  - *l3_tenant:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; If *yes* it will create a VRF, L3VNI and the associated VLAN and SVI
      - *vlans:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; List of VLANs within this tenant
      - *num:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; VLAN Name
      - *name:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; VLAN number
      - *ip_addr:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Adding an IP makes it a L3 VLAN and creates the SVI
      - *ipv4_bgp_redist:* &nbsp;&nbsp;&nbsp;&nbsp; *Yes* will redistribute the SVI into BGP IPv4 address-family

- *srv_tenants_adv.base_vni:* &nbsp;&nbsp;&nbsp;&nbsp; The L3VNIs and L2VNIs are automatically generated from these base values. By default the L3VNI/SVI starts at 3001 and increments by 1 for each L3 tenant, the L2VNI starts at 10000, are created per vlan by adding the vlan number to this value and are increment by 10000 per tenant
  - *tn_vlan: 3001* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Transit L3VNI start VLAN number. Increments by 1 for each L3 tenant (VRF)
  - *l3vni: 3001* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Transit L3VNI start VNI number. Increments by 1 for each L3 tenant (VRF)
  - *l2vni: 10000* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Start L2VNI and range to add to each tenant vlan. Increments by 10000 for each tenant

- *srv_tenants_adv.bgp:*&nbsp;&nbsp; Options to change the redistribution route-map name and tag value

### Interfaces
- *srv_ports:* &nbsp;&nbsp;&nbsp;&nbsp; Used to create the single and dual homed interfaces. Any interface can be delegated as a trunk, access or Layer 3 port. *single-homed* and *dual-homed* are dictionary keys with the values being lists of interfaces. OSPF can only be enabled on a Border switch Layer 3 interface
  - *single_homed:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; For devices only attached to one switch
    - *description:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Interface description
    - *port_type:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Can be *access*, *trunk* or *layer3*
    - *port_variable:* &nbsp;&nbsp;&nbsp;&nbsp; If *access* is the vlan, if *trunk* the allowed vlans (seperated by ,) and if *layer3* the IP address
    - *ospf:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;  Optionally enable OSPF. Specify the process and hello, area is automatically worked out
    - *switch:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Name of the switch to which the port is added
  - *dual_homed:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; For devices attached in a port-channel to two switches                            
    - *po_mode:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Same settings as single-homed, but must 
    - *switch:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Only specify the odd numbered switch and it is automatically created on the VPC pair.  

- *srv_ports_adv:* &nbsp;&nbsp;&nbsp;&nbsp; Modify the reserved interface, port-channel and vpc ranges that server ports can be automatically assigned from. This applies to all leaf and border switches
  - *dual_homed:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Used only for dual-homed devices
    - *first_int: Ethernet1/21* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; First interface
    - *last_int: Ethernet1/50* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Last interface
    - *po: 21* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;  First PortChannel used
    - *vpc: 21* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;  First VPC used
  - *single_homed:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Used only for single-homed devices
    - *first_int: Ethernet1/51* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; First interface
    - *last_int: Ethernet1/60* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;  Last interface

### Routing Protocols
- *srv_routing:* &nbsp;&nbsp;&nbsp;&nbsp; Used to create BGP peerings or non-backbone OSPF process only on the border switches. For redistribution and filtering (*allowed_in* and *allowed_out*) can list the required networks or use the pre-built prefix-lists of ALLOW-ALL, DENY-ALL and DEFAULT. 
  - *tenant:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp The VRF that all the routing protocols are in
    - *bgp:*
      - *inet_peerings:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ISP peerings which only accept a default-route in
        - *name:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Short name used in route-maps
        - *remote_as:*
        - *peer_ip:*
        - *description:*
        - *allowed_out:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; The network/prefix (seperated by ,) advertised. Blank will allow all
        - *timers: [3, 9]* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Uses the default of 3 and 9 unless unhased and specified
      - *ebgp_peerings:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; eBGP peerings which can advertise and receive anything
        - *name:*
        - *remote_as:*
        - *peer_ip:*
        - *description:*
        - *allowed_in: [ALLOW-ANY]* &nbsp;&nbsp;&nbsp; Specify the network/prefixes or use ALLOW-ANY, DENY-ANY or DEFAULT      
        - *allowed_out: [DENY-ALL]*
        - *timers: [3, 9]
    - *ospf:* &nbsp;&nbsp;&nbsp;&nbsp; Only creates the OSPF process, interfaces are added using the 'Device ports' service
      - *pro:* &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; The same process number is used on all border switches
      - *area: 0.0.0.1*  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; First area, so BORDER1/2 will be 0.0.0.1 and BORDER3/4 0.0.0.2
      - *inter_sw_vlan:*  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; VLAN used for OSPF peering between border leafs (IP is got from base.yml)
      - *default_orig: no* &nbsp;&nbsp;&nbsp;&nbsp; Use 'yes' to advertise default route or 'always' to advertise it even if it doesnt exist
      - *bgp_redist_in: yes* &nbsp;&nbsp;&nbsp;&nbsp; Redistributes based on the tenant RT, these are the SVIs redist into BGP with a tag
      - *bgp_redist_out: [ALLOW-ANY]* &nbsp;&nbsp;&nbsp;&nbsp; The network/prefix (seperated by ,) redist into this tenant (into BGP).

- *srv_routing_adv.bgp:* &nbsp;&nbsp;&nbsp;&nbsp; Use to change the naming format for the BGP route-maps and prefix-lists 
- **dir**
srv_routing_adv.ospf:* &nbsp;&nbsp;&nbsp;&nbsp; Use to change the naming format for the BGP route-maps, prefix-list and community list

## Notes/ Caveats/ Improvemnents/ Validation
Simple playbook runs the different plays to create the sperate config snippets and stores in a floder specifically for that device. The default location for this is *~/device_configs* but can be changed in ansible.yml. Specific plays can be run individually using the following tags.
- **dir** &nbsp;&nbsp; Deletes the base directory (*device_configs*) and recreates it 
- **base** &nbsp;&nbsp; Renders *base_template.j2* with *base.yml* and stores the generated output in *base.cfg*
- **fabric** &nbsp;&nbsp; Renders *fabric_template.j2* with *fabric.yml* and stores the generated output in *fabric.cfg*
- **services** &nbsp;&nbsp; Renders *services_template.j2* with *services.yml* and stores the generated output in *services.cfg*

## Notes/ Caveats/ Improvemnents/ Validation
The services data model is a bit big and difficult for a user to edit, therefore use other playbooks to addd services that will update this file. Another layer of abstraction.
<br/>Would be better to refactor and pass all varible files through Filter pluggins to create new varible files. By doing that woill simplify the Jinja and get rid of some of the nesting. 
<br/>Jinja template needs to be more simple so it easy for people with little codong knowledge to be able to update if an any of the device OS config changes
<br/>Want to deploy with replace but will be difficult as device configs are in a very specific order. How do you handle:
<br/>-THings like VLANs added later but wiht lower VLNA number, need to order code in correct order
<br/>-When hyphen is used, for exampel mulitple vlans
<br/>-join together the snipets when different config elements in one snippets needs to be in different locations in config file?
<br/>
<br/>When run play book, fails sometimes on directory dlettion or creation, need ot find out why
<br/><br/>
Going to need to have two types of validation
<br/>-Sanity check the input, make sure all formating is correct and values legit beforre even try to build the config
<br/>-CHeck after deployment of the config

<br/><br/>
How to integrate IPAM. DO you use a plugin to pull the elements down for interfaces and IPs, or do you autogenerate and push that config to IPAM?

<br/>Improve naming format for elements within files and those from filter plugins
