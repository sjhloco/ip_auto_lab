class FilterModule(object):
    def filters(self):
        return {
            'ospf_filter': self.ospf_filter,
        }

 # Create a list of OSPF facts from the ospf output
    def ospf_filter(self, ospf_output, inventory_hostname, ospf_neigh):
        up_ospf_neigh = 0
        ospf_lsa = 0
        for a in ospf_output[0]['stdout'].splitlines():  # Counts number of lines
            up_ospf_neigh += 1
        for a in ospf_output[1]['stdout'].splitlines():
            ospf_lsa = ospf_lsa + int(a.split('Total')[1].strip().split(' ')[0])      # Gets just decimal number fo LSAs and Adds
        ospf_table = [inventory_hostname, ospf_neigh, up_ospf_neigh, ospf_lsa]
        return ospf_table
