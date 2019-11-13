# Data Models - Deploy Leaf and Spine

The idea behind these data models is to deploy a leaf and spine architecture and its related services in a declarative manner. A dynamic inventory is created using either an inventory plugin or dynamic inventory script based on the information within the data models. Unless specifically stated all the elements of the data model can be changed as the none of the scripting or templating uses the actual contents to make decisions.

There are no external hookins with these data models so the device configuration is generated solely from the contents of the data models

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










