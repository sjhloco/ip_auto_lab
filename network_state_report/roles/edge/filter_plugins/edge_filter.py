class FilterModule(object):
    def filters(self):
        return {
            'edge_filter': self.edge_filter,
        }

 # Create a list of OSPF facts from the ospf output
    def edge_filter(self, edge_output, inventory_hostname, os, vpn_peer):
        # Filter commands run on ASA outouts
        vpn_cnt = 0
        if os == 'asa':
            nat_cnt = int(edge_output['show xlate count'].split(' ')[0])
            for a in edge_output['show vpn-sessiondb l2l'].splitlines():
                if 'Connection' in a:
                    vpn_cnt += 1
        # Filter commands run on CSR outouts            
        elif os == 'ios':
            nat_cnt = int(edge_output['show ip nat translations total'].split(' ')[-1])
            for a in edge_output['show crypto session'].splitlines():
                if 'UP-ACTIVE' in a:
                    vpn_cnt += 1
        edge_table = [inventory_hostname, vpn_peer, vpn_cnt, nat_cnt]
        return edge_table
