class FilterModule(object):
    def filters(self):
        return {
            'create_svc_tnt_dm': self.svc_tnt_dm,
            # 'srv_ports_dm': self.srv_ports_dm
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