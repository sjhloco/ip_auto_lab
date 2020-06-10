"""Validates the input variables in the base, fabric and services files are of the correct
format to be able to run the playbook, build a fabric and apply the services.
A pass or fail is returned to the Ansible Assert module, if it fails the full output is also
returned for the failure message. The following methods check:

-base configuration variables using base.yml:
bse.device_name: Ensures that the device names used match the correct format as that is heavily used in inventory script logic
bse.addr: Ensures that the network addresses entered are valid networks (or IP for loopback) with the correct subnet mask

-core fabric configuration variables  using fabric.yml
fbc.network_size: Ensures the number of each type of device is within the limits and constraints
fbc.num_intf: Ensures is one number, then a comma and then upto 3 numbers
fbc.ospf: Ensures that the OSPF process is present and area in dotted decimal format
fbc.bgp.as_num: Ensures that the AS is present, cant make more specific incase is 2-byte or 4-byte ASNs
fbc.acast_gw_mac: Ensures the anycast virtual MAC is a valid mac address
fbc.adv.bse_intf: Ensures that the interface numbers are integrars
fbc.adv.lp: Ensures all the loopback names are unique, no duplicates
fbc.adv.mlag: Ensures all of MLAG paraemters are integers and VLANs within limit
fbc.adv.addr_incre: Ensures all of the IP address increment values used are integers and except for mlag peering are all unique

-tenants (VRFs, VNIs & VLANs) using services_tenant.yml
svc_tnt.tnt.tenant_name: Ensures all tenants have a name, are no restictions of what is in it
svc_tnt.tnt.l3_tenant: Ensures answer is boolean
svc_tnt.tnt.vlans: Ensures vlans are defined, must be at least one
svc_tnt.tnt.vlans.num: Ensures all VLANs are numbers and not conflicting
svc_tnt.tnt.vlans.name: Ensures all VLANs have a name, are no restrictions of what it is
svc_tnt.tnt.vlans.create_on_border: Ensures answer is boolean
svc_tnt.tnt.vlans.create_on_leaf: Ensures answer is boolean
svc_tnt.tnt.vlans.ipv4_bgp_redist: Ensures answer is boolean
svc_tnt.tnt.vlans.ip_addr: Ensures that the IP address is of the correct format
svc_tnt.tnt.vlans.num: Ensures all the VLAN numbers are unique, no duplicates
svc_tnt.adv.bse_vni): Ensures all values are integers
svc_tnt.adv.bgp.ipv4_redist_rm_name: Ensures that it contains both 'vrf' and 'as'

-Interfaces (single_homed, dual_homed & port-channels) using interfaces_tenant.yml
svc_intf.intf.homed: Ensures that single-homed or dual-homed dictionaries are not empty
svc_intf.intf.homed.intf_num: Ensures that intf_num is integrar (also added to a new list to check interface assignment)
svc_intf.intf.dual_homed.po_num: Ensures that po_num is integrar (also added to a new list to check interface assignment)
svc_intf.intf.homed.switch: Ensures that it is a valid hostname within the inventory and if dual-homed the hostname is odd numbered
svc_intf.intf.single_homed.ip_vlan: Ensures that the the IP address is in a valid IPv4 format
svc_intf.intf.homed.ip_vlan: Ensures all VLANs are integrers (numbers)
svc_intf.intf.homed.ip_vlan: Ensures that there are no whitespaces and each vlan is an integrer (number)
svc_intf.intf.single_homed.tenant: Ensures that the VRF exists on the switch that an interface in that VRF is being configured
svc_intf.intf.homed.ip_vlan: Ensures that the VLAN exists on the switch that an interface using that VLAN is being configured
svc_intf.adv.homed.first/last: Ensures that the reserved interface and Port-Channel ranges are integrers
svc_intf.intf.single_homed: Ensures are enough free ports in the range (range minus conflicting static assignments) for number of interfaces defined
svc_intf.intf.dual_homed: Ensures are enough free ports in the range (range minus conflicting static assignments) for number of interfaces defined
svc_intf.intf.dual_homed: Ensures are enough free port-channels in the range (range minus conflicting static assignments) for number of port-channels defined
-svc_intf.intf.homed: Make sure that are not more defined interfaces (single and dual_homed) than there are actual interfaces on the switch
"""

import re
import ipaddress
from collections import defaultdict


class FilterModule(object):
    def filters(self):
        return {
            'input_bse_validate': self.base,
            'input_fbc_validate': self.fabric,
            'input_svc_tnt_validate': self.svc_tnt,
            'input_svc_intf_validate': self.svc_intf
        }



############  Generic assert functions used by all classes to make it DRY ############
    # REGEX search matches the specified pattern anywhere within the string
    def assert_regex_search(self, errors, regex, input_string, error_message):
        try:
            assert re.search(regex, input_string), error_message
        except AssertionError as e:
            errors.append(str(e))
    # REGEX match matches the specified pattern at the beginning of the string
    def assert_regex_match(self, errors, regex, input_string, error_message):
        try:
            assert re.match(regex, input_string), error_message
        except AssertionError as e:
            errors.append(str(e))

    # =! asserts that the variable does not match the specified value
    def assert_not_equal(self, errors, variable, input_value, error_message):
        try:
            assert variable != input_value, error_message
        except AssertionError as e:
            errors.append(str(e))
    # == asserts that the variable does match the specified value
    def assert_equal(self, errors, variable, input_value, error_message):
        try:
            assert variable == input_value, error_message
        except AssertionError as e:
            errors.append(str(e))
    # <= asserts that the variable is equal to or less than the specified value
    def assert_equal_less(self, errors, variable, input_value, error_message):
        try:
            assert variable <= input_value, error_message
        except AssertionError as e:
            errors.append(str(e))
    # IN asserts that the variable is within the specified value
    def assert_in(self, errors, variable, input_value, error_message):
        try:
            assert variable in input_value, error_message
        except AssertionError as e:
            errors.append(str(e))

    # INTEGRER: Asserts that the variable is an integrer (number)
    def assert_integrer(self, errors, variable, error_message):
        try:
            assert isinstance(variable, int), error_message
        except AssertionError as e:
            errors.append(str(e))
    # BOOLEAN: Asserts that the variable is Ture or False
    def assert_boolean(self, errors, variable, error_message):
        try:
            assert isinstance(variable, bool), error_message
        except AssertionError as e:
            errors.append(str(e))
    # IPv4: Asserts that the IPv4 Address or interface address are in the correct format
    def assert_ipv4(self, errors, variable, error_message):
        try:
            ipaddress.IPv4Interface(variable)
        except ipaddress.AddressValueError:
            errors.append(error_message)
        except ipaddress.NetmaskValueError:
            errors.append(error_message)

    # INTF: Asserts whether is enough free interfaces to accommodate all the defined interfaces
    def check_used_intfs(self, errors, intf_type, per_dev_used_intf, intf_range):
        for switch, intf in per_dev_used_intf.items():
            used_intf = len(intf)
            aval_intf = []
            for x in intf:                      # Gets only the statically defined interface numbers
                if x != 'dummy':
                    aval_intf.append(x)
            aval_intf.extend(intf_range)           # Adds range of intfs to static intfs
            total_intf = len(set(aval_intf))    # Removes duplicate intfs to find how many avaiable interfaces from range
            self.assert_equal_less(errors, used_intf, total_intf, "-svc_intf.intf.{} Are more defined interfaces ({}) than free interfaces ({})" \
                                   " in the {} reserved range on {}".format(intf_type, used_intf, total_intf, intf_type, switch))

############  Validate formatting of variables within the base.yml file ############
    def base(self, device_name, addr, users):
        base_errors = ['Check the contents of base.yml for the following issues:']

        # DEVICE_NAME (bse.device_name): Ensures that the device names used match the correct format as is used to create group names
        for dvc, name in device_name.items():
            self.assert_regex_search(base_errors, '-[a-zA-Z0-9_]+$', name, "-bse.device_name.{} '{}' is not in the correct format. Anything after " \
                           "the last '-' is used for the group name so must be letters, digits or underscore".format(dvc, name))

        # ADDR (bse.addr): Ensures that the network addresses entered are valid networks (or IP for loopback) with the correct subnet mask
        for name, address in addr.items():
            try:
                ipaddress.IPv4Network(address)
            except ipaddress.AddressValueError:
                base_errors.append("-bse.addr.{} '{}' is not a valid IPv4 network address".format(name, address))
            except ipaddress.NetmaskValueError:
                base_errors.append("-bse.addr.{} '{}' is not a valid IPv4 network address".format(name, address))
            except ValueError:
                base_errors.append("-bse.addr.{} '{}' is not a valid IPv4 network address".format(name, address))

        # USERS (bse.users): Ensures that username is present and the password at least 25 characters to make sure is encrypted (not 100% this is correct, may need to disable)
        for user in users:
            self.assert_not_equal(base_errors, user['username'], None, "-bse.users.username one of the usernames does not have a value")
            self.assert_regex_match(base_errors, '^.{25,}$', user['password'], "-bse.users.password is probably not in encypted format as it is less that 25 characters long")

        if len(base_errors) == 1:
            return "'base.yml unittest pass'"             # For some reason ansible assert needs the inside quotes
        else:
            return base_errors

############ Validate formatting of variables within the fabric.yml file ############
    def fabric(self, network_size, num_intf, route, acast_gw_mac, bse_intf, lp, mlag, addr_incre):
        fabric_errors = ['Check the contents of fabric.yml for the following issues:']

        # NETWORK_SIZE (fbc.network_size): Ensures they are integers and the number of each type of device is within the limits and constraints
        for dev_type, net_size in network_size.items():
            self.assert_integrer(fabric_errors, net_size, "-fbc.network_size.{} '{}' should be an integrer numerical value".format(dev_type, net_size))
        self.assert_regex_match(fabric_errors, '[1-4]', str(network_size['num_spines']),
                                "-fbc.network_size.num_spines is '{}', valid values are 1 to 4".format(network_size['num_spines']))
        self.assert_regex_match(fabric_errors, '^([2468]|10)$', str(network_size['num_leafs']),
                                "-fbc.network_size.num_leafs is '{}', valid values are 2, 4, 6, 8 and 10".format(network_size['num_leafs']))
        self.assert_regex_match(fabric_errors, '^[024]$', str(network_size['num_borders']),
                                "-fbc.network_size.num_borders is '{}', valid values are 0, 2 and 4".format(network_size['num_borders']))

        # NUMBER_INTERFACES (fbc.num_intf): Ensures is one number, then a comma and then upto 3 numbers
        for dev_type, intf in num_intf.items():
            self.assert_regex_match(fabric_errors, r'^\d,\d{1,3}$', str(intf),
                                    "-fbc.num_intf.{} '{}' is not a valid, must be a digit, comma and 1 to 3 digits".format(dev_type, intf))

        # OSPF (fbc.ospf): Ensures that the OSPF process is present and area in dotted decimal format
        self.assert_not_equal(fabric_errors, route['ospf']['pro'], None, "-fbc.route.ospf.pro does not have a value, this needs to be a string or integrer")
        self.assert_ipv4(fabric_errors, route['ospf']['area'],
                         "-fbc.route.ospf.area '{}' is not a valid dotted decimal area, valid values are 0.0.0.0 to 255.255.255.255".format(route['ospf']['area']))

        # BGP (fbc.bgp.as_num): Ensures that the AS is present, cant make more specific incase is 2-byte or 4-byte ASNs
        self.assert_not_equal(fabric_errors, route['bgp']['as_num'], None, "-fbc.route.bgp.as_num does not have a value")

        # ACAST_GW_MAC (fbc.acast_gw_mac): Ensures the anycast virtual MAC is a valid mac address
        self.assert_regex_match(fabric_errors, r'([0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4}', acast_gw_mac,
                                "-fbc.acast_gw_mac '{}' is not valid, can be [0-9], [a-f] or [A-F] in the format xxxx.xxxx.xxxx".format(acast_gw_mac))

        # BSE_INTF (fbc.adv.bse_intf): Ensures that the interface numbers are integrars
        for name, intf in bse_intf.items():
            if '_to_' in name:
                self.assert_integrer(fabric_errors, intf, "-fbc.adv.bse_intf.{} '{}' should be an integrer numerical value".format(name, intf))
            elif 'mlag_peer' == name:
                self.assert_regex_match(fabric_errors, '^[0-9]{1,3}-[0-9]{1,3}$', str(intf),
                                        "-fbc.adv.bse_intf.{} '{}' should be numerical values in the format xxx-xxx".format(name, intf))

        # LP (fbc.adv.lp): Ensures all the loopback names are unique, no duplicates
        dup_lp = []
        uniq_lp = {}
        for lp_type in lp.values():
            loopback = list(lp_type.keys())[0]
            if loopback not in uniq_lp:
                uniq_lp[loopback] = 1
            else:
                if uniq_lp[loopback] == 1:
                    dup_lp.append(loopback)
                uniq_lp[loopback] += 1
        self.assert_equal(fabric_errors, len(dup_lp), 0, "-fbc.adv.lp {} is/are duplicated, all loopbacks should be unique".format(dup_lp))

        # MLAG (fbc.adv.mlag): Ensures all of MLAG paraemters are integers and VLANs within limit
        for mlag_attr, value in mlag.items():
            self.assert_integrer(fabric_errors, value, "-fbc.adv.mlag.{} '{}' should be an integrer numerical value".format(mlag_attr, value))
        self.assert_regex_match(fabric_errors, r'^(?:(?:[1-9]\d{0,2}|[1-3]\d{3}|40[0-8]\d|409[0-6]),)*?(?:(?:[1-9]\d{0,2}|[1-3]\d{3}|40[0-8]\d|409[0-6]))$',
                                  str(mlag['peer_vlan']), "-fbc.adv.mlag.peer_vlan '{}' is not a valid VLAN number, valid values are 0 to 4096".format(mlag['peer_vlan']))

        # ADDR_INCRE (fbc.adv.addr_incre): Ensures all of the IP address increment values used are integers and except for mlag peering are all unique
        for incr_type, incr in addr_incre.items():
            self.assert_integrer(fabric_errors, incr, "-fbc.adv.addr_incre.{} '{}' should be an integrer numerical value".format(incr_type, incr))

        dup_incr = []
        uniq_incr = {}
        for incr_type, incr in addr_incre.items():
            if not incr_type.startswith('mlag'):
                if incr not in uniq_incr:
                    uniq_incr[incr] = 1
                else:
                    if uniq_incr[incr] == 1:
                        dup_incr.append(incr)
                    uniq_incr[incr] += 1
        self.assert_equal(fabric_errors, len(dup_incr), 0, "-fbc.adv.addr_incre {} is/are duplicated, all address increments should be unique".format(dup_incr))

        # The value returned to Ansible Assert module to determine whether failed or not
        if len(fabric_errors) == 1:
            return "'fabric.yml unittest pass'"             # For some reason ansible assert needs the inside quotes
        else:
            return fabric_errors


############ Validate formatting of variables within the service_tenant.yml file ############
    def svc_tnt(self, svc_tnt, adv):
        svc_tnt_errors = ['Check the contents of services_tenant.yml for the following issues:']

        for tnt in svc_tnt:
            # TENANT_NAME (svc_tnt.tnt.tenant_name): Ensures all tenants have a name, are no restictions of what is in it
            self.assert_not_equal(svc_tnt_errors, tnt['tenant_name'], None, "-svc_tnt.tnt.tenant_name One of the tenants does not have a name")

            # L3_TENANT (svc_tnt.tnt.l3_tenant): Ensures answer is boolean
            self.assert_boolean(svc_tnt_errors, tnt['l3_tenant'],
                                "-svc_tnt.tnt.l3_tenant '{}' is not a boolean ({}), must be True or False".format(tnt['tenant_name'], tnt['l3_tenant']))

            # VLAN (svc_tnt.tnt.vlans): Ensures vlans are defined, must be at least one
            try:
                assert tnt['vlans'] != None, "-svc_tnt.tnt.vlans '{}' tenant has no VLANs, must be at least 1 VLAN to create the tenant".format(tnt['tenant_name'])
            except AssertionError as e:
                svc_tnt_errors.append(str(e))
                return svc_tnt_errors       # Has to exit if this errors as other tests wont run due to it being unbale to loop through the vlans

            # Used by duplicate VLAN check
            dup_vl = []
            uniq_vl = {}

            for vl in tnt['vlans']:
                # VLAN_NUMBER (svc_tnt.tnt.vlans.num): Ensures all VLANs are numbers and not conflicting
                self.assert_integrer(svc_tnt_errors, vl['num'], "-svc_tnt.tnt.vlans.num '{}' should be an integrer numerical value".format(vl['num']))

                # VLAN_NAME (svc_tnt.tnt.vlans.name): Ensures all VLANs have a name, are no restrictions of what it is
                self.assert_not_equal(svc_tnt_errors, vl['name'], None, "-svc_tnt.tnt.vlans.name VLAN {} does not have a name".format(vl['num']))

                # Create dummy default values if these settings arent set in the variable file
                vl.setdefault('create_on_border', False)
                vl.setdefault('create_on_leaf', True)
                vl.setdefault('ipv4_bgp_redist', True)
                vl.setdefault('ip_addr', '169.254.255.254/16')

                # CREATE_ON_BDR, CREATE_ON_LEAF, REDIST (svc_tnt.tnt.vlans): Ensures answer is boolean
                for opt in ['create_on_border', 'create_on_leaf', 'ipv4_bgp_redist']:
                    self.assert_boolean(svc_tnt_errors, vl[opt], "-svc_tnt.tnt.vlans.{} in VLAN {} is not a boolean ({}), must be True or False".format(opt, vl['num'], vl[opt]))

                # IP_ADDR (svc_tnt.tnt.vlans.ip_addr): Ensures that the IP address is of the correct format
                self.assert_ipv4(svc_tnt_errors, vl['ip_addr'], "-svc_tnt.tnt.vlans.ip_addr '{}' is not a valid IPv4 Address/Netmask".format(vl['ip_addr']))

                # DUPLICATE VLANS (svc_tnt.tnt.vlans.num): Ensures all the VLAN numbers are unique, no duplicates
                if vl['num'] not in uniq_vl:
                    uniq_vl[vl['num']] = 1
                else:
                    if uniq_vl[vl['num']] == 1:
                        dup_vl.append(vl['num'])
                    uniq_vl[vl['num']] += 1
            self.assert_equal(svc_tnt_errors, len(dup_vl), 0,
                              "svc_tnt.tnt.vlans.num {} is duplicated in tenant '{}', all VLANs within a tenant should be unique".format(dup_vl, tnt['tenant_name']))

        # BASE_VNI (svc_tnt.adv.bse_vni): Ensures all values are integers
        for opt in ['tnt_vlan', 'l3vni', 'l2vni']:
            self.assert_integrer(svc_tnt_errors, adv['bse_vni'][opt], "-adv.bse_vni.{} '{}' should be an integrer numerical value".format(opt, adv['bse_vni'][opt]))

        # RM_NAME (svc_tnt.adv.bgp.ipv4_redist_rm_name): Ensures that it contains both 'vrf' and 'as'
        self.assert_regex_search(svc_tnt_errors, r'vrf\S*as|as\S*vrf', adv['bgp']['ipv4_redist_rm_name'],
                                 "-adv.bgp.ipv4_redist_rm_name format '{}' is not correct. It must contain 'vrf' and 'as' within its name".format(adv['bgp']['ipv4_redist_rm_name']))

        # The value returned to Ansible Assert module to determine whether failed or not
        if len(svc_tnt_errors) == 1:
            return "'services_tenant.yml unittest pass'"             # For some reason ansible assert needs the inside quotes
        else:
            return svc_tnt_errors


############ Validate formatting of variables within the service_interface.yml file ############
    def svc_intf(self, svc_intf, adv, hosts, tenants, dev_name, num_intf):
        sh_per_dev_intf, dh_per_dev_intf, per_dev_po, per_dev_intf = (defaultdict(list) for i in range(4))
        svcintf_vrf_on_lf, svcintf_vl_on_lf, svcintf_vrf_on_bdr, svcintf_vl_on_bdr = ([] for i in range(4))
        svctnt_vrf_on_lf, svctnt_vl_on_lf, svctnt_vrf_on_bdr, svctnt_vl_on_bdr = ([] for i in range(4))
        sh_intf, dh_intf, po_intf = ([] for i in range(3))
        svc_intf_errors = ['Check the contents of services_interface.yml for the following issues:']

        # Creates lists what VRFs and VLANs are on leafs and borders switches (got from services.tenant.yml)
        for tnt in tenants:
            for vl in tnt['vlans']:
                if vl.get('create_on_leaf') != False:
                    svctnt_vrf_on_lf.extend([tnt['tenant_name']])
                    svctnt_vl_on_lf.extend([vl['num']])
                if vl.get('create_on_border') == True:
                    svctnt_vrf_on_bdr.extend([tnt['tenant_name']])
                    svctnt_vl_on_bdr.extend([vl['num']])
        # Creates lists of what VRFs and VLANs are to be created on leafs and borders switches (got from services_interface.yml
        def svcinft_vrf(switch, info):
            if dev_name['leaf'] in switch:
                svcintf_vrf_on_lf.append(info)
            elif dev_name['border'] in switch:
                svcintf_vrf_on_bdr.append(info)
        def svcinft_vlan(switch, info):
            if dev_name['leaf'] in switch:
                svcintf_vl_on_lf.append(info)
            elif dev_name['border'] in switch:
                svcintf_vl_on_bdr.append(info)

        for homed, interfaces in svc_intf.items():
            # HOMED (svc_intf.intf.homed): Ensures that single-homed or dual-homed dictionaries are not empty
            try:
                assert interfaces != None, "-svc_intf.intf.{0} should not be empty, if it is not used hash out '{0}'".format(homed)
            except AssertionError as e:
                svc_intf_errors.append(str(e))
                return svc_intf_errors      # Has to exit script here as None type breaks rest of tests as it cant loop none

            for intf in interfaces:
                # INTF_NUM (svc_intf.intf.homed.intf_num): Ensures that intf_num is integrar (also added to a new list to check interface assignment)
                if intf.get('intf_num') != None:
                    self.assert_integrer(svc_intf_errors, intf['intf_num'], "-svc_intf.intf.{}.intf_num '{}' should be an integrer numerical value".format(homed, intf['intf_num']))
                # PO_NUM (svc_intf.intf.dual_homed.po_num): Ensures that po_num is integrar (also added to a new list to check interface assignment)
                if intf.get('po_num') != None:
                    self.assert_integrer(svc_intf_errors, intf['po_num'], "-svc_intf.intf.dual_homed.po_num '{}' should be an integrer numerical value".format(intf['po_num']))

                # SWITCH_NAME (svc_intf.intf.homed.switch): Ensures that it is a valid hostname within the inventory and if dual-homed the hostname is odd numbered
                self.assert_in(svc_intf_errors, intf['switch'], hosts, "-svc_intf.intf.{}.switch '{}' is not a valid hostname within the inventory".format(homed, intf['switch']))
                if homed == 'dual_homed':
                    self.assert_not_equal(svc_intf_errors, int(intf['switch'][-2:]) % 2, 0,
                                          "-svc_intf.intf.dual_homed.switch '{}' should be an odd numbered MLAG switch".format(intf['switch']))
                    # HOMED_TYPE (svc_intf.intf.dual_homed.type): Ensures that it is not a Layer3 port, can only have single-homed Layer 3 ports
                    self.assert_not_equal(svc_intf_errors, intf['type'], 'layer3',
                                          "-svc_intf.intf.dual_homed.type '{}' is a Layer3 dual-homed port, it must be single-homed".format(intf['descr']))

                # IP (svc_intf.intf.single_homed.ip_vlan): Ensures that the the IP address is in a valid IPv4 format
                if intf['type'] == 'layer3':
                    self.assert_ipv4(svc_intf_errors, intf['ip_vlan'], "-svc_intf.intf.single_homed.ip_vlan {} is not a valid IPv4 Address/Netmask".format(intf['ip_vlan']))
                    svcinft_vrf(intf['switch'], intf.get('tenant'))

                # ACCESS_VLAN (svc_intf.intf.homed.ip_vlan): Ensures all VLANs are integrers (numbers)
                elif intf['type'] == 'access':
                    self.assert_integrer(svc_intf_errors, intf['ip_vlan'], "-svc_intf.intf.{}.ip_vlan VLAN '{}' should be an integrer numerical value".format(homed, intf['ip_vlan']))
                    svcinft_vlan(intf['switch'], intf.get('ip_vlan'))

                # TRUNK_VLAN (svc_intf.intf.homed.ip_vlan): Ensures that there are no whitespaces and each vlan is an integrer (number)
                else:
                    try:
                        assert re.search(r'\s', str(intf['ip_vlan'])) == None, "-svc_intf.intf.{}.ip_vlan '{}' should not have any whitespaces in it".format(homed, intf['ip_vlan'])
                    except AssertionError as e:
                        svc_intf_errors.append(str(e))
                    if ',' in str(intf['ip_vlan']):
                        list_ip_vlan = intf['ip_vlan'].split(',')
                        for vlan in list_ip_vlan:
                            try:
                                int(vlan)
                                svcinft_vlan(intf['switch'], int(vlan))
                            except:
                                svc_intf_errors.append("-svc_intf.intf.{}.ip_vlan VLAN '{}' should be an integrer numerical value".format(homed, vlan))
                    else:
                        svcinft_vlan(intf['switch'], intf['ip_vlan'])

                # Gets number of Interfaces per device and any static interface/PO given
                if homed == 'single_homed':
                    sh_per_dev_intf[intf['switch']].append(intf.get('intf_num', 'dummy'))
                elif homed == 'dual_homed':
                    switch_pair = intf['switch'][:-2]+ "{:02d}".format(int(intf['switch'][-2:]) +1)
                    dh_per_dev_intf[intf['switch']].append(intf.get('intf_num', 'dummy'))
                    dh_per_dev_intf[switch_pair].append(intf.get('intf_num', 'dummy'))
                    per_dev_po[intf['switch']].append(intf.get('po_num', 'dummy'))
                    per_dev_po[switch_pair].append(intf.get('po_num', 'dummy'))

        # VRF/VLAN: Ensures that the VRF or VLAN of the interfaces being configured on are on the switches they are being configured on
        miss_vrf_on_lf = set(svcintf_vrf_on_lf) - set(svctnt_vrf_on_lf)
        miss_vrf_on_bdr = set(svcintf_vrf_on_bdr) - set(svctnt_vrf_on_bdr)
        miss_vl_on_lf = set(svcintf_vl_on_lf) - set(svctnt_vl_on_lf)
        miss_vl_on_bdr = set(svcintf_vl_on_bdr) - set(svctnt_vl_on_bdr)

        # VRF_ON_SWITCH (svc_intf.intf.single_homed.tenant): Ensures that the VRF exists on the switch that an interface in that VRF is being configured
        self.assert_equal(svc_intf_errors, len(miss_vrf_on_lf), 0,
                        "-svc_intf.intf.single_homed.tenant VRFs {} are not on leaf switches but are in leaf interface configurations".format(list(miss_vrf_on_lf)))
        self.assert_equal(svc_intf_errors, len(miss_vrf_on_bdr), 0,
                        "-svc_intf.intf.single_homed.tenant VRFs {} are not on border switches but are in border interface configurations".format(list(miss_vrf_on_bdr)))
        # VRF_ON_SWITCH (svc_intf.intf.homed.ip_vlan): Ensures that the VLAN exists on the switch that an interface using that VLAN is being configured
        self.assert_equal(svc_intf_errors, len(miss_vl_on_lf), 0,
                        "-svc_intf.intf.homed.ip_vlan VLANs {} are not on leaf switches but are in leaf interface configurations".format(list(miss_vl_on_lf)))
        self.assert_equal(svc_intf_errors, len(miss_vl_on_bdr), 0,
                        "-svc_intf.intf.homed.ip_vlan VLANs {} are not on border switches but are in border interface configurations".format(list(miss_vl_on_bdr)))

        for homed, intf in adv.items():
            # INTF_RANGE (svc_intf.adv.homed.first/last): Ensures that the reserved interface and Port-Channel ranges are integrers
            for intf_pos, num in intf.items():
                try:
                    assert isinstance(num, int), "-svc_intf.adv.{}.{} '{}' should be an integrer numerical value".format(homed, intf_pos, num)
                except AssertionError as e:
                    svc_intf_errors.append(str(e))
                    return svc_intf_errors          # Has to exit if this errors as other tests wont run due to it being unable to loop through the interfaces

            # Create list of all interfaces in the reserved ranges
            if homed == 'single_homed':
                for intf_num in range(intf['first_intf'], intf['last_intf'] + 1):
                     sh_intf.append(intf_num)
            if homed == 'dual_homed':
                for intf_num in range(intf['first_intf'], intf['last_intf'] + 1):
                     dh_intf.append(intf_num)
                for po_num in range(intf['first_po'], intf['last_po'] + 1):
                     po_intf.append(po_num)

        # SH_INTF_RANGE (svc_intf.intf.single_homed): Ensures are enough free ports in the range (range minus conflicting static assignments) for number of interfaces defined
        self.check_used_intfs(svc_intf_errors, 'single_homed', sh_per_dev_intf, sh_intf)
        # DH_INTF_RANGE (svc_intf.intf.dual_homed): Ensures are enough free ports in the range (range minus conflicting static assignments) for number of interfaces defined
        self.check_used_intfs(svc_intf_errors, 'dual_homed', dh_per_dev_intf, dh_intf)
        # PO_INTF_RANGE (svc_intf.intf.dual_homed): Ensures are enough free port-channels in the range (range minus conflicting static assignments) for number of port-channels defined
        self.check_used_intfs(svc_intf_errors, 'port_channel', per_dev_po, po_intf)

        # Combines the SH and DH per device interface dictionaries
        for d in (sh_per_dev_intf, dh_per_dev_intf):
            for key, value in d.items():
                per_dev_intf[key].extend(value)

        # TOTAL_INTF (svc_intf.intf.homed): Make sure that are not more defined interfaces (single and dual_homed) than there are actual interfaces on the switch
        for switch, intf in per_dev_intf.items():
            if dev_name['leaf'] in switch:
                max_intf = int(num_intf['leaf'].split(',')[1])
            elif dev_name['border'] in switch:
                max_intf = int(num_intf['border'].split(',')[1])
            self.assert_equal_less(svc_intf_errors, len(intf), max_intf,
                                   "-svc_intf.intf.homed Are more defined interfaces ({}) than the maximum number of interfaces ({}) on {}".format(len(intf), max_intf, switch))

        if len(svc_intf_errors) == 1:
            return "'services_interface.yml unittest pass'"             # For some reason ansible assert needs the inside quotes
        else:
            return svc_intf_errors