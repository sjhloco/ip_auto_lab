from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

# ============================== Documentation ============================
# options match get_options and are actrually configuration (i.e. type, required, defalt)

DOCUMENTATION = '''
    name: leaf_spine
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
            choices: ['leaf_spine']
        network_size:
            description: Dictates the number of hosts created in the inventory
            required: True
            type: dict
        device_name:
            description: Format used to create the hostnames
            type: dict
            default: [{'spine_name': 'DC1-N9K-SPINE'}, {'border_name': 'DC1-N9K-BORDER'}, {'leaf_name': 'DC1-N9K-LEAF'}]
        device_type:
            description: Device type as used by NAPALM
            type: dict
            default: [{'spine_os': 'nxos'}, {'spine_os': 'nxos'}, {'spine_os': 'nxos'}]
        addressing:
            description: Subnets used to generate device specific IP addresses
            required: True
            type: dict
        address_incre:
            description: The increments used to make each device types IP unique
            type: dict
            default: [{'spine_ip': 10}, {'border_ip': 15}, {'leaf_ip': 20}]
'''
# What users see as away of instructions on how to run the plugin
EXAMPLES = '''
# leaf_spine_inventory.yml file in YAML format
# Example command line: ansible-inventory -v --list -i leaf_spine_inventory.yml
plugin: leaf_spine

# How many of each role of device are inventory entires created for
network_size:
  num_spines: 2
  num_borders: 2
  num_leafs: 4

# Naming format for each host
device_name:
  spine_name: DC1-N9K-SPINE
  border_name: DC1-N9K-BORDER
  leaf_name: DC1-N9K-LEAF

# Device type for each switch role (os)
device_type:
  spine_os: nxos
  border_os: nxos
  leaf_os: nxos

# Address ranges devices IPs are created from
addressing:
  mgmt_ip_subnet: '10.10.108.0/24'
  lo_ip_subnet: '192.168.100.0/32'

# Network address increment used for each device role
address_incre:
  spine_ip: 10
  border_ip: 15
  leaf_ip: 20
'''


# ==================================== Plugin ==================================
# Modules used to format date ready for creating the inventory
from ipaddress import ip_network
# Ansible modules required for the features of the inventory plugin
from ansible.errors import AnsibleParserError
from ansible.module_utils._text import to_native, to_text
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable, Cacheable

# Ansible Inventory plugin class that holds pre-built methods that run automatically (verify_file, parse) without needing to be called
class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    NAME = 'leaf_spine'     # Should match name of the plugin


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
        self.hosts_lp =[]

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


# ============================ Create the inventory ==========================
# 4. Adds groups, hosts and varaibles to create the inventory file
    def create_inventory(self):

        # Creates list of groups created from the device names
        self.groups = [self.device_name['spine_name'].split('-')[-1].lower(), self.device_name['border_name'].split('-')[-1].lower(),
                  self.device_name['leaf_name'].split('-')[-1].lower()]

        for gr in self.groups:
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

        self.host_names = self.spine + self.border + self.leaf       # Create a new list of all hosts (names)
        # Adds the mgmt and lp address as host_vars by using zip to iterate through 3 lists simultaneousl
        for host, mgmt, lp in zip(self.host_names, self.hosts_mgmt, self.hosts_lp):
            self.inventory.set_variable(host, 'ansible_host', mgmt)
            self.inventory.set_variable(host, 'lp_addr', lp)


# ============================ Parse data from config file ==========================
# !!!! The parse method is always auto-run, so is what starts the plugin and runs any custom methods !!!!

    # 2. Pull the data from the config file and create variables for them.
    def parse(self, inventory, loader, path, cache=False):
        # super is normally the args that will be used when running parent meths, what does parse do????????????
        super(InventoryModule, self).parse(inventory, loader, path)     # args come from Ansible class

    # !!!!! ARE 2 ways to do this, not sure if either is better than the other so did both but use onyl 1 !!!!!!
    # Opt1. Read all the data and create variables on the fly with get_option(). !!! Options MUST be defined in documentation options section !!!
        self._read_config_data(path)
        self.network_size = self.get_option('network_size')         # Creates a variable for each dictionary from the data model
        self.device_name = self.get_option('device_name')
        self.device_type = self.get_option('device_type')
        self.addressing = self.get_option('addressing')
        self.address_incre = self.get_option('address_incre')

    # Opt2. Read all the data into a variable and then use get() to create varaibles for each part of the data model
        # data = self._read_config_data(path)                   # Puts all the config options into a long dictionary
        # self.network_size = data.get('network_size')          # Creates a variable for each dictionary from the data model
        # self.device_name = data.get('device_name')
        # self.device_type = data.get('device_type')
        # self.addressing = data.get('addressing')
        # self.address_incre = data.get('address_incre')

        self.create_objects()       # Run the method to turn the data model into inventory objects
        self.create_inventory()     # Run the method to to create the inventory

        # Use test variables created from the data model or formatting to get elements from the dictionaries
        #test = self.addressing['lp_ip_subnet']
        #test = config.get('device_name')[0]['spine_name']
        #self.inventory.add_host(test)


    # To use error handling within the plugin use this format
        # try:
        #     cause_an_exception()
        # except Exception as e:
        #     raise AnsibleError('Something happened, this was original exception: %s' % to_native(e))







