# Network/Device State Report

Collects information from devices to create result tables on each element of a network and combine these into a report.
<br/>Each network element is a seperate role that creates a table for that element. Using tags can run the individual elements or combine elements and create a custom report.

The tables created for each element are stored in *~/network_state/tmp_tables* which is deleted at the start of each playbook run. The report assemebles all these tables into the one file. Reports are stored in *~/network_state*, have the date appplied ot make them unique and are not deleted at the start of each playbook run.

The command outputs are passed through Python filters to create a list from each devices results. Inline jinja is used to create a local ansible fact that is a list of all the device lists for each network element. These list of lists are then used in a further Python filter to build the tables. 

The following network specific variables are stored in *group_vars* and added to the results tables to give a baseline for the expected outcome for vital things such as BGP peerings, OSPF neigbors and L2L VPNs
<br/>**asa.yml:** &nbsp;&nbsp; *ospf_neigh, vpn_peer*
<br/>**iosxe.yml:** &nbsp;&nbsp; *ospf_neigh, bgp_neigh, vpn_peer*
<br/>**spine.yml, leaf.yml, border_leaf.yml:** &nbsp;&nbsp; *bgp_neigh, ospf_neigh*

### Tables/ Tag ###
**--tag bgp** &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Creates */tmp/network_state/tmp_tables/bgp_table.txt*
<br/>Table headers: &nbsp;&nbsp;&nbsp;&nbsp; 'Expected BGP Peers', &nbsp; 'Enabled BGP Peers', &nbsp; 'UP BGP Peers', &nbsp; 'Received prefixes'

**--tag edge** &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Creates */tmp/network_state/tmp_tables/edge_table.txt*
<br/>Table headers: &nbsp;&nbsp;&nbsp;&nbsp; 'Total L2L VPNs', &nbsp; 'Up L2L VPNs',&nbsp;  'Total NAT Translations'

**--tag itf** &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Creates */tmp/network_state/tmp_tables /interface_table.txt*
<br/>Table headers: &nbsp;&nbsp;&nbsp;&nbsp; 'VLANs',&nbsp; 'MACs', &nbsp; 'Configured POs', &nbsp; 'UP POs', &nbsp; 'PO member ports', &nbsp; 'UP PO member ports'

**--tag  l2** &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Creates */tmp/network_state/tmp_tables/l2_table.txt*
<br/>Table headers: &nbsp;&nbsp;&nbsp;&nbsp; 'ARP Table', &nbsp; 'Routing Table'

**--tag l3** &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Creates */tmp/network_state/tmp_tables/l3_table.txt*
<br/>Table headers: &nbsp;&nbsp;&nbsp;&nbsp; 'Enabled Interfaces', &nbsp; 'UP Interfaces', &nbsp; 'LLDP Neighbors'

**--tag ospf** &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Creates */tmp/network_state/tmp_tables/ospf_table.txt*
<br/>Table headers: &nbsp;&nbsp;&nbsp;&nbsp; 'Expected Neighors', &nbsp; 'UP Neighbors', &nbsp; 'Total LSAs'

**--tag vip** &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Creates */tmp/network_state/tmp_tables/vip_table.txt*
<br/>Table headers: &nbsp;&nbsp;&nbsp;&nbsp; 'Enabled VIPs', &nbsp; 'UP VIPs', &nbsp; 'Total Nodes', &nbsp; 'UP Nodes'

**--tag report** &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Creates */tmp/network_state/network_state_DATE/txt*
<br/>Builds the main directory, cleans the tmp directory and assembles all the tables into the one file

### Network Modules ###
No one module could collect and parse all desired the output so the playbook uses a combination of Ansible *network_cli*, *command* (with native *Genie*), *napalm* and *parse_genie*.
<br/>For commands that dont have parsers the playbook uses *| include*. Piping isnt supported by *napalm* APIs so for these commands *network_cli* is used.
<br/>For parsers missing from *napalm* the playbook uses *parse_genie* as all the networking equipment used in this playbook is Cisco. *show bgp all summary* is broken in *parse_genie* so the Ansible *command* with native *Genie* is used instead for this one command.
<br/><br/>username and passwords are stored in *group_vars* for *napalm* and *network_cli*. Until the parse-genie is fixed as the playbook has to use native *Genie* a *roles/bgp/bgp_testbed.yaml* file is required that also has the hostname, username and password for all CSRs.

### Tested on ###
Has only been tested on the following versions of virtual equipment:
<br/>F5: 13.1.1
<br/>N9K: 7.0(3)I7(6)
<br/>ASAv: 9.9(1)
<br/>CSR: 16.06.02
<br/>vIOS: 15.2

### Example Report ###
<br/>===== BGP Table =====<br/>

|      Device     | Expected Peers | Enabled Peers | UP Peers | pfxrcd |
| --- | --- | --- | --- | --- |
|  dc1-n9k-spine1 |       3        |       3       |    3     |   26   |
|  dc1-n9k-spine2 |       3        |       3       |    3     |   26   |
|  dc1-n9k-leaf1  |       2        |       2       |    2     |   12   |
|  dc1-n9k-leaf2  |       2        |       2       |    2     |   12   |
| dc1-n9k-border1 |       4        |       4       |    4     |   44   |
|  dc1-csr-xnet1  |       4        |       4       |    4     |   4    |

<br/>===== Edge Table =====<br/>

|     Device    | Total L2L VPNs | Up L2L VPNs | Total NAT Translations |
| --- | --- | --- | --- |
| dc1-csr-xnet1 |       0        |      0      |           1            |
| dc1-asav-xfw1 |       0        |      0      |           3            |

<br/>===== Interface Table =====<br/>

|      Device     | Enabled Interfaces | UP Interfaces | LLDP Neighbors |
| --- | --- | --- | --- |
|  dc1-n9k-spine1 |         9          |       9       |       3        |
|  dc1-n9k-spine2 |         9          |       9       |       3        |
|  dc1-n9k-leaf1  |         22         |       22      |       5        |
|  dc1-n9k-leaf2  |         22         |       22      |       5        |
| dc1-n9k-border1 |         10         |       10      |       3        |
|   dc1-vios-sw1  |         6          |       6       |       0        |
|  dc1-csr-xnet1  |         6          |       6       |       1        |
|  dc1-asav-xfw1  |         4          |       8       |       0        |

<br/>===== Layer2 Table =====<br/>

|     Device    | VLANs | MACs | cfg POs | UP POs | PO member ports | UP PO member ports |
| --- | --- | --- | --- | --- | --- | --- |
|  dc1-vios-sw1 |   11  |  3   |    1    |   1    |        2        |         2          |
| dc1-n9k-leaf1 |   9   |  14  |    4    |   4    |        4        |         4          |
| dc1-n9k-leaf2 |   9   |  14  |    4    |   4    |        4        |         4          |

<br/>===== Layer3 Table =====<br/>

|      Device     | ARP Table | Routing Table |
| --- | --- | --- |
|  dc1-csr-xnet1  |     11    |       18      |
|  dc1-asav-xfw1  |     4     |       20      |
|  dc1-n9k-spine1 |     5     |       10      |
|  dc1-n9k-spine2 |     5     |       10      |
|  dc1-n9k-leaf1  |     8     |       25      |
|  dc1-n9k-leaf2  |     8     |       25      |
| dc1-n9k-border1 |     6     |       25      |


<br/>===== OSPF Table =====<br/>

|      Device     | Expected Neighors | UP Neighbors | Total LSAs |
| --- | --- | --- | --- |
|  dc1-csr-xnet1  |         1         |      1       |     4      |
|  dc1-asav-xfw1  |         2         |      2       |     12     |
|  dc1-n9k-spine1 |         3         |      3       |     5      |
|  dc1-n9k-spine2 |         3         |      3       |     5      |
|  dc1-n9k-leaf1  |         3         |      3       |     5      |
|  dc1-n9k-leaf2  |         3         |      3       |     5      |
| dc1-n9k-border1 |         3         |      3       |     13     |

<br/>===== VIP Table =====<br/>

|    Device   | Enabled VIPs | UP VIPs | Total Nodes | UP Nodes |
| --- | --- | --- | --- | --- |
| dc1-ltm-lb1 |      2       |    1    |      3      |    2     |
