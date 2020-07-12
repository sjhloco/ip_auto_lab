from collections import defaultdict

class FilterModule(object):
    def filters(self):
        return {
            'create_svc_tnt_dm': self.svc_tnt_dm,
            'create_svc_intf_dm': self.svc_intf_dm,
            'create_svc_rtr_dm': self.svc_rtr_dm
        }


###################################### TNT DATA MODEL: Uses input from service_tenant.yml ######################################
# Creates 2 new seperate Data Models for Leaf and Border devices with only the tenants and vlans on those device roles and incorporating the VNIs

    def svc_tnt_dm(self, srv_tnt, bse_vni, vni_incre, vpc_peer_vlan, rm_name_tmp, as_num):
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

            # Creates the redistribution route-map name
            rm_name = rm_name_tmp.replace('src', 'conn').replace('dst', 'BGP' + str(as_num) + '_' + tnt['tenant_name'])

            # Adds the L3VNI VLAN (not used in template if not a L3_tnt) and creates seperate lists of L3 tenants (and vlans) per device-role
            if len(border_vlans) != 0:
                # Creates a list of just all the VLAN numbers on border switches
                for vl in border_vlans.copy():
                    bdr_vlan_numb.append(vl['num'])
                if tnt['l3_tenant'] == True:
                    bdr_vlan_numb.append(tnt_vlan)
                # Creates the new leaf DM of tenant & vlan properties
                border_vlans.append({'name': tnt['tenant_name'] + '_L3VNI' , 'num': tnt_vlan, 'ip_addr': 'l3_vni', 'ipv4_bgp_redist': False, 'vni': l3vni})
                border_tnt.append({'tnt_name': tnt['tenant_name'], 'l3_tnt': tnt['l3_tenant'], 'l3vni': l3vni, 'tnt_vlan': tnt_vlan, 'tnt_redist': tnt_redist, 'rm_name':rm_name, 'bgp_redist_tag': tnt['bgp_redist_tag'], 'vlans': border_vlans})

            if len(leaf_vlans) != 0:
                # Creates a list of just the VLAN numbers on leaf switches
                for vl in leaf_vlans.copy():
                    lf_vlan_numb.append(vl['num'])
                if tnt['l3_tenant'] == True:
                    lf_vlan_numb.append(tnt_vlan)
                # Creates the new leaf DM of enant & vlan properties
                leaf_vlans.append({'name': tnt['tenant_name'] + '_L3VNI' , 'num': tnt_vlan, 'ip_addr': 'l3_vni', 'ipv4_bgp_redist': False, 'vni': l3vni})
                leaf_tnt.append({'tnt_name': tnt['tenant_name'], 'l3_tnt': tnt['l3_tenant'], 'l3vni': l3vni, 'tnt_vlan': tnt_vlan, 'tnt_redist': tnt_redist, 'rm_name':rm_name, 'bgp_redist_tag': tnt['bgp_redist_tag'], 'vlans': leaf_vlans})

            # For each tenant (doesnt matter if L3_tnt or not) increments VLAN and L3VNI by 1
            l3vni = l3vni + vni_incre['l3vni']
            tnt_vlan = tnt_vlan + vni_incre['tnt_vlan']

        return [leaf_tnt, border_tnt, self.vlan_seq(lf_vlan_numb), self.vlan_seq(bdr_vlan_numb)]


###################################### INTF DATA MODEL: Uses input from service_interface.yml ######################################
# Creates a per-device data model of all interfaces to be configured on that device

    #VLAN SEQ: Method used by main ' svc_intf_dm' method to change sequental vlans so that they are separated by '-' as per the "trunk allowed vlans" config syntax
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


    # Main function to create the data models
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

            if intf['dual_homed'] == False and hostname in intf['switch']:
                if intf['intf_num'] == None:
                    sl_need_intf.append(intf)
                else:
                    all_intf_num.append(intf['intf_num'])                       # List of all used interface numbers
                    intf['intf_num'] = intf_fmt + str(intf['intf_num'])         # Adds the interface name to the number
                    have_intf.append(intf)
            # Dual-homed interfaces need to be created on both MLAG pairs so logic matches both hostnames
            elif intf['dual_homed'] == True and hostname in intf['switch'] or hostname[:-2] + "{:02d}".format(int(hostname[-2:]) -1) in intf['switch']:
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












    def svc_rtr_dm(self, hostname, bgp_grps, bgp_tnt, ospf, static_route, adv, fbc):


        adv_bgp = adv['bgp']
        redist = adv['redist']
        name = adv_bgp['naming']
        bse_intf = fbc['adv']['bse_intf']
        as_num = fbc['route']['bgp']['as_num']
        peers = defaultdict(list)
        groups = defaultdict(dict)
        all_pfx_lst = []
        all_rm = []

################################################## Functions for creating prefix-lists and route-maps ##################################################

        # BGP_ATTR: Function to create the prefix-list and route-map data-models for BGP attribute associated prefixes (weight, local pref, med & AS-path)
        def create_bgpattr_rm_pfx_lst(input_data, direction, bgp_attr, pl_name, rm_name):
            # If BGP attribute is defined and is a prefix (list of 1 or more prefixes)
            if input_data.get(direction, {}).get(bgp_attr) != None and isinstance(input_data.get(direction, {}).get(bgp_attr), dict) == True:
                # Loop through each attribute dictionary {bgp_attr_value: [pfx, pfx, etc]}
                for bgp_attr_value, all_pfx in input_data[direction][bgp_attr].items():
                    self.rm_seq += 10           # Increment RM seq number by 10 each loop
                    pl_seq = 0                  # The starting PL sequence number
                    # Adds a tuple (pl_name, seq, action, pfx) to the list of all prefix-lists
                    if isinstance(all_pfx, str) == True and all_pfx == 'any':
                        all_pfx_lst.append((pl_name.replace('val', str(bgp_attr_value)), pl_seq + 5, 'permit', '0.0.0.0/0 le 32'))
                    else:
                        for pfx in all_pfx:
                            pl_seq += 5         # If it is a list of pfxs increments prefix-list sequence number by 5 each loop
                            all_pfx_lst.append((pl_name.replace('val', str(bgp_attr_value)), pl_seq, 'permit', pfx))
                    # Adds a tuple (rm_name, seq, pl_name, weight) to list of all route-maps
                    all_rm.append((rm_name, self.rm_seq, pl_name.replace('val', str(bgp_attr_value)), (bgp_attr, bgp_attr_value)))
                # Removes the BGP attribute key:value, if inbound/outbound dict is now empty deletes and adds new dict with route-map name as the key
                del input_data[direction][bgp_attr]
                if input_data[direction] == {}:
                    del input_data[direction]
                input_data[direction + '_rm'] = rm_name

        # BGP ALLOW/DENY: Function to create the prefix-list and route-map for allowed and denied prefixes (added in RM order deny, allow, allow_any, deny_any)
        def create_allowdeny_rm_pfx_lst(input_data, direction, pl_name, rm_name):
            # return input_data
            pl_seq = 0
            # Loops DENY prefixes (will be a list) and adds tuple entry
            if input_data.get(direction, {}).get('deny') != None and isinstance(input_data.get(direction, {}).get('deny'), list) == True:
                self.rm_seq += 10
                for pfx in input_data[direction]['deny']:
                    pl_seq += 5
                    all_pfx_lst.append((pl_name, pl_seq, 'deny', pfx))
                    all_rm.append((rm_name, self.rm_seq, pl_name, (None, None)))
            # Loops through ALLOW prefixes and adds tuple entry
            if input_data.get(direction, {}).get('allow') != None:
                if isinstance(input_data.get(direction, {}).get('allow'), list) == True:
                    # Adds RM_seq and RM entry as means above DENY if statment has not been matched
                    if pl_seq == 0:
                        self.rm_seq += 10
                        all_rm.append((rm_name, self.rm_seq, pl_name, (None, None)))
                    for pfx in input_data[direction]['allow']:
                        pl_seq += 5
                        all_pfx_lst.append((pl_name, pl_seq, 'permit', pfx))
                # If ALLOW is only 'default route' or 'any' uses pre-defined prefix list in RM entry
                elif input_data.get(direction, {}).get('allow') == 'default':
                    self.rm_seq += 10
                    all_rm.append((rm_name, self.rm_seq, name['pl_default'], (None, None)))
                    del input_data[direction]['allow']
                elif input_data.get(direction, {}).get('allow') == 'any':
                    self.rm_seq += 10
                    all_rm.append((rm_name, self.rm_seq, name['pl_allow'], (None, None)))
            # DENY ALL should always be last entry in route-map
            if input_data.get(direction, {}).get('deny') != None and input_data.get(direction, {}).get('deny') == 'any':
                self.rm_seq += 10
                all_rm.append((rm_name, self.rm_seq, name['pl_deny'], (None, None)))
            # If the inbound or putbound dict exists it is deleted the new dict added with the route-map name used as the key
            if input_data.get(direction) != None:
                del input_data[direction]
            input_data[direction + '_rm'] = rm_name


        # REDIST: Function to create the prefix-list and route-map for redistribution
        # Creates the all_pfx_lst and all_rm lists before returning the RM name back
        # RM format [name, seq, prx_list, attr], PL format [name, seq, permission, prx]
        def create_redist_rm_pfx_lst(source, destination,allow_pfx, pfx_attr, tenant):

            # EDIT_PL/RM_NAME: Joins routing protocol to the process, shortens connected and adds VRF to BGP (or would have conflicts)
            if 'bgp_' in source:
                source = source.replace('_', '').upper() + '_' + tenant
            elif '_' in source:
                source = source.replace('_', '').upper()
            elif source == 'connected':
                source = 'conn'

            # Adds VRF to BGP for destination protocol (redistributing into BGP)
            if 'BGP' in destination:
                destination = destination.replace('_', '').upper() + '_' + tenant

            # Creates names for all PL and RMs used by this function
            pl_name = redist['pl_name'].replace('src', source).replace('dst', destination)
            rm_name = redist['rm_name'].replace('src', source).replace('dst', destination)
            pl_metric_name = redist['pl_metric_name'].replace('src', source).replace('dst', destination)

            rm_seq = 0
            # NO PFX_LST: Creates blank RM with on matching prefix-list if both allow and metric not defined
            if allow_pfx == None and pfx_attr == None:
                rm_seq += 10
                all_rm.append((rm_name, rm_seq, None, (None, None)))


            # METRIC: Creates the PL and RM for any prefixes that are to be redistributed with a metric value
            if pfx_attr != None:
                for attr_value, all_pfx in pfx_attr.items():
                    rm_seq += 10        # Increment RM seq number by 10 each loop
                    pl_seq = 0           # The starting PL sequence number
                    # Adds a tuple (pl_name, seq, action, pfx) to the list of all prefix-lists
                    if isinstance(all_pfx, str) == True and all_pfx == 'any':
                        all_pfx_lst.append((pl_metric_name.replace('val', str(attr_value)), pl_seq + 5, 'permit', '0.0.0.0/0 le 32'))
                    else:
                        for pfx in all_pfx:
                            pl_seq += 5         # If it is a list of pfxs increments prefix-list sequence number by 5 each loop
                            all_pfx_lst.append((pl_metric_name.replace('val', str(attr_value)), pl_seq, 'permit', pfx))
                    # Adds a tuple (rm_name, seq, pl_name, weight) to list of all route-maps
                    all_rm.append((rm_name, rm_seq, pl_metric_name.replace('val', str(attr_value)), ('metric', attr_value)))

            # ALLOW: Creates the PL and RM for any prefixes that are to be redistributed with no metric value
            if allow_pfx == 'any':
                all_pfx_lst.append((pl_name, 5, 'permit', '0.0.0.0/0 le 32'))
            elif allow_pfx != None and source == 'conn':
                rm_seq += 20            # 20 as redist in tenant (tag of SVIs in tnt) is 10
                all_rm.append((rm_name, rm_seq, ' '.join(allow_pfx), (None, None)))
            elif allow_pfx != None:
                pl_seq = 0
                for pfx in allow_pfx:
                    pl_seq += 5
                    all_pfx_lst.append((pl_name, pl_seq, 'permit', pfx))
                rm_seq += 10
                all_rm.append((rm_name, rm_seq, pl_name, (None, None)))

            return rm_name      # RM_name returned back to be added to the OSPF_proc dict

################################################## BGP data-model creation ##################################################


        # 1. GROUPS and PEERS :Creates a dictionary of Groups/templates (key is grp_name) and a dictionary of peers (key is vrf_name) on this device.
        for grp in bgp_grps:
            # Set default values if the switch or tenant keys are not specified in group
            grp.setdefault('switch', [])
            grp.setdefault('tenant', None)
            for peer in grp['peers']:
                # If switch or tenant are not specified in peer use group values
                # !!!!! HAVE REMOVED 1 LEVEL of LOOPs, can delete once happy not added any issues
                # for sw in peer.setdefault('switch', grp['switch']):
                if hostname in peer.setdefault('switch', grp['switch']):
                    # if sw  == hostname:
                    # PEERS: Formatting to create the peer dictionary on this device
                    peer.setdefault('tenant', grp['tenant'])
                    del peer['switch']              # No longer needed in the dict
                    peer['grp'] = grp['name']       # Adds new dict for group name
                    tenant = peer.pop('tenant')	    # No longer needed in the dict
                    # Creates new dictionary of VRFs with the values being lists of the peer dictionaries within that VRF
                    if isinstance(tenant, list) == True:        # If peer is multiple tenants
                        for tnt in tenant:
                            peers[tnt].append(peer.copy())      # Need copy or cant edit later as same object referencec multiple times
                    else:                                       # If peer is only in 1 tenants
                        peers[tenant].append(peer)

                    # GROUPS: Creates new dictionary with the Key the name of the group/templates and the values being its attributes
                    groups[grp['name']]['timers'] = grp.setdefault('timers', adv_bgp['timers'])
                    groups[grp['name']] = grp

        # GROUP: Loop through each group, create prefix-lists and route maps before delting unneeded dictionaries
        for grp in groups.values():
            # CLEANUP: No need for the switch, tenant and peers dictionaires anymore
            del grp['switch']
            del grp['peers']
            del grp['tenant']
            # INBOUND: Runs functions on inbound methods to get prefix-lists and route maps for inbound traffic control
            self.rm_seq = 0
            create_bgpattr_rm_pfx_lst(grp, 'inbound', 'weight', name['pl_wght_in'].replace('name', grp['name']), name['rm_in'].replace('name', grp['name']))
            create_bgpattr_rm_pfx_lst(grp, 'inbound', 'pref', name['pl_pref_in'].replace('name', grp['name']), name['rm_in'].replace('name', grp['name']))
            create_allowdeny_rm_pfx_lst(grp, 'inbound', name['pl_in'].replace('name', grp['name']), name['rm_in'].replace('name', grp['name']))
            # OUTBOUND: Runs functions on inbound methods to get prefix-lists and route maps for inbound traffic control
            self.rm_seq = 0
            create_bgpattr_rm_pfx_lst(grp, 'outbound', 'med', name['pl_med_out'].replace('name', grp['name']), name['rm_out'].replace('name', grp['name']))
            create_bgpattr_rm_pfx_lst(grp, 'outbound', 'as_prepend', name['pl_aspath_out'].replace('name', grp['name']), name['rm_out'].replace('name', grp['name']))
            create_allowdeny_rm_pfx_lst(grp, 'outbound', name['pl_out'].replace('name', grp['name']), name['rm_out'].replace('name', grp['name']))

        # PEER: Loop through each peer, create prefix-lists and route maps before delting unneeded dictionaries (switch, tenant, peers)
        for all_pr in peers.values():
            for pr in all_pr:
                # INBOUND: Runs functions on inbound methods to get prefix-lists and route maps for inbound traffic control
                self.rm_seq = 0
                create_bgpattr_rm_pfx_lst(pr, 'inbound', 'weight', name['pl_wght_in'].replace('name', pr['name']), name['rm_in'].replace('name', pr['name']))
                create_bgpattr_rm_pfx_lst(pr, 'inbound', 'pref', name['pl_pref_in'].replace('name', pr['name']), name['rm_in'].replace('name', pr['name']))
                create_allowdeny_rm_pfx_lst(pr, 'inbound', name['pl_in'].replace('name', pr['name']), name['rm_in'].replace('name', pr['name']))
                # OUTBOUND: Runs functions on inbound methods to get prefix-lists and route maps for inbound traffic control
                self.rm_seq = 0
                create_bgpattr_rm_pfx_lst(pr, 'outbound', 'med', name['pl_med_out'].replace('name', pr['name']), name['rm_out'].replace('name', pr['name']))
                create_bgpattr_rm_pfx_lst(pr, 'outbound', 'as_prepend', name['pl_aspath_out'].replace('name', pr['name']), name['rm_out'].replace('name', pr['name']))
                create_allowdeny_rm_pfx_lst(pr, 'outbound', name['pl_out'].replace('name', pr['name']), name['rm_out'].replace('name', pr['name']))

        # Get rid of any duplicates casued by using same peer in multiple VRFs
        all_pfx_lst = set(all_pfx_lst)
        all_pfx_lst = list(all_pfx_lst)
        all_pfx_lst.sort()
        all_rm = set(all_rm)
        all_rm = list(all_rm)
        all_rm.sort()


        # NETWORK & SUMMARY and REDIST: repurpose the tenant key
        tenant = defaultdict(dict)
        for tnt in bgp_tnt:
            tnt.setdefault('switch', [])           # Uses empty list if switch not specified, needed to allow using tnenant swithc as default
            # If NETWORK, SUMMARY or REDIST are defined for this switch creates DM for that

            if tnt.get('network') != None:
                pfx_tmp = []
                for pfx in tnt['network']:
                    # if hostname in pfx['switch']:
                    if hostname in pfx.setdefault('switch', tnt['switch']):
                        pfx_tmp.extend(pfx['prefix'])
            tenant[tnt['name']]['network'] = pfx_tmp

            if tnt.get('summary') != None:
                pfx_tmp = {}
                for pfx in tnt['summary']:
                    # if hostname in pfx['switch']:
                    if hostname in pfx.setdefault('switch', tnt['switch']):
                        # Add dummy value for summary if doesnt have one
                        pfx.setdefault('filter', None)
                        for each_pfx in pfx['prefix']:
                            pfx_tmp[each_pfx] = pfx.get('filter', None)
            tenant[tnt['name']]['summary'] = pfx_tmp

            if tnt.get('redist') != None:
                redist_tmp = []
                for each_redist in tnt['redist']:
                    if hostname in pfx.setdefault('switch', tnt['switch']):
                        # Creates the prefix-lists and route-maps before returning the RM name
                        rm_name = create_redist_rm_pfx_lst(each_redist['type'], 'BGP' + str(as_num), each_redist.setdefault('allow', None), each_redist.setdefault('metric', None), tnt['name'])


                        # rm_name = create_redist_rm_pfx_lst('BGP' + str(as_num), each_redist['type'], each_redist.setdefault('allow', None), each_redist.setdefault('metric', None), tnt['name'])
                        # Replace '_' for ' ' so is in correct format for when cmd is sued in the template
                        if '_' in each_redist['type']:
                            each_redist['type'] = each_redist['type'].replace('_', ' ')
                        # Adds RM name and cleans up non-needed dicst before addint to tenant dict
                        each_redist['rm_name'] = rm_name
                        del each_redist['allow']
                        del each_redist['metric']
                        if each_redist.get('switch') != None:
                            del each_redist['switch']
                        redist_tmp.append(each_redist)
            tenant[tnt['name']]['redist'] = redist_tmp

################################################## OSPF data-model creation ##################################################


        # DEVICE: Creates 2 dictionaries, a per-OSPF process dict of process settings and a per-interface dict of ospf interface settings
        ospf_proc, ospf_intf,  = ({} for i in range(2))
        for proc in ospf:
            # Set default values if the switch or default_orig key not specified.
            proc.setdefault('switch', [])               # Uses empty list
            proc.setdefault('default_orig', None)       # Uses None as is blank if referenced in template (instaed of 'always')
            # This dict and list are reset for each loop interation (ospf process)
            area_type_tmp = {}
            auth_tmp, summ_tmp, redist_tmp = ([] for i in range(3))

            #INTF: Creates dictionary and process config values for interfaces on this device (uses process switch if not defined)
            for intf in proc['interface']:
                # Only creates the new dictionaires if OSPF process or OSPF interface is on this switch
                if hostname in intf.setdefault('switch', proc['switch']):
                    # PROC: Creates OSPF proceess as a dictionary if on this switch
                    ospf_proc[proc['process']] = proc
                    # If it is special area (stub, nssa, etc) or uses authetication adds to temp_vars to be added to proc dict later
                    if intf.get('area_type') != None:
                        area_type_tmp[intf['area']] = intf['area_type']
                        del intf['area_type']
                    if intf.get('authetication') != None:
                        auth_tmp.append(intf['area'])

                    # INTF: Adds the process number to the dict of interfaces (key) and there OPSF configuration (value)
                    intf['proc'] = proc['process']
                    for each_intf in intf['name']:
                        # Changes the short interface name for full interface name
                        if bse_intf['intf_short'] in each_intf:
                            each_intf = each_intf.replace(bse_intf['intf_short'], bse_intf['intf_fmt'])
                        ospf_intf[each_intf] = intf

            # SUMM/REDIST: Creates dictionaries for summaries and redistributions on this device (uses process switch if not defined)
            if proc.get('summary') != None:
                for each_smry in proc['summary']:
                    if hostname in each_smry.setdefault('switch', proc['switch']):
                        summ_tmp.append(each_smry)
            if proc.get('redist') != None:
                for each_redist in proc['redist']:
                    if hostname in each_redist.setdefault('switch', proc['switch']):
                        redist_tmp.append(each_redist)

            # PROC: Adds the temp vars that were just created either as new (auth & area_type) or replacing existing (summ & redist)
            ospf_proc[proc['process']]['area_type'] = area_type_tmp
            auth = set(auth_tmp)
            ospf_proc[proc['process']]['auth'] = list(auth)
            ospf_proc[proc['process']]['summary'] = summ_tmp
            ospf_proc[proc['process']]['redist'] = redist_tmp


        for proc, cfg in ospf_proc.items():
            # Deletes interface and switch dicts from process as no longer needed
            del cfg['interface']
            del cfg['switch']
            # SUMMARY and REDIST: Creates new lists            Adds None for summary so in template can use the variable and it will be blank (saves if statements in jinja)
            if cfg.get('summary') != None:
                for each_smry in cfg['summary']:
                    del each_smry['switch']         # No longer needed
                    pfx_tmp = {}
                    # Creates list of dicts [{prfx: filter}, {prfx: filter}, etc] for each summary using None if it doenst exist
                    for pfx in each_smry['prefix']:
                        # pfx_tmp[pfx] = each_smry.get('filter', None)
                        pfx_tmp[pfx] = each_smry.setdefault('filter', None)
                    each_smry['prefix'] = pfx_tmp
                    del each_smry['filter']             # Deletes the filter as no longer needed

            # REDIST:
            if cfg.get('redist') != None:
                for each_redist in cfg['redist']:
                    del each_redist['switch']
                    # Creates the prefix-lists and route-maps before returning the RM name
                    rm_name = create_redist_rm_pfx_lst(each_redist['type'], 'OSPF' + str(proc), each_redist.setdefault('allow', None), each_redist.setdefault('metric', None), cfg['tenant'])
                    # Replace '_' for ' ' so is in correct format for when cmd is sued in the template
                    if '_' in each_redist['type']:
                        each_redist['type'] = each_redist['type'].replace('_', ' ')
                    # Add the route map name as a dictionary and remove 'allow' and 'metric'
                    each_redist['rm_name'] = rm_name
                    del each_redist['allow']
                    del each_redist['metric']


        # Cleanup the not-needed dicts (the switch list and interface list)
        for intf in ospf_intf.values():
            intf.pop('switches', None)
            intf.pop('name', None)


        # STATIC_ROUTES
        stc_rte = defaultdict(list)
        for grp in static_route:
            grp.setdefault('switch', [])
            for tnt in grp['tenant']:
                rte_tmp = []
                for each_route in grp['route']:
                    if hostname in each_route.setdefault('switch', grp['switch']):
                        # Create default values of None so can put in template but be empty if not specified
                        each_route.setdefault('interface', None)
                        each_route.setdefault('ad', None)
                        rte_tmp.append(each_route)
                stc_rte[tnt].extend(rte_tmp)

        # Cleanup the not-needed dicts (the switch list) and wap short intf name for full name
        for route in stc_rte.values():
            for each_route in route:
                each_route.pop('switch', None)
                if each_route['interface'] != None:
                    each_route['interface'] = each_route['interface'].replace(bse_intf['intf_short'], bse_intf['intf_fmt'])

        return [all_pfx_lst, all_rm, dict(groups), dict(peers), dict(tenant), ospf_proc, ospf_intf, dict(stc_rte)]
