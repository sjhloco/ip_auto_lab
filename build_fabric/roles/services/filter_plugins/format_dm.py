class FilterModule(object):
    def filters(self):
        return {
            'create_svc_tnt_dm': self.svc_tnt_dm,
            'create_svc_intf_dm': self.svc_intf_dm
        }

    # Used to take VLANs and change sequental vlans so that they are separated by '-' as per the "trunk allowed vlans" config syntax
    def vlan_seq(self, vlans):
        # 1. Creates a list of all vlans, doesnt matter if int, or str spilt by ',' or '-'
        vlan_list, vlan_seq_lists, vlan_seq = ([] for i in range(3))
        if isinstance(vlans, int) == True:
            vlan_list.append(vlans)
        elif isinstance(vlans, list) == True:
            vlan_list = vlans
        else:
            for vl in vlans.split(','):
                if '-' in vl:
                    for each_vl in range(int(vl.split('-')[0]), int(vl.split('-')[1]) +1):
                        vlan_list.append(each_vl)
                else:
                    vlan_list.append(int(vl))
        # 2. Order the list and create mini lists of sequnetial vlans
        for vlan in sorted(vlan_list):
            if not vlan_seq_lists:
                vlan_seq_lists.append([vlan])
                continue
            if vlan_seq_lists[-1][-1] == vlan - 1:
                    vlan_seq_lists[-1].append(vlan)
            else:
                vlan_seq_lists.append([vlan])
        # 3. Join the mini lists together
        for vlan in vlan_seq_lists:
            if len(vlan) == 1:
                vlan_seq.extend(vlan)
            else:
                vlan_seq.append('{}-{}'.format(vlan[0], vlan[-1]))
        # Return it as one big string
        return ','.join([str(elem) for elem in vlan_seq])

    # Creates 2 new seperate Data Models for Leaf and Border devices with only the tenants and vlans on those device roles and incorporating the VNIs
    def svc_tnt_dm(self, srv_tnt, bse_vni, vni_incre, vpc_peer_vlan):
        l3vni = bse_vni['l3vni']
        tnt_vlan = bse_vni['tnt_vlan']
        l2vni = bse_vni['l2vni']
        border_tnt, leaf_tnt = ([] for i in range(2))
        bdr_vlan_numb, lf_vlan_numb = ([1, vpc_peer_vlan] for i in range(2))

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
                # Creates a list of just all the VLAN numbers on border switches
                for vl in border_vlans.copy():
                    bdr_vlan_numb.append(vl['num'])
                if tnt['l3_tenant'] == True:
                    bdr_vlan_numb.append(tnt_vlan)
                # Creates the new leaf DM of tenant & vlan properties
                border_vlans.append({'name': tnt['tenant_name'] + '_L3VNI' , 'num': tnt_vlan, 'ip_addr': 'l3_vni', 'ipv4_bgp_redist': False, 'vni': l3vni})
                border_tnt.append({'tnt_name': tnt['tenant_name'], 'l3_tnt': tnt['l3_tenant'], 'l3vni': l3vni, 'tnt_vlan': tnt_vlan, 'tnt_redist': tnt_redist, 'bgp_redist_tag': tnt['bgp_redist_tag'], 'vlans': border_vlans})

            if len(leaf_vlans) != 0:
                # Creates a list of just the VLAN numbers on leaf switches
                for vl in leaf_vlans.copy():
                    lf_vlan_numb.append(vl['num'])
                if tnt['l3_tenant'] == True:
                    lf_vlan_numb.append(tnt_vlan)
                # Creates the new leaf DM of enant & vlan properties
                leaf_vlans.append({'name': tnt['tenant_name'] + '_L3VNI' , 'num': tnt_vlan, 'ip_addr': 'l3_vni', 'ipv4_bgp_redist': False, 'vni': l3vni})
                leaf_tnt.append({'tnt_name': tnt['tenant_name'], 'l3_tnt': tnt['l3_tenant'], 'l3vni': l3vni, 'tnt_vlan': tnt_vlan, 'tnt_redist': tnt_redist, 'bgp_redist_tag': tnt['bgp_redist_tag'], 'vlans': leaf_vlans})

            # For each tenant (doesnt matter if L3_tnt or not) increments VLAN and L3VNI by 1
            l3vni = l3vni + vni_incre['l3vni']
            tnt_vlan = tnt_vlan + vni_incre['tnt_vlan']

        return [leaf_tnt, border_tnt, self.vlan_seq(lf_vlan_numb), self.vlan_seq(bdr_vlan_numb)]

    def svc_intf_dm(self, all_homed, hostname, intf_adv, bse_intf):
        sl_hmd = intf_adv['single_homed']
        dl_hmd = intf_adv['dual_homed']
        intf_fmt = bse_intf['intf_fmt']
        ec_fmt = bse_intf['ec_fmt']
        all_intf, have_intf, sl_need_intf, dl_need_intf, all_intf_num, sl_range, dl_range, need_po, all_po_num, po_range = ([] for i in range(10))

        # 1. DEFAULTS: Fill out default values and change the nested dict into a list
        for homed, interfaces in all_homed.items():
            for intf in interfaces:
                # Adds homed as a dict and adds some default value dicts
                intf.setdefault('intf_num', None)
                if homed == 'single_homed':
                    intf['dual_homed'] = False
                elif homed == 'dual_homed':
                    intf['dual_homed'] = True
                    intf.setdefault('po_mode', 'active')
                    if intf['po_mode'] == True:      # Needed as 'on' in yaml is converted to True
                        intf['po_mode'] = "on"
                    intf.setdefault('po_num', None)
                # STP dict is added based on Layer2 port type
                if intf['type'] == 'access':
                    intf['stp'] = 'edge'
                elif intf['type'] == 'stp_trunk':
                    intf['stp'] = 'network'
                elif intf['type'] == 'stp_trunk_non_ba':
                    intf['stp'] = 'normal'
                elif intf['type'] == 'non_stp_trunk':
                    intf['stp'] = 'edge'
                all_intf.append(intf)

        # 2. FILTER: Deletes interfaces not on this switch and separates the defined and non-defined ports for single and dual-homed
        for intf in all_intf:
            if intf['dual_homed'] == False and intf['switch'] == hostname:
                if intf['intf_num'] == None:
                    sl_need_intf.append(intf)
                else:
                    all_intf_num.append(intf['intf_num'])                       # List of all used interface numbers
                    intf['intf_num'] = intf_fmt + str(intf['intf_num'])         # Adds the interface name to the number
                    have_intf.append(intf)
            # Dual-homed interfaces need to be created on both MLAG pairs so logic matches both hostnames
            elif intf['dual_homed'] == True and (intf['switch'] == hostname or intf['switch'] == hostname[:-2] + "{:02d}".format(int(hostname[-2:]) -1)):
                if intf['intf_num'] == None:
                    dl_need_intf.append(intf)
                else:
                    all_intf_num.append(intf['intf_num'])
                    intf['intf_num'] = intf_fmt + str(intf['intf_num'])
                    have_intf.append(intf)
            del intf['switch']                  # Removes as no longer needed

        # 3. INTF_RANGES: Adjust interface assignment ranges to remove any already used interfaces
        for intf_num in range(dl_hmd['first_intf'], dl_hmd['last_intf'] + 1):
            dl_range.append(intf_num)
        dl_range = set(dl_range) - set(all_intf_num)
        dl_range = list(dl_range)
        dl_range.sort()
        for intf_num in range(sl_hmd['first_intf'], sl_hmd['last_intf'] + 1):
            sl_range.append(intf_num)
        sl_range = set(sl_range) - set(all_intf_num)
        sl_range = list(sl_range)
        sl_range.sort()

        # 4a. SINGLE-HOMED: Adds the interface number to existing DM
        for intf, int_num in zip(sl_need_intf, sl_range):
            if intf['dual_homed'] == False:
                intf['intf_num'] = intf_fmt + str(int_num)
                have_intf.append(intf)
        # 4b. DUAL-HOMED: Adds the interface number to existing DM
        for intf, int_num in zip(dl_need_intf, dl_range):
            if intf['dual_homed'] == True:
                intf['intf_num'] = intf_fmt + str(int_num)
                have_intf.append(intf)

        # 5. PO: Adds PO to interface and adds a port-channel interface with the VPC number
        all_intf = []
        for intf in have_intf:
            if intf['dual_homed'] == True:
                # If no PO number (none) adds to new list
                if intf['po_num'] == None:
                    need_po.append(intf)
                else:
                    # If PO number is defined creates new PO interface and adds VPC number
                    all_po_num.append(intf['po_num'])
                    all_intf.append(intf)
                    all_intf.append({'intf_num': ec_fmt + str(intf['po_num']), 'descr': intf['descr'], 'type': intf['type'],
                                     'ip_vlan': intf['ip_vlan'], 'vpc_num': intf['po_num'], 'stp': intf['stp']})
            else:
                all_intf.append(intf)

        # Adjust PO assignment ranges to remove any already used POs
        for po_num in range(dl_hmd['first_po'], dl_hmd['last_po'] + 1):
            po_range.append(po_num)
        po_range = set(po_range) - set(all_po_num)
        po_range = list(po_range)
        po_range.sort()
        # Adds PO to interface and adds a port-channel interface with the VPC number
        for intf, po_num in zip(need_po, po_range):
            intf['po_num'] = po_num
            all_intf.append(intf)
            all_intf.append({'intf_num': ec_fmt + str(intf['po_num']), 'descr': intf['descr'], 'type': intf['type'],
                             'ip_vlan': intf['ip_vlan'], 'vpc_num': intf['po_num'], 'stp': intf['stp']})

        # Adjusts allowed VLAN ranges if sequential (is only needed for post_val, config would automatically do it anyway)
        for intf in all_intf:
            if 'trunk' in intf['type'] and isinstance(intf['ip_vlan'], str) == True:
                intf['ip_vlan'] = self.vlan_seq(intf['ip_vlan'])

        return all_intf

