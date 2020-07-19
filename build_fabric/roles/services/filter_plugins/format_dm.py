from collections import defaultdict

class FilterModule(object):
    def filters(self):
        return {
            'create_svc_tnt_dm': self.svc_tnt_dm,
            'create_svc_intf_dm': self.svc_intf_dm,
            'create_svc_rtr_dm': self.svc_rtr_dm
        }


###################################### TNT DATA-MODEL: Uses input from service_tenant.yml ######################################
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



################################################## DRY Functions used by INTF DATA-MODEL ##################################################

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

###################################### INTF DATA-MODEL: Uses input from service_interface.yml ######################################
# Creates a per-device data model of all interfaces to be configured on that device

    def svc_intf_dm(self, all_homed, hostname, intf_adv, bse_intf):
        sl_hmd = intf_adv['single_homed']
        dl_hmd = intf_adv['dual_homed']
        intf_fmt = bse_intf['intf_fmt']
        lp_fmt = bse_intf['lp_fmt']
        ec_fmt = bse_intf['ec_fmt']
        tmp_all_intf, have_intf, sl_need_intf, dl_need_intf, all_intf_num, sl_range, dl_range, need_po, all_po_num, po_range = ([] for i in range(10))
        all_lp_num, lp_need_intf, lp_range = ([] for i in range(3))

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
                tmp_all_intf.append(intf)
        a = []
        # 2. FILTER:Creates new lists of all interfaces (all_intf_num, all_lp_num), intf with defined port (have_intf) and intf with non-defined ports (lp_need_intf, sl_need_intf, dh_need_intf)
        for intf in tmp_all_intf:
            # SH: Single-homed to be created if hostname is in the list of switches
            if intf['dual_homed'] == False and hostname in intf['switch']:
                # LP: Loopback interfaces to be created on this deivce
                if intf['type'] == 'loopback':
                    if intf['intf_num'] == None:
                        lp_need_intf.append(intf)                                   # List of loopbacks that dont have a number
                    elif intf['intf_num'] != None:
                        all_lp_num.append(intf['intf_num'])                         # List of all used loopback numbers
                        intf['intf_num'] = lp_fmt + str(intf['intf_num'])           # Adds the loopback name to the number
                        have_intf.append(intf)                                      # List of loopbacks that have a number
                # OTHER_SH: All other SH interfaces on this switch
                else:
                    if intf['intf_num'] == None:
                        sl_need_intf.append(intf)                                   # List of interfaces that need to be assigned an interface number
                    else:
                        all_intf_num.append(intf['intf_num'])                       # List of all used interface numbers
                        intf['intf_num'] = intf_fmt + str(intf['intf_num'])         # Adds the interface name to the number
                        have_intf.append(intf)                                      # List of interfaces that have an interface number
            # DH: Dual-homed interfaces need to be created on both MLAG pairs so logic matches both hostnames
            elif intf['dual_homed'] == True:
                if hostname in intf['switch'] or hostname[:-2] + "{:02d}".format(int(hostname[-2:]) -1) in intf['switch']:
                    if intf['intf_num'] == None:
                        dl_need_intf.append(intf)
                    else:
                        all_intf_num.append(intf['intf_num'])
                        intf['intf_num'] = intf_fmt + str(intf['intf_num'])
                        have_intf.append(intf)
            del intf['switch']                                                  # Removes as no longer needed

        # 3. INTF_RANGES: Adjust interface assignment ranges to remove any already used interfaces
        # Loopback
        for intf_num in range(sl_hmd['first_lp'], sl_hmd['last_lp'] + 1):
            lp_range.append(intf_num)
        lp_range = set(lp_range) - set(all_lp_num)
        lp_range = list(lp_range)
        lp_range.sort()
        # Single-homed
        for intf_num in range(sl_hmd['first_intf'], sl_hmd['last_intf'] + 1):
            sl_range.append(intf_num)
        sl_range = set(sl_range) - set(all_intf_num)
        sl_range = list(sl_range)
        sl_range.sort()
       # Dual-homed
        for intf_num in range(dl_hmd['first_intf'], dl_hmd['last_intf'] + 1):
            dl_range.append(intf_num)
        dl_range = set(dl_range) - set(all_intf_num)
        dl_range = list(dl_range)
        dl_range.sort()

        # 4. INTF_ASSIGN:  Assigns an interface number and adds that number to the existing interface DM
        # Loopback
        for intf, int_num in zip(lp_need_intf, lp_range):
            if intf['type'] == 'loopback':
                intf['intf_num'] = lp_fmt + str(int_num)
                have_intf.append(intf)
        # Single-homed
        for intf, int_num in zip(sl_need_intf, sl_range):
            if intf['dual_homed'] == False:
                intf['intf_num'] = intf_fmt + str(int_num)
                have_intf.append(intf)
        # Dual-homed
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


################################################## DRY Functions used by RTR DATA-MODEL ##################################################

# BGP_ATTR: Function to create the prefix-list and route-map data-models for BGP attribute associated prefixes (weight, local pref, med & AS-path)
    def create_bgpattr_rm_pfx_lst(self, input_data, direction, bgp_attr, pl_name, rm_name):
        # If a BGP attribute is defined in the dictionary for that direction (inbound or outbound) the input_data is processed by this method
        if input_data.get(direction, {}).get(bgp_attr) != None:
            # 1. LOOP: Loop through each attribute dictionary {bgp_attr_value: [pfx, pfx, etc]}
            for bgp_attr_value, all_pfx in input_data[direction][bgp_attr].items():
                # 2. INCRE: Increment RM seq number by 10 each BGP_attr (loop) and set starting PL sequence number (as each bgp_attr has its own PL)
                self.rm_seq += 10
                pl_seq = 0
                # 3. CREATE_PL: Creates a tuple (pl_name, seq, action, pfx) which is added to the list of all prefix-lists
                if isinstance(all_pfx, str) == True:
                    # If the BGP_ATTR is applied to only a default route (default keyword)
                    if all_pfx == 'default':
                        self.all_pfx_lst.append((pl_name.replace('val', str(bgp_attr_value)), pl_seq + 5, 'permit', '0.0.0.0/0'))
                    # If the BGP_ATTR is applied to any traffic (any keyword)
                    elif all_pfx == 'any':
                        self.all_pfx_lst.append((pl_name.replace('val', str(bgp_attr_value)), pl_seq + 5, 'permit', '0.0.0.0/0 le 32'))
                # If the BGP_ATTR is applied to a list of prefixes
                elif isinstance(all_pfx, list) == True:
                    for pfx in all_pfx:
                        # As is a list of multiple prefixes increments the prefix-list sequence number by 5 each loop
                        pl_seq += 5
                        self.all_pfx_lst.append((pl_name.replace('val', str(bgp_attr_value)), pl_seq, 'permit', pfx))
                # 4. CREATE_RM: Creates a tuple (rm_name, seq, pl_name, weight) which is added to the list of all route-maps
                self.all_rm.append((rm_name, self.rm_seq, pl_name.replace('val', str(bgp_attr_value)), (bgp_attr, bgp_attr_value)))

            # 5. CLEANUP: Removes the BGP attribute key:value, if inbound/outbound dict is now empty deletes
            del input_data[direction][bgp_attr]
            if input_data[direction] == {}:
                del input_data[direction]
            # 6. NEW_DICT: Adds a new dict for the direction of the filtering with route-map name as the key
            input_data[direction + '_rm'] = rm_name


# BGP ALLOW/DENY: Function to create the prefix-list and route-map for allowed and denied prefixes (added in RM order deny/allow_spec, allow_any/deny_any)
    def create_allowdeny_rm_pfx_lst(self, input_data, direction, pl_name, rm_name, dflt_pl):
        # If a 'allow' or 'deny' are defined in the dictionary for that direction (inbound or outbound) the input_data is processed by this method
        if input_data.get(direction, {}).get('allow') != None or input_data.get(direction, {}).get('deny') != None:
            # Sets starting PL seq. Will be same prefix-list for all allow_specific and deny_specific rules so also have same RM statement (seq)
            pl_seq = 0
            # 1. DENY_SPECIFIC: Loops DENY prefixes (will be a list) and adds a tuple entry to the list of all prefix-lists
            if input_data.get(direction, {}).get('deny') != None and isinstance(input_data.get(direction, {}).get('deny'), list) == True:
                # Increments the RM sequence, all the deny statements will be in prefix list associated to this 1 RM entry
                self.rm_seq += 10
                for pfx in input_data[direction]['deny']:
                    # Increments the PL sequence number by 5 for each prefix in the list (iteration of loop)
                    pl_seq += 5
                    # Adds the PL and RM entry at each prefix loop. The RM will alwasy be same so is just overwriting same entry each time.
                    self.all_pfx_lst.append((pl_name, pl_seq, 'deny', pfx))
                    self.all_rm.append((rm_name, self.rm_seq, pl_name, (None, None)))
            # 2. ALLOW_SPECIFIC: Loops through ALLOW prefixes and adds tuple entry to the list of all prefix-lists
            if input_data.get(direction, {}).get('allow') != None:
                if isinstance(input_data.get(direction, {}).get('allow'), list) == True:
                    # If the pl_seq has not been incremented it means the previous DENY if statment has not been matched, so needs to add the RM_seq and RM entry
                    if pl_seq == 0:
                        self.rm_seq += 10
                        self.all_rm.append((rm_name, self.rm_seq, pl_name, (None, None)))
                    for pfx in input_data[direction]['allow']:
                        pl_seq += 5
                        self.all_pfx_lst.append((pl_name, pl_seq, 'permit', pfx))
                # 3. ALLOW_DEFAULT: Has string of 'default route', uses pre-defined prefix list 'pl_default' in RM entry
                elif input_data.get(direction, {}).get('allow') == 'default':
                    self.rm_seq += 10
                    self.all_rm.append((rm_name, self.rm_seq, dflt_pl['pl_default'], (None, None)))
                # 4. ALLOW_ANY: Has string of 'any', uses pre-defined prefix list 'pl_allow' in RM entry
                elif input_data.get(direction, {}).get('allow') == 'any':
                    self.rm_seq += 10
                    self.all_rm.append((rm_name, self.rm_seq, dflt_pl['pl_allow'], (None, None)))
            # 5. DENY_ANY: Should always be last entry in route-map. Has string of 'any', uses pre-defined prefix list 'pl_deny' in RM entry
            if input_data.get(direction, {}).get('deny') != None and input_data.get(direction, {}).get('deny') == 'any':
                self.rm_seq += 10
                self.all_rm.append((rm_name, self.rm_seq, dflt_pl['pl_deny'], (None, None)))

            # 6. CLEANUP: If the inbound/ outbound dict exists it is deleted
            if input_data.get(direction) != None:
                del input_data[direction]
            # 7. NEW_DICT: Adds a new dict for the direction of the filtering with route-map name as the key
            input_data[direction + '_rm'] = rm_name


# REDISTRIBUTION: Function to create the prefix-list and route-map for prefixes to be redistributed and any changes to the metric.
    def create_redist_rm_pfx_lst(self, source, destination, allow_pfx, pfx_attr, tnt, rm_pl_name, dflt_pl):
        # 1a. EDIT_PL/RM_NAME: Joins routing protocol to the process/AS, shortens connected and adds VRF to BGP (or would have conflicts)
        if 'bgp_' in source:
            source = source.replace('_', '').upper() + '_' + tnt
        elif '_' in source:
            source = source.replace('_', '').upper()
        elif source == 'connected':
            source = 'conn'
        # Adds VRF to BGP name for the destination protocol (redistributing into BGP)
        if 'BGP' in destination:
            destination = destination.replace('_', '').upper() + '_' + tnt
        # 1b. RM_PL_NAMES: Creates names for all PL and RMs used by this function
        pl_name = rm_pl_name['pl_name'].replace('src', source).replace('dst', destination)
        rm_name = rm_pl_name['rm_name'].replace('src', source).replace('dst', destination)
        pl_metric_name = rm_pl_name['pl_metric_name'].replace('src', source).replace('dst', destination)

        rm_seq = 0
       # 2. NO PFX_LST: Creates blank RM with on matching prefix-list if both allow and metric not defined (redistribute all)
        if allow_pfx == None and pfx_attr == None:
            rm_seq += 10
            self.all_rm.append((rm_name, rm_seq, None, (None, None)))

        # 3. METRIC: Creates the PL and RM for any prefixes that are to be redistributed with a metric value
        elif pfx_attr != None:
            #LOOP: Loops through each metric:pfx(list) dixt creating a seperate PL and RM entry for each one
            for attr_value, all_pfx in pfx_attr.items():
                #SEQ: Increment RM seq number by 10 for each loop and resets the PL sequence number
                rm_seq += 10
                pl_seq = 0
                # 3a. DEFAULT: If redistributing only default route (default keyword) with a metric value
                if isinstance(all_pfx, str) == True and all_pfx == 'default':
                    self.all_pfx_lst.append((pl_metric_name.replace('val', str(attr_value)), pl_seq + 5, 'permit', '0.0.0.0/0'))
                # 3b. ANY: If redistributing only all prefixes (any keyword) with a metric value
                elif isinstance(all_pfx, str) == True and all_pfx == 'any':
                    self.all_pfx_lst.append((pl_metric_name.replace('val', str(attr_value)), pl_seq + 5, 'permit', '0.0.0.0/0 le 32'))
                # 3c. PREFIXES: Adds all prefixes in the list to the one PL, incrementing the prefix-list sequence number by 5 each loop
                else:
                    for pfx in all_pfx:
                        pl_seq += 5
                        self.all_pfx_lst.append((pl_metric_name.replace('val', str(attr_value)), pl_seq, 'permit', pfx))
                # 3c, RM: Adds a tuple (rm_name, seq, pl_name, (metric, metric_value)) to list of all route-maps
                self.all_rm.append((rm_name, rm_seq, pl_metric_name.replace('val', str(attr_value)), ('metric', attr_value)))

        # 4a. ALLOW_DFLT: Adds 10 to the rm_seq and adds a RM entry with the predefind 'default' PL (no metric)
        if allow_pfx == 'default':
            rm_seq += 10
            self.all_rm.append((rm_name, rm_seq, dflt_pl['pl_default'], (None, None)))
        # 4b. ALLOW_ANY: Adds 10 to the rm_seq and adds a RM entry with the predefind 'any' PL (no metric)
        elif allow_pfx == 'any':
            rm_seq += 10
            self.all_rm.append((rm_name, rm_seq, dflt_pl['pl_allow'], (None, None)))
        # 4c. CONN: RM_SEQ starts at 20 as RM already exists (created in svc_tnt). No PL so adds interfaces in its place in the RM list
        elif allow_pfx != None and source == 'conn':
            rm_seq += 20                                                                    # 20 as redist in tenant (tag of SVIs in tnt) is 10
            self.all_rm.append((rm_name, rm_seq, ' '.join(allow_pfx), (None, None)))        # Adds interfaces rather than PL name
        # 4d. ALLOW: Creates PL of all prefixes (seq 5 between) and adds 10 to the rm_seq before adding a RM entry (no metric)
        elif allow_pfx != None:
            pl_seq = 0
            for pfx in allow_pfx:
                pl_seq += 5
                self.all_pfx_lst.append((pl_name, pl_seq, 'permit', pfx))
            rm_seq += 10
            self.all_rm.append((rm_name, rm_seq, pl_name, (None, None)))

        # 5. Returns the RM name back to be added to the  BGP or OSPF redist dictionary
        return rm_name


###################################### RTR DATA MODEL: Uses input from service_routing.yml ######################################
# Creates 7 data models for Prefix-lists, Route-maps, BGP groups, BGP peers, BGP tenants (network, summary, redist), OSPF processes, OSPF interfaces and static routes

    def svc_rtr_dm(self, hostname, bgp_grps, bgp_tnt, ospf, static_route, adv, fbc):
        # These hold ALL prefix-lists and route-maps created by the external methods for all elements of BGP and OSPF (filtering, path manipulation & redistribution)
        self.all_pfx_lst, self.all_rm = ([] for i in range(2))

################################ BGP data models ################################
        pl_rm_name = adv['bgp']['naming']
        bse_intf = fbc['adv']['bse_intf']
        as_num = fbc['route']['bgp']['as_num']
        peer = defaultdict(list)
        group, tenant = (defaultdict(dict) for i in range(2))

        # 1. CREATE_DICT: Creates a dictionary of Groups (key is grp_name) and a dictionary of peer (key is vrf_name) on this device.
        for grp in bgp_grps:
            # DFLT_VAL: Set default values if the switch or tenant keys are not specified in group
            grp.setdefault('switch', [])
            grp.setdefault('tenant', None)

            # 1a. PEER_FMT: Formatting in preparation to create the peer dictionary
            for each_peer in grp['peer']:
                # DFLT_VAL: If switch or tenant is not specified in peer adds the group values
                if hostname in each_peer.setdefault('switch', grp['switch']):
                    each_peer.setdefault('tenant', grp['tenant'])
                    # Adds new dict for group name, removes switch (no longer needed) and pops tenanat to use in creating next peer dict
                    each_peer['grp'] = grp['name']
                    del each_peer['switch']
                    tnt = each_peer.pop('tenant')
                    # PEER_DICT: Creates new dictionary of VRFs with the values being lists of the peer dictionaries within that VRF
                    for each_tnt in tnt:
                        peer[each_tnt].append(each_peer.copy())  # Needs a copy or you cant edit later as mutable (same object reference multiple times)

                    # 1b. GROUP_DICT: Creates new dictionary with the Key the name of the group/templates and the values being its attributes
                    group[grp['name']]['timers'] = grp.setdefault('timers', adv['bgp']['timers'])     # Sets default BGP timers for groups if not specified
                    group[grp['name']] = grp

        # 2. RM_GROUP: Loop through each group to create the prefix-lists and route-maps for allow/deny and BGP attributes
        for grp in group.values():
            # CLEANUP: No need for the switch, tenant and peer dictionaries anymore
            del grp['switch'], grp['peer'], grp['tenant']
            # INBOUND: Runs functions to create prefix-lists and route maps for inbound traffic control. Allow/Deny is run after the BGP attributes have been added
            self.rm_seq = 0         # All below filters in same RM, so incremented in each method (why has to be self. and not passed in as an arg)
            self.create_bgpattr_rm_pfx_lst(grp, 'inbound', 'weight', pl_rm_name['pl_wght_in'].replace('name', grp['name']), pl_rm_name['rm_in'].replace('name', grp['name']))
            self.create_bgpattr_rm_pfx_lst(grp, 'inbound', 'pref', pl_rm_name['pl_pref_in'].replace('name', grp['name']), pl_rm_name['rm_in'].replace('name', grp['name']))
            self.create_allowdeny_rm_pfx_lst(grp, 'inbound', pl_rm_name['pl_in'].replace('name', grp['name']), pl_rm_name['rm_in'].replace('name', grp['name']), adv['dflt_pl'])
            # OUTBOUND: Runs functions on inbound methods to create prefix-lists and route maps for inbound traffic control
            self.rm_seq = 0
            self.create_bgpattr_rm_pfx_lst(grp, 'outbound', 'med', pl_rm_name['pl_med_out'].replace('name', grp['name']), pl_rm_name['rm_out'].replace('name', grp['name']))
            self.create_bgpattr_rm_pfx_lst(grp, 'outbound', 'as_prepend', pl_rm_name['pl_aspath_out'].replace('name', grp['name']), pl_rm_name['rm_out'].replace('name', grp['name']))
            self.create_allowdeny_rm_pfx_lst(grp, 'outbound', pl_rm_name['pl_out'].replace('name', grp['name']), pl_rm_name['rm_out'].replace('name', grp['name']), adv['dflt_pl'])

        # 3. RM_PEER: Loop through each group to create the prefix-lists and route-maps for allow/deny and BGP attributes
        for all_pr in peer.values():
            for pr in all_pr:
                # INBOUND: Runs functions to create prefix-lists and route maps for inbound traffic control. Allow/Deny is run after the BGP attributes have been added
                self.rm_seq = 0
                self.create_bgpattr_rm_pfx_lst(pr, 'inbound', 'weight', pl_rm_name['pl_wght_in'].replace('name', pr['name']), pl_rm_name['rm_in'].replace('name', pr['name']))
                self.create_bgpattr_rm_pfx_lst(pr, 'inbound', 'pref', pl_rm_name['pl_pref_in'].replace('name', pr['name']), pl_rm_name['rm_in'].replace('name', pr['name']))
                self.create_allowdeny_rm_pfx_lst(pr, 'inbound', pl_rm_name['pl_in'].replace('name', pr['name']), pl_rm_name['rm_in'].replace('name', pr['name']), adv['dflt_pl'])
                # OUTBOUND: Runs functions on inbound methods to create prefix-lists and route maps for inbound traffic control
                self.rm_seq = 0
                self.create_bgpattr_rm_pfx_lst(pr, 'outbound', 'med', pl_rm_name['pl_med_out'].replace('name', pr['name']), pl_rm_name['rm_out'].replace('name', pr['name']))
                self.create_bgpattr_rm_pfx_lst(pr, 'outbound', 'as_prepend', pl_rm_name['pl_aspath_out'].replace('name', pr['name']), pl_rm_name['rm_out'].replace('name', pr['name']))
                self.create_allowdeny_rm_pfx_lst(pr, 'outbound', pl_rm_name['pl_out'].replace('name', pr['name']), pl_rm_name['rm_out'].replace('name', pr['name']), adv['dflt_pl'])

        # 4. PFX_LST_RM_CLEANUP: Get rid of any duplicates casued by using same peer in multiple VRFs
        self.all_pfx_lst = set(self.all_pfx_lst)
        self.all_pfx_lst = list(self.all_pfx_lst)
        self.all_pfx_lst.sort()
        self.all_rm = set(self.all_rm)
        self.all_rm = list(self.all_rm)
        self.all_rm.sort()

        ### Summary, Network and redistribution are configured on a per tenant (VRF) rather than per-group or per-peer basis ###
        for tnt in bgp_tnt:
            # 5a. TMP_VARS: Collect all information for that element per-teant, so reset at each interation
            summ_tmp = {}
            net_tmp, redist_tmp = ([] for i in range(2))
            # 5b. DFLT_VAL: If switch is not specified in for the tnt uses emtpy list (needed to allow using tenant switch as the default)
            tnt.setdefault('switch', [])           # Uses empty list if switch not specified,

            # 6a. NETWORK: Replaces 'network' dict with just those on to be added on this devices
            if tnt.get('network') != None:
                for pfx in tnt['network']:
                    if hostname in pfx.setdefault('switch', tnt['switch']):
                        net_tmp.extend(pfx['prefix'])
            tenant[tnt['name']]['network'] = net_tmp
            # 6b. SUMMARY: Replaces 'summary' dict with just those on to be added on this devices. Add dummy value for summary if doesnt have one
            if tnt.get('summary') != None:
                for pfx in tnt['summary']:
                    if hostname in pfx.setdefault('switch', tnt['switch']):
                        for each_pfx in pfx['prefix']:
                             summ_tmp[each_pfx] = pfx.setdefault('filter', None)
            tenant[tnt['name']]['summary'] = summ_tmp

            # 7. REDIST: Replaces 'redist' dict with just those on to be added on this devices and extra element with rm_name
            if tnt.get('redist') != None:
                for each_redist in tnt['redist']:
                    if hostname in each_redist.setdefault('switch', tnt['switch']):
                        # 7a. CREATE PL/RM: Runs functions to create the prefix-lists and route maps used with redist. The RM name is returned
                        rm_name = self.create_redist_rm_pfx_lst(each_redist['type'], 'BGP' + str(as_num), each_redist.setdefault('allow', None), each_redist.setdefault('metric', None), tnt['name'], adv['redist'], adv['dflt_pl'])
                        # 7b. RENAME & CLEANUP: Replace '_' for ' ' so is in correct format for when cmd is used in the jinja template
                        if '_' in each_redist['type']:
                            each_redist['type'] = each_redist['type'].replace('_', ' ')
                        del each_redist['allow'], each_redist['metric'], each_redist['switch']
                        # 7c. UPDATE_DICT: Add RM_name to orignal dict before adding that dict to the new tenant dictioanry
                        each_redist['rm_name'] = rm_name
                        redist_tmp.append(each_redist)
            tenant[tnt['name']]['redist'] = redist_tmp

################################ OSPF data-model creation ################################

        # Creates 2 dictionaries, a per-OSPF process dict of process settings and a per-interface dict of ospf interface settings
        ospf_proc, ospf_intf,  = ({} for i in range(2))

        for proc in ospf:
            # 1a. TMP_VARS: The dict and lists are reset for each loop interation (ospf process)
            area_type_tmp = {}
            auth_tmp, summ_tmp, redist_tmp = ([] for i in range(3))
            # 1b. DFLT_VAL: Set default values if the switch or default_orig keys are not specified in the process
            proc.setdefault('switch', [])               # Uses empty list
            proc.setdefault('default_orig', None)       # Uses None as is blank if referenced in template (instaed of 'always')

            #1c. LOOP: Loops through each interface in the process, only creates the new dicts if OSPF process orinterface is on this switch
            for intf in proc['interface']:
                if hostname in intf.setdefault('switch', proc['switch']):
                    # 2. PROC_DICT: Uses OSPF process number as the key and its settings as the value in the new process dictionary
                    ospf_proc[proc['process']] = proc
                    # 2a. PROC_ATTR: If it is special area (stub, nssa, etc) or uses authetication adds to temp_vars to be added to process dict later
                    if intf.get('area_type') != None:
                        area_type_tmp[intf['area']] = intf['area_type']
                        del intf['area_type']
                    if intf.get('authetication') != None:
                        auth_tmp.append(intf['area'])

                    # 3. INTF_PROC: Adds the process number to the existing interfaces dictionary
                    # intf.pop('switches', None)
                    intf['proc'] = proc['process']
                    for each_intf in intf['name']:
                        # 3a. INTF_NAME: Changes the short interface name for full interface name
                        if bse_intf['intf_short'] in each_intf:
                            each_intf = each_intf.replace(bse_intf['intf_short'], bse_intf['intf_fmt'])
                        # 3c. INTF_DICT: Uses Interface name as the key and its OSPF settings as the value in the new process dictionary
                        ospf_intf[each_intf] = intf

            # 4a. TMP_SUMM/REDIST: Creates temp lists of summary and redist dictionaries on this device (uses process switch if switch not defined)
            if proc.get('summary') != None:
                for each_smry in proc['summary']:
                    if hostname in each_smry.setdefault('switch', proc['switch']):
                        summ_tmp.append(each_smry)
            if proc.get('redist') != None:
                for each_redist in proc['redist']:
                    if hostname in each_redist.setdefault('switch', proc['switch']):
                        redist_tmp.append(each_redist)

            # 4b. PROC_ATTR: Adds to the process dict the temp_vars that were created either as new dicts or replacing existingdicts
            if ospf_proc.get(proc['process']) != None:                                  # Required incase a device doesnt have a OSPF process
                ospf_proc[proc['process']]['area_type'] = area_type_tmp                 # Adds area type as new dict
                auth = set(auth_tmp)                                                    # Needs to first get rid of duplicates
                ospf_proc[proc['process']]['auth'] = list(auth)                         # Adds area type as new dict
                ospf_proc[proc['process']]['summary'] = summ_tmp                        # Replaces existing summary with device-specific summary
                ospf_proc[proc['process']]['redist'] = redist_tmp                       # Replaces existing redist with device-specific redist

        # 5. INTF_CLEANUP: Remove the not-needed dicts. Couldnt be done earlier as can have muliple intefraces with same config
        for intf in ospf_intf.values():
            intf.pop('switch', None)
            intf.pop('name', None)

        for proc, cfg in ospf_proc.items():
            # CLEANUP: Deletes interface and switch dicts from process as no longer needed
            del cfg['interface'], cfg['switch']
             # 6. SUMMARY: Creates list of dicts [{prfx: filter}, {prfx: filter}, etc] for each summary, uses 'None; if filter doenst exist
            if cfg.get('summary') != None:
                for each_smry in cfg['summary']:
                    pfx_tmp = {}
                    for pfx in each_smry['prefix']:
                        pfx_tmp[pfx] = each_smry.setdefault('filter', None)
                    # 6b. UPDATE_DICT: Replaces existing summary dictionary value with new one
                    each_smry['prefix'] = pfx_tmp
                     # 6c. CLEANUP: Delete no longer needed dictionaries
                    del each_smry['filter'], each_smry['switch']

            # 7a. REDIST: Replaces 'redist' dict with just those on to be added on this devices and extra element with rm_name
            if cfg.get('redist') != None:
                for each_redist in cfg['redist']:
                    # CREATE PL/RM: Runs functions to create the prefix-lists and route maps used with redist. The RM name is returned
                    rm_name = self.create_redist_rm_pfx_lst(each_redist['type'], 'OSPF' + str(proc), each_redist.setdefault('allow', None), each_redist.setdefault('metric', None), cfg['tenant'], adv['redist'], adv['dflt_pl'])
                    # 7b. RENAME & CLEANUP: Replace '_' for ' ' so is in correct format for when cmd used in template, delete uneeded dictionaries
                    if '_' in each_redist['type']:
                        each_redist['type'] = each_redist['type'].replace('_', ' ')
                    del each_redist['allow'], each_redist['metric'], each_redist['switch']

                    # 7c. UPDATE_DICT: Adds RM name to the existing redist dictioanry
                    each_redist['rm_name'] = rm_name


################################ Static route data-model creation ################################

        # Creates a new dictionary {vrf: [rte_details], vrf: [rte_details]} of routes per VRF
        stc_rte = defaultdict(list)
        for grp in static_route:
            # 1. DFLT_VAL: Set default values for the switch if not specified in the VRF
            grp.setdefault('switch', [])
            # 2. LOOP_TNT: Loops through the tenants resetting the temp_var each time so it is a list of routes only on that tenant
            for tnt in grp['tenant']:
                rte_tmp = []
                # 3. LOOP_RTE: Loops through routes finding those on this device, uses the switch from the tenant if not specified
                for each_route in grp['route']:
                    if hostname in each_route.setdefault('switch', grp['switch']):
                        # 4. DFLT_VAL: Creates default values of None so can put added in JINJA template but be empty if that option is not configured
                        each_route.setdefault('interface', None)
                        each_route.setdefault('ad', None)
                        # 5a. ADD_TEMP_VAR: Adds all routes into the temp_var list
                        rte_tmp.append(each_route)
                #5b. ADD_DICT: If are routes in a VRF adds new dict of {vrf: rte_details} to the new dictionary
                if len(rte_tmp) != 0:
                    stc_rte[tnt].extend(rte_tmp)

        # 6. CLEANUP: Deletes switch (couldnt do in last loop if route used by muliple tenants) and swap short intf name for full intf name
        for route in stc_rte.values():
            for each_route in route:
                each_route.pop('switch', None)
                if each_route['interface'] != None:
                    each_route['interface'] = each_route['interface'].replace(bse_intf['intf_short'], bse_intf['intf_fmt'])


#### Output returned back to asnible to be used in the jinja2 template
        return [self.all_pfx_lst, self.all_rm, dict(group), dict(peer), dict(tenant), ospf_proc, ospf_intf, dict(stc_rte)]
