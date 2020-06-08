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
svc_intf.intf.homed.po_num: Ensures that po_num is integrar (also added to a new list to check interface assignment)
svc_intf.intf.homed.switch: Ensures that it is a valid device name within inventary_hostnames and the hostname is odd numbered if dual-homed
svc_intf.intf.single_homed.ip_vlan: Ensures that the the IP address is in a valid IPv4 format
svc_intf.intf.homed.ip_vlan: Ensures all VLANs are integrers (numbers)
svc_intf.intf.homed.ip_vlan: Ensures that there are no whitespaces and each vlan is an integrer (number)
VRF/VLAN: Ensures that the VRF or VLAN of the interfaces being configured on are on the switches they are being configured on
svc_intf.adv.homed.first/last: Ensures that the reserved interface and Port-Channel ranges are integrers
vc_intf.intf.single_homed: Ensures are enough free ports in the range (range minus conflicting static assignments) for number of interfaces defined
svc_intf.intf.dual_homed: Ensures are enough free ports in the range (range minus conflicting static assignments) for number of interfaces defined
svc_intf.intf.dual_homed: Ensures are enough free port-channels in the range (range minus conflicting static assignments) for number of port-channels defined
TOTAL_INTF: Make sure that are not more defined interfaces (single and dual_homed) than there are actual interfaces on the switch

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



############  Generic assert functions used by all classes to make DRY ############
# DEFO can do integrers and regex (search and match)

    # def re_search(regex, input, msg):
    #     try:
    #         assert re.search(regex, input), msg
    #     except AssertionError as e:
    #         errors.append(str(e))

    #     re_search('-[a-zA-Z0-9_]+$', name, "-bse.device_name.{} format ({}) is not correct. Anything after " \
    #                  "the last '-' is used for the group name so must be letters, digits or underscore".format(dvc, name))


        # Used to assert any integrer !!!!! MAYBE ADD AS GENERIC ONE FOR ALL and also for IP addresses ????
        # def assert_integrer(value, path):
        #     try:
        #         assert isinstance(value, int), "-{} '{}' should be an integrer numerical value".format(path, value)
        #     except AssertionError as e:
        #         svc_intf_errors.append(str(e))





############  Validate formatting of variables within the base.yml file ############
    def base(self, device_name, addr, users):
        base_errors = ['Check the contents of base.yml for the following issues:']

        # DEVICE_NAME (bse.device_name): Ensures that the device names used match the correct format as is used to create group names
        for dvc, name in device_name.items():
            try:
                assert re.search('-[a-zA-Z0-9_]+$', name), "-bse.device_name.{} format ({}) is not correct. Anything after " \
                     "the last '-' is used for the group name so must be letters, digits or underscore".format(dvc, name)
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


############ Validate formatting of variables within the fabric.yml file ############
    def fabric(self, network_size, num_intf, route, acast_gw_mac, bse_intf, lp, mlag, addr_incre):
        fabric_errors = ['Check the contents of fabric.yml for the following issues:']

        # NETWORK_SIZE (fbc.network_size): Ensures they are integers and the number of each type of device is within the limits and constraints
        for dev_type, net_size in network_size.items():
            try:
                assert type(net_size) == int, "-fbc.network_size.{} should be an integrer numerical value".format(dev_type)
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

        # NUMBER_INTERFACES (fbc.num_intf): Ensures is one number, then a comma and then upto 3 numbers
        for dev_type, intf in num_intf.items():
            try:
                assert re.match(r'^\d,\d{1,3}$', str(intf)), "-fbc.num_intf.{} {} is not a valid format".format(dev_type, intf)
            except AssertionError as e:
                fabric_errors.append(str(e))

        # OSPF (fbc.ospf): Ensures that the OSPF process is present and area in dotted decimal format
        try:
            assert route['ospf']['pro'] != None ,"-fbc.route.ospf.pro does not have a value, this needs to be a string or integrer"
        except AssertionError as e:
            fabric_errors.append(str(e))
        try:
            ipaddress.IPv4Address(route['ospf']['area'])
        except ipaddress.AddressValueError:
            fabric_errors.append("-fbc.route.ospf.area ({}) is not a valid dotted decimal area, valid values are 0.0.0.0 to 255.255.255.255".format(route['ospf']['area']))

        # BGP (fbc.bgp.as_num): Ensures that the AS is present, cant make more specific incase is 2-byte or 4-byte ASNs
        try:
            assert type(route['bgp']['as_num']) != None, "-fbc.route.bgp.as_num does not have a value"
        except AssertionError as e:
            fabric_errors.append(str(e))

        # ACAST_GW_MAC (fbc.acast_gw_mac): Ensures the anycast virtual MAC is a valid mac address
        try:
            assert re.match(r'([0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4}', acast_gw_mac), \
                            "-fbc.acast_gw_mac ({}) is not a valid, can be [0-9], [a-f] or [A-F] in the format xxxx.xxxx.xxxx".format(acast_gw_mac)
        except AssertionError as e:
            fabric_errors.append(str(e))

        # BSE_INTF (fbc.adv.bse_intf): Ensures that the interface numbers are integrars
        for name, intf in bse_intf.items():
            if '_to_' in name:
                try:
                    assert type(intf) == int, "-fbc.adv.bse_intf.{} should be an integrer numerical value".format(name)
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
                assert type(value) == int, "-fbc.adv.mlag.{} should be an integrer numerical value".format(mlag_attr)
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
                assert type(incr) == int, "-ffbc.adv.addr_incre.{} should be an integrer numerical value".format(incr_type)
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


############ Validate formatting of variables within the service_tenant.yml file ############
    def svc_tnt(self, svc_tnt, adv):
        svc_tnt_errors = ['Check the contents of services_tenant.yml for the following issues:']

        for tnt in svc_tnt:
            # TENANT_NAME (svc_tnt.tnt.tenant_name): Ensures all tenants have a name, are no restictions of what is in it
            try:
                assert tnt['tenant_name'] != None, "-svc_tnt.tnt.tenant_name, one of the tenants does not have a name"
            except AssertionError as e:
                svc_tnt_errors.append(str(e))
            # L3_TENANT (svc_tnt.tnt.l3_tenant): Ensures answer is boolean
            try:
                assert isinstance(tnt['l3_tenant'], bool), "-svc_tnt.tnt.l3_tenant for tenant {} is not a boolean ({}), must be True or False".format(tnt['tenant_name'], tnt['l3_tenant'])
            except AssertionError as e:
                svc_tnt_errors.append(str(e))

            # VLAN (svc_tnt.tnt.vlans): Ensures vlans are defined, must be at least one
            try:
                assert tnt['vlans'] != None, "-svc_tnt.tnt.vlans no VLANs in tenant {}, must be at least 1 VLAN to create the tenant ".format(tnt['tenant_name'])
            except AssertionError as e:
                svc_tnt_errors.append(str(e))
                return svc_tnt_errors

            # Used by duplicate VLAN check
            dup_vl = []
            uniq_vl = {}

            for vl in tnt['vlans']:
                # VLAN_NUMBER (svc_tnt.tnt.vlans.num): Ensures all VLANs are numbers and not conflicting
                try:
                    assert isinstance(vl['num'], int), "-svc_tnt.tnt.vlans.num VLAN '{}' should be an integrer numerical value".format(vl['num'])
                except AssertionError as e:
                    svc_tnt_errors.append(str(e))

                # VLAN_NAME (svc_tnt.tnt.vlans.name): Ensures all VLANs have a name, are no restrictions of what it is
                try:
                    assert vl['name'] != None, "-svc_tnt.tnt.vlans.name VLAN{} does not have a name".format(vl['num'])
                except AssertionError as e:
                    svc_tnt_errors.append(str(e))

                # Create dummy default values if these settings arent set in the variable file
                vl.setdefault('create_on_border', False)
                vl.setdefault('create_on_leaf', True)
                vl.setdefault('ipv4_bgp_redist', True)
                vl.setdefault('ip_addr', '169.254.255.254/16')

                # CREATE_ON_BDR, CREATE_ON_LEAF, REDIST (svc_tnt.tnt.vlans): Ensures answer is boolean
                for opt in ['create_on_border', 'create_on_leaf', 'ipv4_bgp_redist']:
                    try:
                        assert isinstance(vl[opt], bool), "-svc_tnt.tnt.vlans.{} in VLAN{} is not a boolean ({}), "\
                                                      "must be True or False".format(opt, vl['num'], vl[opt])
                    except AssertionError as e:
                        svc_tnt_errors.append(str(e))

                # IP_ADDR (svc_tnt.tnt.vlans.ip_addr): Ensures that the IP address is of the correct format
                try:
                    ipaddress.IPv4Interface(vl['ip_addr'])
                except ipaddress.AddressValueError:
                    svc_tnt_errors.append("-svc_tnt.tnt.vlans.ip_addr ({}) is not a valid IPv4 address".format(vl['ip_addr']))

                # DUPLICATE VLANS (svc_tnt.tnt.vlans.num): Ensures all the VLAN numbers are unique, no duplicates
                if vl['num'] not in uniq_vl:
                    uniq_vl[vl['num']] = 1
                else:
                    if uniq_vl[vl['num']] == 1:
                        dup_vl.append(vl['num'])
                    uniq_vl[vl['num']] += 1
            try:
                assert len(dup_vl) == 0, "svc_tnt.tnt.vlans.num {} is/are duplicated in tenant {}, "\
                                         "all VLANs within a tenant should be unique".format(dup_vl, tnt['tenant_name'])
            except AssertionError as e:
                svc_tnt_errors.append(str(e))

        # BASE_VNI (svc_tnt.adv.bse_vni): Ensures all values are integers
        for opt in ['tnt_vlan', 'l3vni', 'l2vni']:
            try:
                assert isinstance(adv['bse_vni'][opt], int), "-adv.bse_vni.{} ({}) should be an integrer numerical value".format(opt, adv['bse_vni'][opt])
            except AssertionError as e:
                svc_tnt_errors.append(str(e))

        # RM_NAME (svc_tnt.adv.bgp.ipv4_redist_rm_name): Ensures that it contains both 'vrf' and 'as'
        try:
            assert re.search(r'vrf\S*as|as\S*vrf', adv['bgp']['ipv4_redist_rm_name']), "-adv.bgp.ipv4_redist_rm_name format ({}) is not correct. " \
                                "It must contain 'vrf' and 'as' within its name".format(adv['bgp']['ipv4_redist_rm_name'])
        except AssertionError as e:
            svc_tnt_errors.append(str(e))

        # The value returned to Ansible Assert module to determine whether failed or not
        if len(svc_tnt_errors) == 1:
            return "'service_tenant.yml unittest pass'"             # For some reason ansible assert needs the inside quotes
        else:
            return svc_tnt_errors


############ Validate formatting of variables within the service_interface.yml file ############

    def svc_intf(self, svc_intf, adv, hosts, tenants, dev_name, num_intf):
        sh_per_dev_intf, dh_per_dev_intf, per_dev_po, per_dev_intf = (defaultdict(list) for i in range(4))
        tnt_on_border, tnt_on_leaf, intf_on_border, intf_on_leaf, sh_intf, dh_intf, po_intf = ([] for i in range(7))
        svc_intf_errors = ['Check the contents of services_interface.yml for the following issues:']

        # Used in svc_intf, gets a list of what VRFs and VLANs are to be created on leafs and borders switches (got from services_interface.yml
        def vrf_vlan_list(switch, info):
            if dev_name['leaf'] in switch:
                intf_on_leaf.append(info)
            elif dev_name['border'] in switch:
                intf_on_border.append(info)

         # List what VRFs and VLANs are on leafs and borders switches (got from services.tenant.yml)
        for tnt in tenants:
            for vl in tnt['vlans']:
                if vl.get('create_on_leaf') != False:
                    tnt_on_leaf.extend([tnt['tenant_name'], vl['num']])
                if vl.get('create_on_border') == True:
                    tnt_on_border.extend([tnt['tenant_name'], vl['num']])


        for homed, interfaces in svc_intf.items():
            # HOMED (svc_intf.intf.homed): Ensures that single-homed or dual-homed dictionaries are not empty
            try:
                assert interfaces != None, "-svc_intf.intf.{0} should not be empty, if it is not used hash out '{0}'".format(homed)
            except AssertionError as e:
                svc_intf_errors.append(str(e))
                return svc_intf_errors              # Has to exit script here as Nonetype breaks rest of it

            for intf in interfaces:
                # INTF_NUM (svc_intf.intf.homed.intf_num): Ensures that intf_num is integrar (also added to a new list to check interface assignment)
                if intf.get('intf_num') != None:
                    try:
                        assert isinstance(intf['intf_num'], int), "-svc_intf.intf.homed.intf_num '{}' should be an integrer numerical value".format(intf['intf_num'])
                        # all_custom_intf.append(intf['intf_num'])
                    except AssertionError as e:
                        svc_intf_errors.append(str(e))
                # PO_NUM (svc_intf.intf.po_num): Ensures that po_num is integrar (also added to a new list to check interface assignment)
                if intf.get('po_num') != None:
                    try:
                        assert isinstance(intf['po_num'], int), "-svc_intf.intf.homed.po_num '{}' should be an integrer numerical value".format(intf['po_num'])
                        # all_custom_po.append(intf['po_num'])
                    except AssertionError as e:
                        svc_intf_errors.append(str(e))

                # SWITCH_NAME (svc_intf.intf.homed.switch): Ensures that it is a valid device name within inventory_hostnames and the hostname is odd numbered if dual-homed
                try:
                    assert intf['switch'] in hosts, "-svc_intf.intf.homed.switch '{}' is not an inventory_hostname".format(intf['switch'])
                except AssertionError as e:
                    svc_intf_errors.append(str(e))
                if homed == 'dual_homed':
                    try:
                        assert int(intf['switch'][-2:]) % 2 != 0, "-svc_intf.intf.dual_homed.switch '{}' should be an odd numbered MLAG switch".format(intf['switch'])
                    except AssertionError as e:
                        svc_intf_errors.append(str(e))
                    # HOMED_TYPE (svc_intf.intf.dual_homed.type): Ensures that it is not a Layer3 port, can only have single-homed Layer 3 ports
                    if intf['type'] == 'layer3':
                        svc_intf_errors.append("-svc_intf.intf.dual_homed.type Layer3 port ({}) cant be dual-homed, it must be single-homed".format(intf['descr']))

                # IP (svc_intf.intf.single_homed.ip_vlan): Ensures that the the IP address is in a valid IPv4 format
                if intf['type'] == 'layer3':
                    try:
                        ipaddress.IPv4Interface(intf['ip_vlan'])
                    except ipaddress.AddressValueError:
                        svc_intf_errors.append("-svc_intf.intf.single_homed.ip_vlan {} is not a valid IPv4 address".format(intf['ip_vlan']))
                    vrf_vlan_list(intf['switch'], intf['tenant'])

                # ACCESS_VLAN (svc_intf.intf.homed.ip_vlan): Ensures all VLANs are integrers (numbers)
                elif intf['type'] == 'access':
                    try:
                        assert isinstance(intf['ip_vlan'], int), "-svc_intf.intf.homed.ip_vlan VLAN '{}' should be an integrer numerical value".format(intf['ip_vlan'])
                    except AssertionError as e:
                        svc_intf_errors.append(str(e))
                    vrf_vlan_list(intf['switch'], intf['ip_vlan'])

                # TRUNK_VLAN (svc_intf.intf.homed.ip_vlan): Ensures that there are no whitespaces and each vlan is an integrer (number)
                else:
                    try:
                        assert re.search(r'\s', str(intf['ip_vlan'])) == None, "-svc_intf.intf.homed.ip_vlan '{}' should not have any whitespaces in it".format(intf['ip_vlan'])
                    except AssertionError as e:
                        svc_intf_errors.append(str(e))
                    if ',' in str(intf['ip_vlan']):
                        list_ip_vlan = intf['ip_vlan'].split(',')
                        for vlan in list_ip_vlan:
                            try:
                                int(vlan)
                                vrf_vlan_list(intf['switch'], int(vlan))
                            except:
                                svc_intf_errors.append("-svc_intf.intf.homed.ip_vlan VLAN{} should be an integrer numerical value".format(vlan))
                    else:
                        vrf_vlan_list(intf['switch'], intf['ip_vlan'])

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
        miss_on_lf = set(intf_on_leaf) - set(tnt_on_leaf)
        miss_on_bdr = set(intf_on_border) - set(tnt_on_border)
        try:
            assert len(miss_on_lf) == 0, "VRF or VLANs {} are not on leaf switches but are in leaf interface configurations".format(list(miss_on_lf))
        except AssertionError as e:
            svc_intf_errors.append(str(e))
        try:
            assert len(miss_on_bdr) == 0, "VRF or VLANs {} are not on border switches but are in border interface configurations".format(list(miss_on_bdr))
        except AssertionError as e:
            svc_intf_errors.append(str(e))

        for homed, intf in adv.items():
            # INTF_RANGE (svc_intf.adv.homed.first/last): Ensures that the reserved interface and Port-Channel ranges are integrers
            for intf_pos, num in intf.items():
                try:
                    assert isinstance(num, int), "-svc_intf.adv.{}.{} '{}' should be an integrer numerical value".format(homed, intf_pos, num)
                except AssertionError as e:
                    svc_intf_errors.append(str(e))

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
        for switch, intf in sh_per_dev_intf.items():
            used_intf = len(intf)
            aval_intf = []
            for x in intf:                      # Gets only the statically defined interface numbers
                if x != 'dummy':
                    aval_intf.append(x)
            aval_intf.extend(sh_intf)           # Adds range of intfs to static intfs
            total_intf = len(set(aval_intf))    # Removes duplicate intfs to find how many avaiable interfaces from range
            try:
                assert used_intf <= total_intf, "-Are more defined single-homed interfaces ({}) than free interfaces in reserved range ({}) on {}".format(used_intf, total_intf, switch)
            except AssertionError as e:
                svc_intf_errors.append(str(e))

        # DH_INTF_RANGE (svc_intf.intf.dual_homed): Ensures are enough free ports in the range (range minus conflicting static assignments) for number of interfaces defined
        for switch, intf in dh_per_dev_intf.items():
            used_intf = len(intf)
            aval_intf = []
            for x in intf:
                if x != 'dummy':
                    aval_intf.append(x)
            aval_intf.extend(dh_intf)
            total_intf = len(set(aval_intf))
            try:
                assert used_intf <= total_intf, "-Are more defined dual-homed interfaces ({}) than free interfaces in reserved range ({}) on {}".format(used_intf, total_intf, switch)
            except AssertionError as e:
                svc_intf_errors.append(str(e))

        # PO_INTF_RANGE (svc_intf.intf.dual_homed): Ensures are enough free port-channels in the range (range minus conflicting static assignments) for number of port-channels defined
        for switch, intf in per_dev_po.items():
            used_intf = len(intf)
            aval_intf = []
            for x in intf:
                if x != 'dummy':
                    aval_intf.append(x)
            aval_intf.extend(po_intf)
            total_intf = len(set(aval_intf))
            try:
                assert used_intf <= total_intf, "-Are more defined Port-channels ({}) than free Port-channels in reserved range ({}) on {}".format(used_intf, total_intf, switch)
            except AssertionError as e:
                svc_intf_errors.append(str(e))

        # Combines the SH and DH per device interface dictionaries
        for d in (sh_per_dev_intf, dh_per_dev_intf):
            for key, value in d.items():
                per_dev_intf[key].extend(value)

        # TOTAL_INTF: TOTAL_INTF: Make sure that are not more defined interfaces (single and dual_homed) than there are actual interfaces on the switch
        for switch, intf in per_dev_intf.items():
            if dev_name['leaf'] in switch:
                max_intf = int(num_intf['leaf'].split(',')[1])
            elif dev_name['border'] in switch:
                max_intf = int(num_intf['border'].split(',')[1])
            try:
                assert len(intf) <= max_intf, "-Are more defined interfaces ({}) than the maximum number of interfaces ({}) on {}".format(len(intf), max_intf, switch)
            except AssertionError as e:
                svc_intf_errors.append(str(e))

        return svc_intf_errors
