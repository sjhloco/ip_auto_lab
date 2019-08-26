import json

class FilterModule(object):
    def filters(self):
        return {
            'bgp_filter': self.neigh_filter,
            'csr_bgp_filter': self.csr_neigh_filter
        }

 # Create a list of BGP facts from the bgp output (naplam)
    def neigh_filter(self, bgp_output, inventory_hostname, bgp_neigh):
        enabled_bgp_neigh = 0
        up_bgp_neigh = 0
        bgp_pfxrcd = 0
        for a in bgp_output['napalm_bgp_neighbors'].values():      # for each vrf
            for b in a['peers'].values():                   # for each neighbor
                if b["is_enabled"] is True:
                    enabled_bgp_neigh += 1
                if b["is_up"] is True:
                    up_bgp_neigh += 1                       # Adds up all up neighbors
                    #z.append(b["is_enabled"])
                for c in b['address_family'].values():      # for each address-family
                    bgp_pfxrcd = bgp_pfxrcd + int(c['received_prefixes'])       # Adds up all the prefixes
        bgp_table = [inventory_hostname, bgp_neigh, enabled_bgp_neigh, up_bgp_neigh, bgp_pfxrcd]
        return bgp_table

 # Create a list of BGP facts from the bgp output (genie cli)
    def csr_neigh_filter(self, bgp_output, inventory_hostname, bgp_neigh):
        enabled_bgp_neigh = 0
        up_bgp_neigh = 0
        bgp_pfxrcd = 0
        z = []
        bgp_output1 = json.loads(bgp_output)        # required to convert ansible input "<class 'dict'>"
        for a in bgp_output1['vrf'].values():      # for each vrf
            for b in a['neighbor'].values():                # for each neighbor
                enabled_bgp_neigh += 1                       # Adds up all up neighbors
                for c in b['address_family'].values():      # for each address-family
                    if (c['state_pfxrcd']).isdigit() is True:   # If prexix count is a decimal value
                        up_bgp_neigh += 1                   # Adds 1 if neighbor is up
                        bgp_pfxrcd = bgp_pfxrcd + int(c['state_pfxrcd'])    # Adds up the prefixes

        bgp_table = [inventory_hostname, bgp_neigh, enabled_bgp_neigh, up_bgp_neigh, bgp_pfxrcd]
        return bgp_table
