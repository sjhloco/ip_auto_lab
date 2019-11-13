# Data Models - Deploy Leaf and Spine

The idea behind these data models is to deploy a leaf and spine architecture and its related services in a declarative manner. A dynamic inventory is created using either an inventory plugin or dynamic inventory script based on the information within the data models. Unless specifically stated all the elements of the data model can be changed as the none of the scripting or templating uses the actual contents to make decisions.

This deployment will only scale upto 4 spines, 4 borders and 10 leafs. By default the following ports are used for inter-switch links, ideally these ranges would not be changed but if need be can be done so within *fabric.yml*.
- SPINE-to-LEAF = Eth1/1 - 1/10     
- SPINE-to-Border = Eth1/11 - 1/15
- BORDER-to-SPINE: = Eth1/1 - 1/5
- LEAF-to-SPINE = Eth1/1 - 1/5      
- VPC Peer-link = Eth1/127 - 128

## Core Data Model Elements
These core elements are what is required to make this declarative and are used for the dynamic inventory creation as well as by the majority of the templates.

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

*address_incre:*

## Data Models
**ansible.yml -** Contains the login and Ansible settings that would normally be stored in *all.yml*. The reason I dont use  *group_vars* is that the inventory plugin would add each variable in *all.yml* to every devices *host_var*.

- *ansible_python_interpreter:* Python location on the Ansible host (operating system specific)           
- *dir_path:* Base directory Location to store the generated configuration snippets
- *creds_all:* User credentials for connecting to devices
- *device_type:* Operating system of each device type (Spine, Leaf and Border)

**base.yml -** These varaibles are used for creating the devices base configuration, so contains things such as naming, IP addressing, users, syslog, aaa, ACLs, etc. The naming format and addressing subnets are used by the inventory and all other templates as are part of the 5 core elements needed to make this declaritive.

- *device_name:* Naming format for hostname (see core elements for more details)
- *addressing:* Subnets from which device addressing is generated (see core elements for more details)
- *bse.users:* List of device usernames
- *bse_services:* Dictionary of services consumed by the device such as dns, syslog, tacacs, snmp and logging
- *bse_acl:* Management ACLs for things such as snmp and ssh access
- *base_adv:* Configuration elements less likely to change such as the image and exec-timeout










