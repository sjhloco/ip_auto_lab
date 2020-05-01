"""Validates the core fabric variables in the base and fabric files are of the correct
format to be able to run the playbook and build a fabric.
A pass or fail is returned to the Ansible Assert module, if it fails the full output is also
returned for the failure message. The following methods check:

-base using base.yml:
bse.device_name: Ensures that the device names used match the correct format as that is heavily used in inventory script logic
bse.addr: Ensures that the network addresses entered are valid networks (or IP for loopback) with the correct subnet mask

-fabric using abric.yml
fbc.network_size: Ensures the number of each type of device is within the limits and constraints
fbc.ospf: Ensures that the OSPF process is present and area in dotted decimal format
fbc.bgp.as_num: Ensures that the AS is present, cant make more specific incase is 2-byte or 4-byte ASNs
fbc.acast_gw_mac: Ensures the anycast virtual MAC is a valid mac address
fbc.adv.bse_intf: Ensures that the interface numbers are integrars
fbc.adv.lp: Ensures all the loopback names are unique, no duplicates
fbc.adv.mlag): Ensures all of MLAG paraemters are integers and VLANs within limit
fbc.adv.addr_incre: Ensures all of the IP address increment values used are integers and except for mlag peering are all unique
"""

import re
import ipaddress


class FilterModule(object):
    def filters(self):
        return {
            'input_bse_validate': self.base,
            'input_fbc_validate': self.fabric
        }

 # Validate formatting of variables within the base.yml file
    def base(self, device_name, addr, users):
        base_errors = ['Check the contents of base.yml for the following issues:']

        # DEVICE_NAME (bse.device_name): Ensures that the device names used match the correct format as that is heavily used in inventory script logic
        try:
            assert re.match('.*-SPINE$', device_name['spine']), "-bse.device_name.spine format ({}) is not correct, it must end in '-SPINE'".format(device_name['spine'])
        except AssertionError as e:
            base_errors.append(str(e))
        try:
            assert re.match('.*-LEAF$', device_name['leaf']), "-bse.device_name.leaf format ({}) is not correct, it must end in '-LEAF'".format(device_name['leaf'])
        except AssertionError as e:
            base_errors.append(str(e))
        try:
            assert re.match('.*-BORDER$', device_name['border']), "-bse.device_name.border format ({}) is not correct, it must end in '-BORDER'".format(device_name['border'])
        except AssertionError as e:
            base_errors.append(str(e))

        # ADDR (bse.addr): Ensures that the network addresses entered are valid networks (or IP for loopback) with the correct subnet mask
        for name, address in addr.items():
            try:
                ipaddress.IPv4Network(address)
            except ipaddress.AddressValueError:
                base_errors.append("-bse.addr.{} ({}) is not a valid IPv4 network address".format(name, address))
            except ipaddress.NetmaskValueError:
                base_errors.append("-bse.addr.{} ({}) is not a valid IPv4 network address".format(name, address))
            except ValueError:
                base_errors.append("-bse.addr.{} ({}) is not a valid IPv4 network address".format(name, address))

        # USERS (bse.users): Ensures that username is present and the password at least 25 characters to make sure is encrypted (not 100% this is correct, may need to disable)
        for user in users:
            try:
                assert user['username'] != None, "-bse.users.username one of the usernames does not have a value"
            except AssertionError as e:
                base_errors.append(str(e))
            try:
                assert re.match('^.{25,}$', user['password']), "-bse.users.password is probably not in encypted format as it is less that 25 characters long"
            except AssertionError as e:
                base_errors.append(str(e))

        # The value returned to Ansible Assert module to determine whether failed or not
        if len(base_errors) == 1:
            return "'base.yml unittest pass'"             # For some reason ansible assert needs the inside quotes
        else:
            return base_errors

 # Validate formatting of variables within the fabric.yml file
    def fabric(self, network_size, route, acast_gw_mac, bse_intf, lp, mlag, addr_incre):
        fabric_errors = ['Check the contents of fabric.yml for the following issues:']

        # 1. NETWORK_SIZE (fbc.network_size): Ensures thye are integers and the number of each type of device is within the limits and constraints
        for dev_type, net_size in network_size.items():
            try:
                assert type(net_size) == int, "-fbc.network_size.{} should be a numerical value".format(dev_type)
            except AssertionError as e:
                fabric_errors.append(str(e))

        try:
            assert re.match('[1-4]', str(network_size['num_spines'])), "-fbc.network_size.num_spines is {}, valid values are 1 to 4".format(network_size['num_spines'])
        except AssertionError as e:
            fabric_errors.append(str(e))
        try:
            assert re.match('^([2468]|10)$', str(network_size['num_leafs'])), "-fbc.network_size.num_leafs is {}, valid values are 2, 4, 6, 8 and 10".format(network_size['num_leafs'])
        except AssertionError as e:
            fabric_errors.append(str(e))
        try:
            assert re.match('^[024]$', str(network_size['num_borders'])), "-fbc.network_size.num_borders is {}, valid values are 0, 2 and 4".format(network_size['num_borders'])
        except AssertionError as e:
            fabric_errors.append(str(e))

        # 2. OSPF (fbc.ospf): Ensures that the OSPF process is present and area in dotted decimal format
        try:
            assert route['ospf']['pro'] != None ,"-fbc.route.ospf.pro does not have a value, this needs to be a string or integrer"
        except AssertionError as e:
            fabric_errors.append(str(e))
        try:
            ipaddress.IPv4Address(route['ospf']['area'])
        except ipaddress.AddressValueError:
            fabric_errors.append("-fbc.route.ospf.area ({}) is not a valid dotted decimal area, valid values are 0.0.0.0 to 255.255.255.255".format(route['ospf']['area']))

        # 3. BGP (fbc.bgp.as_num): Ensures that the AS is present, cant make more specific incase is 2-byte or 4-byte ASNs
        try:
            assert type(route['bgp']['as_num']) != None, "-fbc.route.bgp.as_num does not have a value"
        except AssertionError as e:
            fabric_errors.append(str(e))

        # 4. ACAST_GW_MAC (fbc.acast_gw_mac): Ensures the anycast virtual MAC is a valid mac address
        try:
            assert re.match(r'([0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4}', acast_gw_mac), \
                            "-fbc.acast_gw_mac ({}) is not a valid, can be [0-9], [a-f] or [A-F] in the format xxxx.xxxx.xxxx".format(acast_gw_mac)
        except AssertionError as e:
            fabric_errors.append(str(e))

        # BSE_INTF (fbc.adv.bse_intf): Ensures that the interface numbers are integrars
        for name, intf in bse_intf.items():
            if '_to_' in name:
                try:
                    assert type(intf) == int, "-fbc.adv.bse_intf.{} should be a numerical value".format(name)
                except AssertionError as e:
                    fabric_errors.append(str(e))
            elif 'mlag_peer' == name:
                try:
                    assert re.match('^[0-9]{1,3}-[0-9]{1,3}$', str(intf)), "-fbc.adv.bse_intf.{} should be numerical values in the format xxx-xxx".format(name)
                except AssertionError as e:
                    fabric_errors.append(str(e))

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
        try:
            assert len(dup_lp) == 0, "-fbc.adv.lp {} is/are duplicated, all loopbacks should be unique".format(dup_lp)
        except AssertionError as e:
            fabric_errors.append(str(e))

        # MLAG (fbc.adv.mlag): Ensures all of MLAG paraemters are integers and VLANs within limit
        for mlag_attr, value in mlag.items():
            try:
                assert type(value) == int, "-fbc.adv.mlag.{} should be a numerical value".format(mlag_attr)
            except AssertionError as e:
                fabric_errors.append(str(e))
        try:
            assert re.match(r'^(?:(?:[1-9]\d{0,2}|[1-3]\d{3}|40[0-8]\d|409[0-6]),)*?(?:(?:[1-9]\d{0,2}|[1-3]\d{3}|40[0-8]\d|409[0-6]))$', str(mlag['peer_vlan'])), \
                            "-fbc.adv.mlag.peer_vlan ({}) is not a valid VLAN, valid values are 0 to 4096".format(mlag['peer_vlan'])
        except AssertionError as e:
            fabric_errors.append(str(e))

        # ADDR_INCRE (fbc.adv.addr_incre): Ensures all of the IP address increment values used are integers and except for mlag peering are all unique
        for incr_type, incr in addr_incre.items():
            try:
                assert type(incr) == int, "-ffbc.adv.addr_incre.{} should be a numerical value".format(incr_type)
            except AssertionError as e:
                fabric_errors.append(str(e))

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
        try:
            assert len(dup_incr) == 0, "-fbc.adv.addr_incre {} is/are duplicated, all address increments should be unique".format(dup_incr)
        except AssertionError as e:
            fabric_errors.append(str(e))

        # The value returned to Ansible Assert module to determine whether failed or not
        if len(fabric_errors) == 1:
            return "'fabric.yml unittest pass'"             # For some reason ansible assert needs the inside quotes
        else:
            return fabric_errors