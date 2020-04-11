from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

# ============================== Documentation ============================
# options match get_options (in section that parses) and are actually the configuration (i.e. type, required, default)

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
# What users see as a way of instructions on how to run the plugin
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
    - device_name                       # Naming format for each host
    - addr                              # Address ranges the devices IPs are created from. Loopback must be /32
  fabric:
    - network_size                      # Dictates number of inventory objects created for each device role
    - bse_intf                          # Naming and increments for the fabric interfaces
    - lp                                # Loopback interface naming and descriptions
    - mlag                              # Holds the peer link Port-Channel number
    - addr_incre                        # Network address increment used for each device role (group)
'''

# ==================================== Plugin ==================================
# Modules used to format date ready for creating the inventory
import os
import yaml
from ipaddress import ip_network
from collections import defaultdict
# Ansible modules required for the features of the inventory plugin
from ansible.errors import AnsibleParserError
from ansible.module_utils._text import to_native, to_text
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable, Cacheable

# Ansible Inventory plugin class that holds pre-built methods that run automatically (verify_file, parse) without needing to be called
class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    NAME = 'inv_from_vars'                  # Should match name of the plugin

# ==================================== 1. Verify config file ==================================
# 1. Makes a quick determination whether the inventory source config file is usable by the plugin
    def verify_file(self, path):
        valid = False
        if super(InventoryModule, self).verify_file(path):
            if path.endswith(('inv_from_vars_cfg.yaml', 'inv_from_vars_cfg.yml')):
                valid = True
        return valid

# ============================ 3. Generate all the device specific IP interface addresses  ==========================
# #3. Generates the hostname and IP addresses to be used to create the inventory using data model from config file
    def create_ip(self):
        self.all_lp, self.all_mgmt, self.mlag_peer = ({} for i in range(3))
        self.spine, self.border, self.leaf = ([] for i in range(3))

        # Create new network size variabels as will be decreasing the value
        num_sp = self.network_size['num_spines']
        num_lf = self.network_size['num_leafs']
        num_bdr = self.network_size['num_borders']

        # 3a. SPINE: Generates name, management and Loopback IP (rtr) and adds to self.all_x dictionaries (spine_name is the key)
        incr_num = 0
        while num_sp != 0:
            incr_num += 1                    # Increments by 1 for each device
            # Creates the spine name using the incremented (double-decimal format)
            self.spine.append(self.device_name['spine'] + str("%02d" % incr_num))
            # Creates the mgmt IP by adding the num_incr and device_ip_incr to the the network address ({sp_name: mgmt_ip})
            self.all_mgmt[self.spine[incr_num -1]] = str(ip_network(self.addr['mgmt_net'], strict=False)[self.addr_incre['spine_ip'] + incr_num -1])
            # Creates the RTR loopback by adding the num_incr and device_ip_incr to the the network address and then adding subnet and adds to dict
            rtr_ip = str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['spine_ip'] + incr_num -1) + '/' + self.addr['lp_net'].split('/')[1]
            # Creates dict in format sp_name: [{name:lp, ip:lp_ip, descr:lp_descr}) used in next method to create the inventory
            self.all_lp[self.spine[incr_num -1]] = [{'name': list(self.lp['rtr'].keys())[0], 'ip': rtr_ip, 'descr': list(self.lp['rtr'].values())[0]}]
            num_sp -= 1        # Reduces number of spines each iteration

        # 3b. LEAF: Generates name, management, Loopback IPs (rtr, vtep, mlag), mlag peer IP and adds to self.all_x dictionaries (leaf_name is the key)
        incr_num, odd_incr_num = (0 for i in range(2))
        while num_lf != 0:
            incr_num += 1
            self.leaf.append(self.device_name['leaf'] + str("%02d" % incr_num))
            # If device_name ends in an odd number makes one MLAG (loopback secondary) IP as is shared between a VPC pair
            if int(self.leaf[incr_num -1][-2:]) % 2 != 0:
                odd_incr_num += 1
                mlag_ip = str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['leaf_mlag_lp'] + odd_incr_num -1) + '/' + self.addr['lp_net'].split('/')[1]
            self.all_mgmt[self.leaf[incr_num -1]] = str(ip_network(self.addr['mgmt_net'], strict=False)[self.addr_incre['leaf_ip'] + incr_num -1])
            rtr_ip = str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['leaf_ip'] + incr_num - 1) + '/' + self.addr['lp_net'].split('/')[1]
            vtep_ip = str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['leaf_vtep_lp'] + incr_num -1) + '/' + self.addr['lp_net'].split('/')[1]
            self.all_lp[self.leaf[incr_num -1]] = [{'name': list(self.lp['rtr'].keys())[0], 'ip': rtr_ip, 'descr': list(self.lp['rtr'].values())[0]},
                                                   {'name': list(self.lp['vtep'].keys())[0], 'ip': vtep_ip, 'descr': list(self.lp['vtep'].values())[0],
                                                   'mlag_lp_addr': mlag_ip}]
            # Generates MLAG peer IP and adds to dictionary
            self.mlag_peer[self.leaf[incr_num -1]] = str(ip_network(self.addr['mlag_net'], strict=False)[int(self.leaf[incr_num -1][-2:]) +
                                                                    self.addr_incre['mlag_leaf_ip'] -1]) + '/31'
            num_lf -= 1

       # 3c. BORDER: Generates name, management and Loopback IPs (rtr, vtep, mlag, bgw) and adds to self.all_x dictionaries (border_name is the key)
        incr_num, odd_incr_num = (0 for i in range(2))
        while num_bdr != 0:
            incr_num += 1
            self.border.append(self.device_name['border'] + str("%02d" % incr_num))
            if int(self.border[incr_num -1][-2:]) % 2 != 0:
                odd_incr_num += 1
                mlag_ip = str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['border_mlag_lp'] + odd_incr_num -1) + '/' + self.addr['lp_net'].split('/')[1]
                bgw_ip = str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['border_bgw_lp'] + odd_incr_num -1) + '/' + self.addr['lp_net'].split('/')[1]
            self.all_mgmt[self.border[incr_num -1]] = str(ip_network(self.addr['mgmt_net'], strict=False)[self.addr_incre['border_ip'] + incr_num -1])
            rtr_ip = str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['border_ip'] + incr_num - 1) + '/' + self.addr['lp_net'].split('/')[1]
            vtep_ip = str(ip_network(self.addr['lp_net'])[0] + self.addr_incre['border_vtep_lp'] + incr_num - 1) + '/' + self.addr['lp_net'].split('/')[1]
            self.all_lp[self.border[incr_num -1]] = [{'name': list(self.lp['rtr'].keys())[0], 'ip': rtr_ip, 'descr': list(self.lp['rtr'].values())[0]},
                                                {'name': list(self.lp['vtep'].keys())[0], 'ip': vtep_ip, 'descr': list(self.lp['vtep'].values())[0],
                                                'mlag_lp_addr': mlag_ip},
                                                {'name': list(self.lp['bgw'].keys())[0], 'ip': bgw_ip, 'descr': list(self.lp['bgw'].values())[0]}]
            self.mlag_peer[self.border[incr_num -1]] = str(ip_network(self.addr['mlag_net'], strict=False)[int(self.border[incr_num -1][-2:]) +
                                                                      self.addr_incre['mlag_border_ip'] -1]) + '/31'
            num_bdr -= 1


# ============================ 4. Generate all the fabric interfaces  ==========================
# 4. For the uplinks (doesnt include iPs) creates nested dicts with key the device_name and value a dict {sp_name: {intf_num: descr}, {intf_num: descr}}
    def create_intf(self):
        self.all_int, self.mlag_int, mlag_ports = (defaultdict(dict) for i in range(3))

        # 4a. SPINE: Create nested dictionary of the devices fabric interfaces based on number of leaf and border switches
        for sp in self.spine:
            for lf_num in range(self.network_size['num_leafs']):
                # Loops through the number of leafs using the increment to create the remote device name
                dev_name = 'UPLINK > ' + self.device_name['leaf'] + "{:02d} ".format(lf_num +1)
                # Creates remote device port using spine number and the leaf_to_spine interfcae increment
                dev_int = self.bse_intf['intf_short'] + "{:01d}".format(int(sp[-2:]) + self.bse_intf['lf_to_sp'] -1)
                # Interface number got from the starting interface increment (sp_to_lf) and the loop interation (lf_num)
                self.all_int[sp][self.bse_intf['intf_fmt'] + (str(self.bse_intf['sp_to_lf'] + lf_num))] = dev_name + dev_int
            for bdr_num in range(self.network_size['num_borders']):
                dev_name = 'UPLINK > ' + self.device_name['border'] + "{:02d} ".format(bdr_num +1)
                dev_int = self.bse_intf['intf_short'] + "{:01d}".format(int(sp[-2:]) + self.bse_intf['bdr_to_sp'] -1)
                self.all_int[sp][self.bse_intf['intf_fmt'] + (str(self.bse_intf['sp_to_bdr'] + bdr_num))] = dev_name + dev_int

        # 4b. LEAF: Create nested dictionary of the devices fabric interfaces based on the number of spine switches
        for lf in self.leaf:
            for sp_num in range(self.network_size['num_spines']):
                dev_name = 'UPLINK > ' + self.device_name['spine'] + "{:02d} ".format(sp_num +1)
                dev_int = self.bse_intf['intf_short'] + "{:01d}".format(int(lf[-2:]) + self.bse_intf['sp_to_lf'] -1)
                self.all_int[lf][self.bse_intf['intf_fmt'] + (str(self.bse_intf['lf_to_sp'] + sp_num))] = dev_name + dev_int

        # 4c. BORDER: Create nested dictionary of the devices fabric interfaces based on the number of spine switches
        for bdr in self.border:
            for sp_num in range(self.network_size['num_spines']):
                dev_name = 'UPLINK > ' + self.device_name['spine'] + "{:02d} ".format(sp_num +1)
                dev_int = self.bse_intf['intf_short'] + "{:01d}".format(int(bdr[-2:]) + self.bse_intf['sp_to_bdr'] -1)
                self.all_int[bdr][self.bse_intf['intf_fmt'] + (str(self.bse_intf['bdr_to_sp'] + sp_num))] = dev_name + dev_int

        # 4d. BORDER, LEAF: Create nested dictionary for border and leaf MLAG interfaces
        # Create a list of dictionaries of all MLAG ports and their short names for the description [{int_name: short_int_name}]
        for intf_num in self.bse_intf['mlag_peer'].split('-'):
            mlag_ports[self.bse_intf['intf_fmt'] + intf_num] = self.bse_intf['intf_short'] + intf_num
        mlag_ports[self.bse_intf['ec_fmt'] + str(self.mlag['peer_po'])] = self.bse_intf['ec_short'] + str(self.mlag['peer_po'])

        for dev in self.leaf + self.border:
            for intf, intf_short in mlag_ports.items():
                # If device_name ends in an odd number increment the device_name by 1
                if int(dev[-2:]) % 2 != 0:
                    self.mlag_int[dev][intf] = 'MLAG peer-link > ' + dev[:-2] + "{:02d} ".format(int(dev[-2:]) +1) + intf_short
                # If device_name ends in an even number decreases the device_name by 1
                else:                           # If device_name ends in an even number
                    self.mlag_int[dev][intf] = 'MLAG peer-link > ' + dev[:-2] + "{:02d} ".format(int(dev[-2:]) -1) + intf_short


# ============================ 5. Create the inventory ==========================
# 5. Adds groups, hosts and host_vars to create the inventory file
    def create_inventory(self):
        # Creates list of groups created from the device names
        groups = [self.device_name['spine'].split('-')[-1].lower(), self.device_name['border'].split('-')[-1].lower(),
                  self.device_name['leaf'].split('-')[-1].lower()]

        #5a. Creates all the group, they are automatically added to the 'all' group
        for gr in groups:
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

        #5b. Adds host_vars for all the IP dictionaries created in 'create_ip' method
        for host, mgmt_ip in self.all_mgmt.items():
            self.inventory.set_variable(host, 'ansible_host', mgmt_ip)
        for host, lp in self.all_lp.items():
            self.inventory.set_variable(host, 'intf_lp', lp)
        for host, mlag_peer in self.mlag_peer.items():
            self.inventory.set_variable(host, 'mlag_peer_ip', mlag_peer)

        #5c. Adds host_vars for all the Interface dictionaries created in 'create_intf' method
        for host, int_details in self.all_int.items():
            self.inventory.set_variable(host, 'intf_fbc', int_details)
        for host, int_details in self.mlag_int.items():
            self.inventory.set_variable(host, 'intf_mlag', int_details)


# ============================ 2. Parse data from config file ==========================
# !!!! The parse method is always auto-run, so is what starts the plugin and runs any custom methods !!!!

# 2. This Ansible pre-defined method pulls the data from the config file and creates variables for it.
    def parse(self, inventory, loader, path, cache=False):
        # `Inherited methods: inventory creates inv, loader loads vars from cfg file and path is path to cfg file
        super(InventoryModule, self).parse(inventory, loader, path)

        # 2a. Read the data from the config file and create variables. !!! The options MUST be defined in DOCUMENTATION options section !!!
        self._read_config_data(path)
        var_files = self.get_option('var_files')           # List of the Ansible varaible files (in vars)
        var_dicts = self.get_option('var_dicts')           # Names of the dictionaries that will be got from these files

        # 2b. Loads the yaml file to makes a dictionary of dictionaires holding contents of all files in format {file_name:file_contents}
        all_vars = {}
        mydir = os.getcwd()                 # Gets current directory
        for dict_name, file_name in zip(var_dicts.keys(), var_files):
            with open(os.path.join(mydir, 'vars/') + file_name, 'r') as file_content:
                all_vars[dict_name] = yaml.load(file_content, Loader=yaml.FullLoader)

        # 2c. Create new variables of only those needed from the dict created in the last step (all_vars)
        # As it loops through list in cfg file is easy to add more variables in the future
        for file_name, var_names in var_dicts.items():
            for each_var in var_names:
                if each_var == 'device_type':
                    self.device_type = all_vars[file_name]['ans'][each_var]
                elif each_var == 'device_name':
                    self.device_name = all_vars[file_name]['bse'][each_var]
                elif each_var == 'addr':
                    self.addr = all_vars[file_name]['bse'][each_var]
                elif each_var == 'network_size':
                    self.network_size = all_vars[file_name]['fbc'][each_var]
                elif each_var == 'bse_intf':
                    self.bse_intf = all_vars[file_name]['fbc']['adv'][each_var]
                elif each_var == 'lp':
                    self.lp = all_vars[file_name]['fbc']['adv'][each_var]
                elif each_var == 'mlag':
                    self.mlag = all_vars[file_name]['fbc']['adv'][each_var]
                elif each_var == 'addr_incre':
                    self.addr_incre = all_vars[file_name]['fbc']['adv'][each_var]

        # 3. Creates a data model of the hostnames and device specific IP interface addresses
        self.create_ip()
        # 4. Creates a data model of all the fabric interfaces
        self.create_intf()
        # 5. Uses  the data models to create the inventory containing groups, hosts and host_vars
        self.create_inventory()

   # Example ways to test variable format is correct before running other methods
        # test = self.addr['lp_net']
        # test = config.get('device_name')[0]['spine']
        # self.inventory.add_host(test)

    # To use error handling within the plugin use this format
        # try:
        #     cause_an_exception()
        # except Exception as e:
        #     raise AnsibleError('Something happened, this was original exception: %s' % to_native(e))