from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

# ============================== Documentation ============================
# options match get_options and are actually configuration (i.e. type, required, default)

DOCUMENTATION = '''
    name: inv_from_vars
    plugin_type: inventory
    version_added: "2.8"
    short_description: Creates inventory from desired state
    description:
        - Dynamically creates inventory from specified number of Spine & leaf devices
    extends_documentation_fragment:
        - constructed
        - inventory_cache
    options:
        plugin:
            description: token that ensures this is a source file for the 'leaf_spine' plugin.
            required: True
            choices: ['inv_from_vars']
        var_files:
            description: Data-model in Ansible vars directory where dictionaries will be imported from
            required: True
            type: list
        var_dicts:
            description: Dictionaries that wil be imported from the data-model
            required: True
            type: list

'''
# What users see as away of instructions on how to run the plugin
EXAMPLES = '''
# inv_from_vars_cfg.yml file in YAML format
# Example command line: ANSIBLE_INVENTORY_PLUGINS=$(pwd inventory_plugins) ansible-inventory -v --list -i inv_from_vars_cfg.yml
plugin: inv_from_vars

# Data-model in Ansible vars directory where dictionaries will imported from
var_files:
  - ansible.yml
  - base.yml
  - fabric.yml

# Dictionaries that wil be imported from the data-model
var_dicts:
  ansible:
    - device_type                       # Device type (os) for each switch type (group)
  base:
    - device_name                   # Naming format for each host
    - addr                    # Address ranges the devices IPs are created from. Loopback must be /32

  fabric:
    - network_size                  # Dictates number of inventory objects created for each device role
    - bse_intf                   # Naming and increments for the fabric interfaces
    - lp                            # Loopback interfaces
    - mlag                      # mlag settings
    - addr_incre             # Network address increment used for each device role (group)
'''

# ==================================== Plugin ==================================
# Modules used to format date ready for creating the inventory
import os
import yaml
from ipaddress import ip_network
from collections import defaultdict
from pprint import pprint
# Ansible modules required for the features of the inventory plugin
from ansible.errors import AnsibleParserError
from ansible.module_utils._text import to_native, to_text
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable, Cacheable

# Ansible Inventory plugin class that holds pre-built methods that run automatically (verify_file, parse) without needing to be called
class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    NAME = 'inv_from_vars'     # Should match name of the plugin

# ==================================== Verify config file ==================================
    # 1. Makes a quick determination whether the inventory source config file is usable by the plugin
    def verify_file(self, path):
        valid = False
        if super(InventoryModule, self).verify_file(path):
            if path.endswith(('inv_from_vars_cfg.yaml', 'inv_from_vars_cfg.yml')):
                valid = True
        return valid

# ============================ Generates host details from data models ==========================
    #3. Generates the hostname and IP addresses to be used to create the inventory using data model from config file
    def create_objects(self):
        self.spine, self.border, self.leaf, self.mgmt_ip, self.rtr_lp, self.vtep_lp, self.mlag_lp, self.bgw_lp = ([] for i in range(8))

        ##### !!!! NEED to RENAME
        # Used in create_inventory to set the element on which to start loop so skips spine and/or border loopback addresses
        self.skip_sp = self.network_size['num_spines']
        self.skip_lf = self.network_size['num_leafs']
        self.skip_bdr = self.network_size['num_borders']
        self.skip_sp_lf = self.network_size['num_spines'] + self.network_size['num_leafs']

        # Halfs the the number of border and leaf switches which is used to create the MLAG loopback IP
        half_num_borders = self.network_size['num_borders'] /2
        half_num_leafs = self.network_size['num_leafs'] /2

        # 3a. Generate a lists of Spine switches, the management IPs and Loopback IPs
        num = 0
        while self.network_size['num_spines'] != 0:
            num += 1            # Increments by 1 for each device
            # Creates the name using the incremented (double-decimal format)
            self.spine.append(self.device_name['spine'] + str("%02d" % num))
            # Creates the mgmt IP by adding the num_incr and device_ip_incr to the the network address
            self.mgmt_ip.append(str(ip_network(self.addr['mgmt_net'], strict=False)[self.addr_incre['spine_ip'] + num -1]))
            # Creates the RTR loopback by adding the num_incr and device_ip_incr to the the network address and then adding subnet
            self.rtr_lp.append(str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['spine_ip'] + num -1) + '/' + self.addr['lp_net'].split('/')[1])
            self.network_size['num_spines'] -= 1        # Reduces number of spines each iteration

        # 3b. Generate a lists of leaf switches and adds management IPs and Loopback IPs to existing list
        num = 0
        while self.network_size['num_leafs'] != 0:
            num += 1
            self.leaf.append(self.device_name['leaf'] + str("%02d" % num))
            self.mgmt_ip.append(str(ip_network(self.addr['mgmt_net'], strict=False)[self.addr_incre['leaf_ip'] + num -1]))
            self.rtr_lp.append(str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['leaf_ip'] + num - 1) + '/' + self.addr['lp_net'].split('/')[1])
            self.vtep_lp.append(str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['leaf_vtep_lp'] + num -1) + '/' + self.addr['lp_net'].split('/')[1])
            self.network_size['num_leafs'] -= 1

       # 3c. Generate a lists of border switches and adds management IPs and Loopback IPs to existing list as well as neew vist for VTEPs
        num = 0
        while self.network_size['num_borders'] != 0:
            num += 1
            self.border.append(self.device_name['border'] + str("%02d" % num))
            self.mgmt_ip.append(str(ip_network(self.addr['mgmt_net'], strict=False)[self.addr_incre['border_ip'] + num -1]))
            self.rtr_lp.append(str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['border_ip'] + num - 1) + '/' + self.addr['lp_net'].split('/')[1])
            self.vtep_lp.append(str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['border_vtep_lp'] + num -1) + '/' + self.addr['lp_net'].split('/')[1])
            self.network_size['num_borders'] -= 1

    #     # 3d. Generate a list of MLAG loopbacks to be used by each border and leaf MLAG pair and BGW loopback only on borders
        num = 0
        while half_num_leafs != 0:
            num += 1
            # Adds the generated IP address for MLAG loopback twice as same IP used by both devices in MLAG pair
            self.mlag_lp.append(str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['leaf_mlag_lp'] + num -1) + '/' + self.addr['lp_net'].split('/')[1])
            self.mlag_lp.append(str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['leaf_mlag_lp'] + num -1) + '/' + self.addr['lp_net'].split('/')[1])
            half_num_leafs-= 1
        num = 0
        while half_num_borders != 0:
            num += 1
            self.mlag_lp.append(str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['border_mlag_lp'] + num -1) + '/' + self.addr['lp_net'].split('/')[1])
            self.mlag_lp.append(str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['border_mlag_lp'] + num -1)+ '/' + self.addr['lp_net'].split('/')[1])
            # Adds the generated IP address for the BGW loopback twice as same IP used by both devices in MLAG pair
            self.bgw_lp.append(str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['border_bgw_lp'] + num -1) + '/' + self.addr['lp_net'].split('/')[1])
            self.bgw_lp.append(str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['border_bgw_lp'] + num -1) + '/' + self.addr['lp_net'].split('/')[1])
            half_num_borders -= 1


        # Create MLAG interface IP address
        self.mlag_peer = {}
        for dev in self.leaf + self.border:
            if self.device_name['leaf'] in dev:
                self.mlag_peer[dev] = str(ip_network(self.addr['mlag_net'], strict=False)[int(dev[-2:]) + self.addr_incre['mlag_leaf_ip'] -1]) + '/31'
            else:
                self.mlag_peer[dev] = str(ip_network(self.addr['mlag_net'], strict=False)[int(dev[-2:]) + self.addr_incre['mlag_border_ip'] -1]) + '/31'


    def create_interfaces(self):
        # 4. For the underlay uplinks creates nested dicts with key the device_name and value being another dictionary of {interface:description}
        self.all_int = defaultdict(dict)
        self.mlag_int = defaultdict(dict)

        # 4a. Create nested dictionary for spine interfaces
        for sp in self.spine:
            for lf_num in range(self.skip_lf):
                # Description uses loop increment to get remote device number and spine name and interface increment to get remote device port
                descr = 'UPLINK > ' + self.device_name['leaf'] + "{:02d} ".format(lf_num +1) + self.bse_intf['intf_fmt'][:3] + self.bse_intf['intf_fmt'][-2:] + "{:01d}".format(int(sp[-2:]) + self.bse_intf['lf_to_sp'] -1)
                # Interface number got from the starting interface increment (sp_to_lf) and the loop interation (lf_num)
                self.all_int[sp][self.bse_intf['intf_fmt'] + (str(self.bse_intf['sp_to_lf'] + lf_num))] = descr
            for lf_num in range(self.skip_bdr):
                descr = 'UPLINK > ' + self.device_name['border'] + "{:02d} ".format(lf_num +1) + self.bse_intf['intf_fmt'][:3] + self.bse_intf['intf_fmt'][-2:] + "{:01d}".format(int(sp[-2:]) + self.bse_intf['bdr_to_sp'] -1)
                self.all_int[sp][self.bse_intf['intf_fmt'] + (str(self.bse_intf['sp_to_bdr'] + lf_num))] = descr

        # 4b. Create nested dictionary for leaf interfaces
        for lf in self.leaf:
            for sp_num in range(self.skip_sp):
                descr = 'UPLINK > ' + self.device_name['spine'] + "{:02d} ".format(sp_num +1) + self.bse_intf['intf_fmt'][:3] + self.bse_intf['intf_fmt'][-2:] + "{:01d}".format(int(lf[-2:]) + self.bse_intf['sp_to_lf'] -1)
                self.all_int[lf][self.bse_intf['intf_fmt'] + (str(self.bse_intf['lf_to_sp'] + sp_num))] = descr

        # 4c. Create nested dictionary for border interfaces
        for bdr in self.border:
            for sp_num in range(self.skip_sp):
                descr = 'UPLINK > ' + self.device_name['spine'] + "{:02d} ".format(sp_num +1) + self.bse_intf['intf_fmt'][:3] + self.bse_intf['intf_fmt'][-2:] + "{:01d}".format(int(bdr[-2:]) + self.bse_intf['sp_to_bdr'] -1)
                self.all_int[bdr][self.bse_intf['intf_fmt'] + (str(self.bse_intf['bdr_to_sp'] + sp_num))] = descr

        # 4d. Create nested dictionary for border and leaf MLAG interfaces
        mlag_ports = [self.bse_intf['intf_fmt'] + self.bse_intf['mlag_peer'].split('-')[0], self.bse_intf['intf_fmt'] +
                      self.bse_intf['mlag_peer'].split('-')[1], self.bse_intf['ec_fmt'] + str(self.mlag['peer_po'])]
        for dev in self.leaf + self.border:
            for port in mlag_ports:
                if self.bse_intf['intf_fmt'] in port:
                    if int(dev[-2:]) % 2 != 0:        # If device_name ends in an odd number
                        self.mlag_int[dev][port] = 'MLAG peer-link > ' + dev[:-2] + "{:02d} ".format(int(dev[-2:]) +1) + port[:3] + port[len(self.bse_intf['intf_fmt']) -2:]
                    else:                           # If device_name ends in an even number
                        self.mlag_int[dev][port] = 'MLAG peer-link > ' + dev[:-2] + "{:02d} ".format(int(dev[-2:]) -1) + port[:3] + port[len(self.bse_intf['intf_fmt']) -2:]
                else:           # Different description for port-channel
                    if int(dev[-2:]) % 2 != 0:
                        self.mlag_int[dev][port] = 'MLAG peer-link > ' + dev[:-2] + "{:02d} ".format(int(dev[-2:]) +1) + port[:2] + str(self.mlag['peer_po'])
                    else:
                        self.mlag_int[dev][port] = 'MLAG peer-link > ' + dev[:-2] + "{:02d} ".format(int(dev[-2:]) -1) + port[:2] + str(self.mlag['peer_po'])


# {# For border devices using peer_incre creates /31 peer-link IPs based in hostname number #}
# {% if device_name.border_name in inventory_hostname %}
#   ip address {{ addressing.vpc_peer_subnet |ipaddr('network') |ipmath(inventory_hostname[-2:]|int+address_incre.vpc_border_ip) }}/31
# {# For leaf devices using peer_incre creates /31 peer-link IPs based in hostname number #}
# {% elif device_name.leaf_name in inventory_hostname %}
#   ip address {{ addressing.vpc_peer_subnet |ipaddr('network') |ipmath(inventory_hostname[-2:]|int+address_incre.vpc_leaf_ip) }}/31





        # for x in self.all_int:
        #     print(x)
        # pprint(self.all_int)




# ============================ Create the inventory ==========================
# 4. Adds groups, hosts and variables to create the inventory file
    def create_inventory(self):
        # Creates list of groups created from the device names
        groups = [self.device_name['spine'].split('-')[-1].lower(), self.device_name['border'].split('-')[-1].lower(),
                  self.device_name['leaf'].split('-')[-1].lower()]

        for gr in groups:
            # Creates all the group, they are automatically added to the 'all' group
            self.inventory.add_group(gr)
            # Creates the host entries, os and mlag_lp_addr host_var (although assigned to group in the cmd)
            if gr == 'spine':
                for sp in self.spine:
                    self.inventory.add_host(sp, gr)
                    self.inventory.set_variable(gr, 'os', self.device_type['spine_os'])
            if gr == 'border':
                for br in self.border:
                    self.inventory.add_host(br, gr)
                    self.inventory.set_variable(gr, 'os', self.device_type['border_os'])

            if gr == 'leaf':
                for lf in self.leaf:
                    self.inventory.add_host(lf, gr)
                    self.inventory.set_variable(gr, 'os', self.device_type['leaf_os'])

        # Adds the mgmt as host_vars for all devices by using zip to iterate through 3 lists simultaneously
        for host, mgmt, rtr_lp in zip((self.spine + self.leaf + self.border), self.mgmt_ip, self.rtr_lp):
            self.inventory.set_variable(host, 'ansible_host', mgmt)

        # SPINE: Adds RTR loopback address in nested dictionary called lp
        for host, rtr_lp in zip(self.spine, self.rtr_lp):
            self.inventory.set_variable(host, 'intf_lp', {list(self.lp['rtr'].keys())[0]: {rtr_lp: list(self.lp['rtr'].values())[0]}})

        # LEAF: Adds the RTR, VTEP and MLAG loopback address (secondary IP) to lp nested host_var on leafss. Loop index starts past spine lps
        for host, rtr_lp, vtep_lp, mlag_lp, in zip(self.leaf, self.rtr_lp[self.skip_sp:], self.vtep_lp, self.mlag_lp):
            self.inventory.set_variable(host, 'intf_lp', {list(self.lp['rtr'].keys())[0]: {rtr_lp: list(self.lp['rtr'].values())[0]},
                                                     list(self.lp['vtep'].keys())[0]: {vtep_lp: list(self.lp['vtep'].values())[0],
                                                                                       'mlag_lp_addr': mlag_lp}})

        # BORDER: Adds the RTR, VTEP, MLAG, BGW loopback address (secondary IP) to lp nested host_var on borders. Loop index starts past spine and leaf lps
        for host, rtr_lp, vtep_lp, mlag_lp, bgw_lp in zip(self.border , self.rtr_lp[self.skip_sp_lf:], self.vtep_lp[self.skip_lf:], self.mlag_lp[self.skip_lf:], self.bgw_lp):
            self.inventory.set_variable(host, 'intf_lp', {list(self.lp['rtr'].keys())[0]: {rtr_lp: list(self.lp['rtr'].values())[0]},
                                                     list(self.lp['vtep'].keys())[0]: {vtep_lp: list(self.lp['vtep'].values())[0],
                                                                                       'mlag_lp_addr': mlag_lp},
                                                     list(self.lp['bgw'].keys())[0]: {bgw_lp: list(self.lp['bgw'].values())[0]}})

        # Adds the fabric interfaces
        for host, int_details in self.all_int.items():
            self.inventory.set_variable(host, 'intf_fbc', int_details)

        # Adds the MLAG interfaces
        for host, int_details in self.mlag_int.items():
            self.inventory.set_variable(host, 'intf_mlag', int_details)

       # Adds the MLAG Peer IP
        for host, int_details in self.mlag_peer.items():
            self.inventory.set_variable(host, 'mlag_peer_ip', int_details)

# ============================ Parse data from config file ==========================
# !!!! The parse method is always auto-run, so is what starts the plugin and runs any custom methods !!!!

    # 2. This Ansible pre-defined method pulls the data from the config file and creates variables for it.
    def parse(self, inventory, loader, path, cache=False):
        # `Inherited methods: inventory creates inv, loader loads vars from cfg file and path is path to cfg file
        super(InventoryModule, self).parse(inventory, loader, path)

        # 2a. Read the data from the config file and create variables. !!! The options MUST be defined in documentation options section !!!
        self._read_config_data(path)
        var_files = self.get_option('var_files')           # List of the Ansible varaible files (in vars)
        var_dicts = self.get_option('var_dicts')           # Names of the dictionaries that will be got from these files

        # 2b. Loads the yaml file to makes a dictionary of dictionaires holding contents of all files in format file_name:file_contents
        all_vars = {}
        mydir = os.getcwd()                 # Gets current directory
        for dict_name, file_name in zip(var_dicts.keys(), var_files):
            with open(os.path.join(mydir, 'vars/') + file_name, 'r') as file_content:
                all_vars[dict_name] = yaml.load(file_content, Loader=yaml.FullLoader)

        # 2c. Create new variables of only those needed from the dict of all variables created from yaml files in last step (all_vars)
        # As it loops through list in cfg file is easy to add more variables in the future
        for file_name, var_names in var_dicts.items():
            for each_var in var_names:
                if each_var == 'device_name':
                    self.device_name = all_vars[file_name]['bse'][each_var]
                elif each_var == 'device_type':
                    self.device_type = all_vars[file_name]['ans'][each_var]
                elif each_var == 'addr_incre':
                    self.addr_incre = all_vars[file_name]['fbc']['adv'][each_var]
                elif each_var == 'addr':
                    self.addr = all_vars[file_name]['bse'][each_var]
                elif each_var == 'network_size':
                    self.network_size = all_vars[file_name]['fbc'][each_var]
                elif each_var == 'lp':
                    self.lp = all_vars[file_name]['fbc']['adv'][each_var]
                elif each_var == 'bse_intf':
                    self.bse_intf = all_vars[file_name]['fbc']['adv'][each_var]
                elif each_var == 'mlag':
                    self.mlag = all_vars[file_name]['fbc']['adv'][each_var]
        self.create_objects()           # Run the method to turn the data model into inventory objects
        self.create_interfaces()
        self.create_inventory()         # Run the method to to create the inventory
   # Example ways to test variable format is correct before running other methods
        # test = self.addr['lp_net']
        # test = config.get('device_name')[0]['spine']
        # self.inventory.add_host(test)

    # To use error handling within the plugin use this format
        # try:
        #     cause_an_exception()
        # except Exception as e:
        #     raise AnsibleError('Something happened, this was original exception: %s' % to_native(e))



