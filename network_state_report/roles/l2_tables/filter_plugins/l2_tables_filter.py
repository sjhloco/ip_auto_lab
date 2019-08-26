class FilterModule(object):
    def filters(self):
        return {
            'l2_filter': self.l2_filter,
        }

 # Create a list of OSPF facts from the ospf output
    def l2_filter(self, genie_vlan, inventory_hostname, genie_mac, genie_pc):
        vlans = len(genie_vlan['vlans'].values())
        macs = 0
        up_pc = 0
        pc_members = 0
        up_pc_memb = 0
        # Counts the nummber of mac addresses
        for a in genie_mac['mac_table']['vlans'].values():  # For each vlan
            for b in a['mac_addresses']:                    # for each mac address
                macs += 1
        # Counts PCs, member ports and status
        configured_pc = len(genie_pc['interfaces'].values())
        for a in genie_pc['interfaces'].values():           # For every pc
            if a['oper_status'] == 'up':                     # Add up operational PCs
                up_pc += 1
        for a in genie_pc['interfaces'].values():            # For every pc
            for b in a['members'].values():                     # For each member port of a PC
                pc_members += 1                             # count them
                if b['flags'] == 'P':                       # For each up member port of a PC
                    up_pc_memb += 1                         # count them

        l2_table = [inventory_hostname, vlans, macs, configured_pc, up_pc, pc_members, up_pc_memb]
        return l2_table
