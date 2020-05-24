class FilterModule(object):
    def filters(self):
        return {
            'create_svc_tnt_dm': self.svc_tnt_dm,
            'create_svc_intf_dm': self.svc_intf_dm
        }

    # Creates 2 new seperate Data Models for Leaf and Border devices with only the tenants and vlans on those device roles and incorporating the VNIs
    def svc_tnt_dm(self, srv_tnt, bse_vni, vni_incre):
        l3vni = bse_vni['l3vni']
        tnt_vlan = bse_vni['tnt_vlan']
        l2vni = bse_vni['l2vni']
        border_tnt, leaf_tnt = ([] for i in range(2))

        # Looping through current DM of tenants creates new per-device-role (border or leaf) DM of tenants
        for tnt in srv_tnt:
            # Lists to hold all the VLANs for that device-role within this tenant and redist flag. Is cleared at each tnt iteration
            border_vlans, leaf_vlans, tnt_redist = ([] for i in range(3))

            # If the BGP redist tag has not been set adds a dict with default value of the l3vni
            tnt.setdefault('bgp_redist_tag', l3vni)

            # For each VLAN makes decisions based on the VLAN settings
            for vl in tnt['vlans']:
                # Creates a L2VNI by adding vlan num to base VNI
                vl['vni'] = l2vni + vl['num']
                # Creates seperate lists of VLANs on leafs and borders. 'setdefault' adds a dictionary for the default values
                if vl.setdefault('create_on_border', False) == True:
                    border_vlans.append(vl)
                if vl.setdefault('create_on_leaf', True) == True:
                    leaf_vlans.append(vl)

                # Adds a dictionary with value on None if no IP address is present
                vl.setdefault('ip_addr', None)
                # If the IP addesss is 'None' makes sure that 'ipv4_bgp_redist: False'
                if vl['ip_addr'] == None:
                    vl['ipv4_bgp_redist'] = False
                # If the VLAN has an IP addr adds dict 'ipv4_bgp_redist: True' (the default) adds 'True' to 'tnt_redist'
                elif vl['ip_addr'] != None:
                    if vl.setdefault('ipv4_bgp_redist', True) != False:
                        tnt_redist.append(vl['ipv4_bgp_redist'])

            # For each tenant increments the L2VNI by 10000
            l2vni = l2vni + vni_incre['l2vni']

            # Sets the tnt_redist flag to True or False dependant on whether any VLANs within that tenant are to be redistributed
            if len(tnt_redist) == 0:
                tnt_redist = False
            elif len(tnt_redist) != 0:
                tnt_redist = True

            # Adds the L3VNI VLAN (not used in template if not a L3_tnt) and creates seperate lists of L3 tenants (and vlans) per device-role
            if len(border_vlans) != 0:
                border_vlans.append({'name': tnt['tenant_name'] + '_L3VNI' , 'num': tnt_vlan, 'ip_addr': 'l3_vni', 'ipv4_bgp_redist': False, 'vni': l3vni})
                border_tnt.append({'tnt_name': tnt['tenant_name'], 'l3_tnt': tnt['l3_tenant'], 'l3vni': l3vni, 'tnt_vlan': tnt_vlan, 'tnt_redist': tnt_redist, 'bgp_redist_tag': tnt['bgp_redist_tag'], 'vlans': border_vlans})
            if len(leaf_vlans) != 0:
                leaf_vlans.append({'name': tnt['tenant_name'] + '_L3VNI' , 'num': tnt_vlan, 'ip_addr': 'l3_vni', 'ipv4_bgp_redist': False, 'vni': l3vni})
                leaf_tnt.append({'tnt_name': tnt['tenant_name'], 'l3_tnt': tnt['l3_tenant'], 'l3vni': l3vni, 'tnt_vlan': tnt_vlan, 'tnt_redist': tnt_redist, 'bgp_redist_tag': tnt['bgp_redist_tag'], 'vlans': leaf_vlans})

            # For each tenant (doesnt matter if L3_tnt or not) increments VLAN and L3VNI by 1
            l3vni = l3vni + vni_incre['l3vni']
            tnt_vlan = tnt_vlan + vni_incre['tnt_vlan']

        return [leaf_tnt, border_tnt]

    def svc_intf_dm(self, all_types, hostname, intf_adv, bse_intf):
        sl_hmd = intf_adv['single_homed']
        dl_hmd = intf_adv['dual_homed']

        intf_fmt = bse_intf['intf_fmt']
        ec_fmt = bse_intf['ec_fmt']

        #
        all_interfaces = []

        # 1. DEFAULTS: Fill out default values for dual_homed & po_mode, add stp & port type and create new list
        for intf_type, interfaces in all_types.items():
            for intf in interfaces:
                if intf.setdefault('dual_homed', True) != False:
                    intf.setdefault('po_mode', 'active')
                # Adds port type as dict and combines into 1 non-nested list
                if intf_type == 'layer3':
                    intf['intf_type'] = 'layer3'
                if intf_type == 'access':
                    intf['stp'] = 'edge'
                    intf['intf_type'] = 'access'
                elif intf_type == 'stp_trunk':
                    intf['stp'] = 'network'
                    intf['intf_type'] = 'stp_trunk'
                elif intf_type == 'non_stp_trunk':
                    intf['stp'] = 'normal'
                    intf['intf_type'] = 'non_stp_trunk'
                all_interfaces.append(intf)

        # 2. FILTER: Deletes interface DM for interfaces not on this switch (single-homed) or the MLAG pair (dual-homed)
        # for interfaces in all_types.values():
        #     # Reverse loops through list so doesnt have any iteration issues due to loop elements being deleted
        #     for intf in reversed(interfaces):
        #         if intf['dual_homed'] == False and intf['switch'] != hostname:
        #             interfaces.remove(intf)
        # # Needs fresh loop as if hostname is even changes name (-1) so keeps interface config for the MLAG pair
        # for interfaces in all_types.values():
        #     for intf in reversed(interfaces):
        #         if intf['dual_homed'] == True:
        #             if int(hostname[-2:]) % 2 == 0:
        #                 hostname = hostname[:-2] + "{:02d}".format(int(hostname[-2:]) -1)
        #             if intf['switch'] != hostname:
        #                 interfaces.remove(intf)
        #         del intf['switch']                  # Removes as no longer needed

        # # 3. SINGLE-HOMED: Adds the interface number to existing DM
        # sl_incr_num, dl_incr_num = (0 for i in range(2))
        # for intf_type, interfaces in all_types.items():
        #     port_channels = []
        #     for intf in interfaces:
        #         if intf['dual_homed'] == False:
        #             intf['num'] = intf_fmt + str(sl_hmd['first_intf'] + sl_incr_num)
        #             sl_incr_num += 1
        #         # 4. DUAL-HOMED: Adds the interface number, creates port-channel DM and adds PO and VPC to existing DM
        #         elif intf['dual_homed'] == True:
        #             intf['num'] = intf_fmt + str(dl_hmd['first_intf'] + dl_incr_num)
        #             intf['vpc_num'] = dl_hmd['vpc'] + dl_incr_num
        #             intf['po_num'] = dl_hmd['po'] + dl_incr_num
        #             dl_incr_num += 1
        #             port_channels.append({'num': ec_fmt + str(intf['po_num']), 'descr': intf['descr'], 'ip_vlan': intf['ip_vlan'], 'stp': intf['stp']})
        #         del intf['dual_homed']                  # Removes as no longer needed
        #     interfaces.extend(port_channels)            # Adds PO to list of interfaces


        return all_interfaces

# interfaces = [{'descr': 'dev1'}, {'descr': 'dev2'}, {'descr': 'dev3'}, {'descr': 'dev4'}, {'descr': 'dev5'}, {'descr': 'dev6'}]
# first_intf = 13
# last_intf = 32
# int_num = [1,2,3,4,5,6]

# for intf, num in zip(interfaces, range(first_intf, last_intf)):
#     intf['num'] = num

# if n in range(3,9)


# if interface is defined get the numbers.
# check if numbers are in the range.
# Create a new list of all numbers in range excluding these
# double loop using rnage numbers.


#     access:
#       - descr: DC1-SRV-APP01 eth1
#         ip_vlan: 10
#         switch: DC1-N9K-LEAF01
#       - descr: DC1-SRV-PRD01 eth1
#         ip_vlan: 20
#         switch: DC1-N9K-LEAF01


#   adv:                  # Reserved interface range that server ports can be automatically assigned from (applies to all leaf and border switches)
#     dual_homed:                   # Used only for dual-homed devices
#       first_int: 21     # First interface
#       last_int: 50      # Last interface
#       po: 21                      # First PortChannel used
#       vpc: 21                     # First VPC used
#     single_homed:                 # Used only for single-homed devices
#       first_int: Ethernet1/51     # First interface
#       last_int: Ethernet1/60      # Last interface



        # l3vni = bse_vni['l3vni']
        # tnt_vlan = bse_vni['tnt_vlan']
        # l2vni = bse_vni['l2vni']
        # border_tnt, leaf_tnt = ([] for i in range(2))



#  # Create a new ports data model including interface and Po info
#     def srv_ports_dm(self, srv_ports, srv_ports_adv, srv_tenants):
#         ### 1. First need to create seperate lists for single and dual homed so can use loop index to increment interafce number ###
#         sh_ports = []
#         dh_ports = []
#         # Split the single and dual homed start interface into a list of two elements (port type and number)
#         sh_first = srv_ports_adv['single_homed']['first_int'].split('/')
#         dh_first = srv_ports_adv['dual_homed']['first_int'].split('/')

#         ### 1. Use iteration number (index) to increment interface and add to the dictionary
#         # Create single-homed interfaces
#         for index, port in enumerate(srv_ports['single_homed']):
#             int_num = str(int(sh_first[1]) + index)                     # Adds the index to the start port number
#             port['interface'] = sh_first[0] + '/' + int_num             # Creates a new dict element for interface number
#             sh_ports.append(port)                                   # Adds all single-homed port dictonaries to a list

#         # Create dual-homed interfaces,POs and VPC
#         for index, port in enumerate(srv_ports['dual_homed']):
#             int_num = str(int(dh_first[1]) + index)
#             port['interface'] = dh_first[0] + '/' + int_num             # Used 2 different ways to add to dictionary, could have used either
#             port.update({'vpc': srv_ports_adv['dual_homed']['vpc'] + index, 'po': srv_ports_adv['dual_homed']['po'] + index})
#             dh_ports.append(port)                                   # Adds all dual-homed port dictonaries to a list

#         ### 2. FAIL-FAST: Only return new dictionaires if havent reached the interface limit
#         num_sh = []
#         num_dh = []
#         # Works out the max number of interfaces that would be available
#         sh_limit = int(srv_ports_adv['single_homed']['last_int'].split('/')[1]) - int(sh_first[1]) + 1
#         dh_limit = int(srv_ports_adv['dual_homed']['last_int'].split('/')[1]) - int(dh_first[1]) + 1

#         # Gets switch names from port dictionaries
#         for sh_swi in sh_ports:
#             num_sh.append(sh_swi ['switch'])
#         for dh_swi in dh_ports:
#             num_dh.append(dh_swi ['switch'])

#         # Counts the number of ports on each switch and returns error if is higher than limit
#         for sw_name, sw_count in dict(Counter(num_sh)).items():
#             if sw_count > sh_limit:     # If the number of switch ports is more than the limit
#                 return 'Error: No single-homed ports left on ' + sw_name
#         for sw_name, sw_count in dict(Counter(num_dh)).items():
#             if sw_count > dh_limit:     # If the number of switch ports is more than the limit
#                 return 'Error: No dual-homed ports left on ' + sw_name

#         # 3. Returns a dictionary containing both dictionaries
#         return {'sh_ports': sh_ports, 'dh_ports': dh_ports}