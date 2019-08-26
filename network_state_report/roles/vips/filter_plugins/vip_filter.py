class FilterModule(object):
    def filters(self):
        return {
            'vip_filter': self.vip_filter,
        }

 # Create a list of OSPF facts from the ospf output
    def vip_filter(self, vip_output, inventory_hostname):
        enabled_vip = 0
        up_vip = 0
        total_node = 0
        up_node = 0

        # Count total and up VIPs
        for a in vip_output['virtual_servers']:
            if a['enabled'] == 'yes':
                enabled_vip += 1
            if a['availability_status'] == 'available':
                up_vip += 1

        # Count total and up Nodes
        for b in vip_output['ltm_pools']:
            total_node = total_node + int(b['member_count'])
        for b in vip_output['ltm_pools']:
            up_node = up_node + int(b['active_member_count'])

        vip_table = [inventory_hostname, enabled_vip, up_vip, total_node, up_node]
        return vip_table
