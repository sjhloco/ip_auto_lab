class FilterModule(object):
    def filters(self):
        return {
            'itf_filter': self.itf_filter,
        }

 # Create a list of OSPF facts from the ospf output
    def itf_filter(self, itf_output, inventory_hostname):
        enabled_int = 0
        up_int = 0
        # Needed as ASA output doesnt have lldp neighbors so stops erroring
        if len(itf_output) == 1:
            lldp_neigh = 0
        elif len(itf_output) == 2:
            lldp_neigh = len(itf_output[1]['ansible_facts']['napalm_lldp_neighbors'])
        # Counting enabled and up interfaces
        for a in itf_output[0]['ansible_facts']['napalm_interfaces'].values():
            if a['is_enabled'] is True:
                enabled_int += 1
            if a['is_up'] is True:
                up_int += 1
        interface_table = [inventory_hostname, enabled_int, up_int, lldp_neigh]
        return interface_table
