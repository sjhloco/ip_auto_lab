from prettytable import PrettyTable

class FilterModule(object):
    def filters(self):
        return {
            'bgp_table': self.bgp_table,
            'edge_table': self.edge_table,
            'interface_table': self.interface_table,
            'l2_table': self.l2_table,
            'l3_table': self.l3_table,
            'ospf_table': self.ospf_table,
            'vip_table': self.vip_table
        }

    def bgp_table(self, list_bgp_table):
        bgp_table = PrettyTable()
        bgp_table.field_names = ['Device', 'Expected Peers', 'Enabled Peers', 'UP Peers', 'pfxrcd']
        bgp_table.align['Information'] = 'l'
        if type(list_bgp_table[0]) is list:      # If is a list of list iterate
            for x in list_bgp_table:
                bgp_table.add_row(x)
        else:
            bgp_table.add_row(list_bgp_table)
        output = '=' * 5 + ' BGP Table ' + '=' * 5 + '\n\n{}\n\n'.format(bgp_table)
        return output

    def edge_table(self, list_edge_table):
        edge_table = PrettyTable()
        edge_table.field_names = ['Device', 'Total L2L VPNs', 'Up L2L VPNs', 'Total NAT Translations']
        edge_table.align['Information'] = 'l'
        if type(list_edge_table[0]) is list:      # If is a list of list iterate
            for x in list_edge_table:
                edge_table.add_row(x)
        else:
            edge_table.add_row(list_edge_table)    # If single list add to table
        output = '=' * 5 + ' XNET Edge Table ' + '=' * 5 + '\n\n{}\n\n'.format(edge_table)
        return output

    def l2_table(self, list_l2_table):
        l2_table = PrettyTable()
        l2_table.field_names = ['Device', 'VLANs', 'MACs', 'cfg POs', 'UP POs',  'PO member ports', 'UP PO member ports']
        l2_table.align['Information'] = 'l'
        if type(list_l2_table[0]) is list:      # If is a list of list iterate
            for x in list_l2_table:
                l2_table.add_row(x)
        else:
            l2_table.add_row(list_l2_table)    # If single list add to table
        output = '=' * 5 + ' Layer2 Table ' + '=' * 5 + '\n\n{}\n\n'.format(l2_table)
        return output

    def l3_table(self, list_l3_table):
        l3_table = PrettyTable()
        l3_table.field_names = ['Device', 'ARP Table', 'Routing Table']
        l3_table.align['Information'] = 'l'
        if type(list_l3_table[0]) is list:      # If is a list of list iterate
            for x in list_l3_table:
                l3_table.add_row(x)
        else:
            l3_table.add_row(list_l3_table)    # If single list add to table
        output = '=' * 5 + ' Layer3 Table ' + '=' * 5 + '\n\n{}\n\n'.format(l3_table)
        return output

    def interface_table(self, list_interface_table):
        interface_table = PrettyTable()
        interface_table.field_names = ['Device', 'Enabled Interfaces', 'UP Interfaces', 'LLDP Neighbors']
        interface_table.align['Information'] = 'l'
        if type(list_interface_table[0]) is list:      # If is a list of list iterate
            for x in list_interface_table:
                interface_table.add_row(x)
        else:
            interface_table.add_row(list_interface_table)
        output = '=' * 5 + ' Interface Table ' + '=' * 5 + '\n\n{}\n\n'.format(interface_table)
        return output

    def ospf_table(self, list_ospf_table):
        ospf_table = PrettyTable()
        ospf_table.field_names = ['Device', 'Expected Neighors', 'UP Neighbors', 'Total LSAs']
        ospf_table.align['Information'] = 'l'
        if type(list_ospf_table[0]) is list:      # If is a list of list iterate
            for x in list_ospf_table:
                ospf_table.add_row(x)
        else:
            ospf_table.add_row(list_ospf_table)
        output = '=' * 5 + ' OSPF Table ' + '=' * 5 + '\n\n{}\n\n'.format(ospf_table)
        return output

    def vip_table(self, list_vip_table):
        vip_table = PrettyTable()
        vip_table.field_names = ['Device', 'Enabled VIPs', 'UP VIPs', 'Total Nodes', 'UP Nodes']
        vip_table.align['Information'] = 'l'
        if type(list_vip_table[0]) is list:      # If is a list of list iterate
            for x in list_vip_table:
                vip_table.add_row(x)
        else:
            vip_table.add_row(list_vip_table)
        output = '=' * 5 + ' VIP Table ' + '=' * 5 + '\n\n{}\n\n'.format(vip_table)
        return output

####################################### Used for testing a table #######################################
    # def def table(self, list_interface_table):
    #     return
