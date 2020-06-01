'''
Decleratively cleans up all interfaces not used by ensuring config is the default.
'''

class FilterModule(object):
    def filters(self):
        return {
            'get_intf': self.get_intf
        }

    def get_intf(self, hostvar, bse_intf, svc_intf):
        intf_mlag = hostvar.get('intf_mlag')       # As Spine wont have int_mlag dict
        ec_fmt = bse_intf['ec_fmt']
        first_intf = int(hostvar['num_intf'].split(',')[0])
        last_intf = int(hostvar['num_intf'].split(',')[1]) + 1     # Needs +1 as range doesnt include last number
        used_intf, total_intf, left_intf = ([] for i in range(3))

        # Go through each list of interfaces creating a new list of all interfaces
        for intf in hostvar['intf_fbc'].keys():
            if ec_fmt not in intf:
                used_intf.append(intf)
        if intf_mlag != None:
            for intf in intf_mlag.keys():
                if ec_fmt not in intf:
                    used_intf.append(intf)
        if svc_intf != None:
            for intf in svc_intf:
                if ec_fmt not in intf['intf_num']:
                    used_intf.append(intf['intf_num'])

        # Creates list of all possible interfaces on the device
        for intf in range(first_intf, last_intf):
            total_intf.append(bse_intf['intf_fmt'] + (str(intf)))

        # Gets just none duplicates, so the interfaces not used
        left_intf  = list(set(total_intf) ^ set(used_intf))
        left_intf.sort()

        return left_intf