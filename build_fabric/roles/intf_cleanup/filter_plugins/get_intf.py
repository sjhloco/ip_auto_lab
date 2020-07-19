'''
Decleratively cleans up all interfaces not used by ensuring config is the default.
'''

class FilterModule(object):
    def filters(self):
        return {
            'get_intf': self.get_intf
        }

    def get_intf(self, hostvar, bse_intf, svc_intf):
        intf_fmt = bse_intf['intf_fmt']
        used_intf, total_intf, left_intf = ([] for i in range(3))

        # ACTUAL_INTF: Uses the value specified in fbc.num_intf to create a list of all possible interfaces on the device
        first_intf = int(hostvar['num_intf'].split(',')[0])
        last_intf = int(hostvar['num_intf'].split(',')[1]) + 1     # Needs +1 as range doesnt include last number

        # Creates list of all possible interfaces on the device
        for intf in range(first_intf, last_intf):
            total_intf.append(bse_intf['intf_fmt'] + (str(intf)))

        # INTF_FBC: Creates a list of the fabric interfaces, are got from the inventory
        for intf in hostvar['intf_fbc'].keys():
             if intf_fmt in  intf:
                used_intf.append(intf)
        # INTF_MLAG: Creates a list of the MLAG interfaces, are got from the inventory
        if hostvar.get('intf_mlag') != None:                # get required as Spine wont have int_mlag dict
            for intf in hostvar['intf_mlag'].keys():
                 if intf_fmt in intf:
                    used_intf.append(intf)
        # SVC_INTF: Creates a list of the physical interfaces (not PO or LP), are got from *svc_intf_dm* method in *format_dm.py* custom filter plugin
        if svc_intf != None:
            for intf in svc_intf:
                # if ec_fmt not in intf['intf_num'] or lp_fmt not in intf['intf_num']:
                if intf_fmt in intf['intf_num']:
                    used_intf.append(intf['intf_num'])

        #COMPARE: Gets just the none duplicates from both lists, so the interfaces not used
        left_intf  = list(set(total_intf) ^ set(used_intf))
        left_intf.sort()

        return left_intf