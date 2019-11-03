from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

# ============================== Documentation ============================
# options match get_options and are actrually configuration (i.e. type, required, defalt)

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
            description: Data-model in Ansible vars directory where dictionaries will imported from
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
  - default.yml
  - base.yml
  - fabric.yml

# Dictionaries that wil be imported from the data-model
var_dicts:
  ansible:
    - device_type                   # Device type (os) for each switch type (group)
  base:
    - device_name                   # Naming format for each host
    - addressing                    # Address ranges the devices IPs are created from. Loopback must be /32
  fabric:
    - network_size                  # Dictates number of inventory objects created for each device role
    - address_incre                 # Network address increment used for each device role (group)
'''

# ==================================== Plugin ==================================
# Modules used to format date ready for creating the inventory
import os
import yaml
from ipaddress import ip_network
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
    #3. Generates the objects to be used to create the inventory using data mdoel from config file
    def create_objects(self):
        self.spine = []
        self.border = []
        self.leaf = []
        self.hosts_mgmt = []
        self.hosts_lp = []
        self.hosts_sec_lp = []

        # Halfs the the number of border and leaf switches which is used to create secondary loopback IP
        half_num_borders = self.network_size['num_borders'] /2
        half_num_leafs = self.network_size['num_leafs'] /2

        # 3a. Generate a lists of Spine switches, the management IPs and Loopback IPs
        num = 0
        while self.network_size['num_spines'] != 0:
            num += 1            # Increments by 1 for each device
            # Creates the name using the incremented (double-decimal format)
            self.spine.append(self.device_name['spine_name'] + str("%02d" % num))
            # Creates the mgmt IP by adding the incr and device_ip_incr to the the network address
            self.hosts_mgmt.append(str(ip_network(self.addressing['mgmt_ip_subnet'], strict=False)[self.address_incre['spine_ip'] + num]))
            # Creates the loopback IP by adding the incr and device_ip_incr
            self.hosts_lp.append(str(ip_network(self.addressing['lp_ip_subnet'])[0] + self.address_incre['spine_ip'] + num))
            self.network_size['num_spines'] -= 1        # Reduces number of spines each iteration

       # 3b. Generate a lists of border switches and adds management IPs and Loopback IPs to existing list
        num = 0
        while self.network_size['num_borders'] != 0:
            num += 1
            self.border.append(self.device_name['border_name'] + str("%02d" % num))
            self.hosts_mgmt.append(str(ip_network(self.addressing['mgmt_ip_subnet'], strict=False)[self.address_incre['border_ip'] + num]))
            self.hosts_lp.append(str(ip_network(self.addressing['lp_ip_subnet'])[0] + self.address_incre['border_ip'] + num))
            self.network_size['num_borders'] -= 1

       # 3b. Generate a lists of leaf switches and adds management IPs and Loopback IPs to existing list
        num = 0
        while self.network_size['num_leafs'] != 0:
            num += 1
            self.leaf.append(self.device_name['leaf_name'] + str("%02d" % num))
            self.hosts_mgmt.append(str(ip_network(self.addressing['mgmt_ip_subnet'], strict=False)[self.address_incre['leaf_ip'] + num]))
            self.hosts_lp.append(str(ip_network(self.addressing['lp_ip_subnet'])[0] + self.address_incre['leaf_ip'] + num))
            self.network_size['num_leafs'] -= 1

        # 2d. Generate a list of secondary loopbacks to be used by each border and leaf VPC pair
        num = 0
        while half_num_borders != 0:
            num += 1
            # Adds the generated IP address twice as same IP used by both devices in VPC pair
            self.hosts_sec_lp.append(str(ip_network(self.addressing['lp_ip_subnet'])[0] + self.address_incre['sec_border_lp'] + num))
            self.hosts_sec_lp.append(str(ip_network(self.addressing['lp_ip_subnet'])[0] + self.address_incre['sec_border_lp'] + num))
            half_num_borders -= 1
        num = 0
        while half_num_leafs != 0:
            num += 1
            self.hosts_sec_lp.append(str(ip_network(self.addressing['lp_ip_subnet'])[0] + self.address_incre['sec_leaf_lp'] + num))
            self.hosts_sec_lp.append(str(ip_network(self.addressing['lp_ip_subnet'])[0] + self.address_incre['sec_leaf_lp'] + num))
            half_num_leafs-= 1

# ============================ Create the inventory ==========================
# 4. Adds groups, hosts and varaibles to create the inventory file
    def create_inventory(self):

        # Creates list of groups created from the device names
        groups = [self.device_name['spine_name'].split('-')[-1].lower(), self.device_name['border_name'].split('-')[-1].lower(),
                  self.device_name['leaf_name'].split('-')[-1].lower()]

        for gr in groups:
            # Creates all the group, they are automatically added to the 'all' group
            self.inventory.add_group(gr)
            # Creates the host entries and the os host_var (although assigned to group in the cmd)
            if gr == 'spine':
                for sp in self.spine:
                    self.inventory.add_host(sp, gr)
                    self.inventory.set_variable(gr, 'os', self.device_type['spine_os'])
            if gr == 'border':
                for sp in self.border:
                    self.inventory.add_host(sp, gr)
                    self.inventory.set_variable(gr, 'os', self.device_type['border_os'])
            if gr == 'leaf':
                for sp in self.leaf:
                    self.inventory.add_host(sp, gr)
                    self.inventory.set_variable(gr, 'os', self.device_type['leaf_os'])

        host_names = self.spine + self.border + self.leaf       # Create a new list of all hosts (names)
        # Adds the mgmt and lp address as host_vars by using zip to iterate through 3 lists simultaneously
        for host, mgmt, lp in zip(host_names, self.hosts_mgmt, self.hosts_lp):
            self.inventory.set_variable(host, 'ansible_host', mgmt)
            self.inventory.set_variable(host, 'lp_addr', lp)

        # Adds the secondary loopback address variable to border and leaf switches
        sec_hostnames = self.border + self.leaf       # list of just border and leafs
        for host, sec_lp in zip(sec_hostnames, self.hosts_sec_lp):
            self.inventory.set_variable(host, 'sec_lp_addr', sec_lp)

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

        # 2b. Makes a dictionary of dictionaires holding contents of all files in format file_name:file_contents
        all_vars = {}
        mydir = os.getcwd()                 # Gets current directory
        for name, file in zip(var_dicts.keys(), var_files):
            with open(os.path.join(mydir, 'vars/') + file, 'r') as file_content:
                all_vars[name] = yaml.load(file_content, Loader=yaml.FullLoader)

        # 2c. Make the content more managable by splitting it up into file_name:dict_var nested dictionaries
        # As it loops through list in cfg file is easy to add more variables in the future
        for file_name, var_names in var_dicts.items():
            for each_var in var_names:
                if each_var == 'device_name':
                    self.device_name = all_vars[file_name][each_var]
                elif each_var == 'device_type':
                    self.device_type = all_vars[file_name][each_var]
                elif each_var == 'address_incre':
                    self.address_incre = all_vars[file_name][each_var]
                elif each_var == 'addressing':
                    self.addressing = all_vars[file_name][each_var]
                elif each_var == 'network_size':
                    self.network_size = all_vars[file_name][each_var]

        self.create_objects()       # Run the method to turn the data model into inventory objects
        self.create_inventory()     # Run the method to to create the inventory

   # Example ways to test varaible format is correct before runnign other methods
        #test = self.addressing['lp_ip_subnet']
        #test = config.get('device_name')[0]['spine_name']
        #self.inventory.add_host(test)

    # To use error handling within the plugin use this format
        # try:
        #     cause_an_exception()
        # except Exception as e:
        #     raise AnsibleError('Something happened, this was original exception: %s' % to_native(e))



