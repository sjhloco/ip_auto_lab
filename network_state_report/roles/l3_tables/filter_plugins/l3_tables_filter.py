class FilterModule(object):
    def filters(self):
        return {
            'l3_filter': self.l3_filter,
        }

 # Create a list of OSPF facts from the ospf output
    def l3_filter(self, l3_output, inventory_hostname):
        if l3_output[0]['item'] == "show ip arp summary":   # If is CSR output
            arps = int(l3_output[0]['stdout'].split(' ')[0].strip())
        else:               # All other devicest
            arps = int(l3_output[0]['stdout'].split(':')[1].strip())
        # Routing table entries are cacluated by counting the number of lines
        routes = len(l3_output[1]['stdout'].splitlines())
        l3_table = [inventory_hostname, arps, routes]
        return l3_table
