
from collections import Counter
from ipaddress import ip_network

class FilterModule(object):
    def filters(self):
        return {
            'srv_tenants_dm': self.srv_tenants_dm,
            'srv_ports_dm': self.srv_ports_dm
        }

 # Create a new tenants data model including VNI info
    def srv_tenants_dm(self, srv_tenants, base_vni):
        # Create variables from imported nested variables
        l3vni = base_vni['l3vni']
        tn_vlan = base_vni['tn_vlan']
        l2vni = base_vni['l2vni']

        for tn in srv_tenants:
            # If a tenant is L3 (has VRF) adds the VLAN and L3VNI for it to the dictionary
            if tn['l3_tenant'] is True:
                tn['l3vni'] = l3vni
                tn['tn_vlan'] = tn_vlan
            # For each L3 tenant increases VLAN and L3VNOI by 1
            l3vni = l3vni + 1
            tn_vlan = tn_vlan + 1
            # For each VLAN createsa L2VNI by adding vlan num to base VNI
            for vl in tn['vlans']:
                vl['l2vni'] = l2vni + vl['num']
            # For each tenant increments the L2VNI by 10000
            l2vni = l2vni + 10000

        # If any SVIs are redistrbuted into BGP creates the new tenant 'redist' dictionary
        for tn in srv_tenants:
            if tn['l3_tenant'] is True:
                for vl in tn['vlans']:
                    if vl['ipv4_bgp_redist'] == True:
                        tn['redist'] = True

        # Dictionary returned back to Ansible
        return srv_tenants

 # Create a new ports data model including interface and Po info
    def srv_ports_dm(self, srv_ports, srv_ports_adv, srv_tenants):
        ### 1. First need to create seperate lists for single and dual homed so can use loop index to increment interafce number ###
        sh_ports = []
        dh_ports = []
        # Split the single and dual homed start interface into a list of two elements (port type and number)
        sh_first = srv_ports_adv['single_homed']['first_int'].split('/')
        dh_first = srv_ports_adv['dual_homed']['first_int'].split('/')

        ### 1. Use iteration number (index) to increment interface and add to the dictionary
        # Create single-homed interfaces
        for index, port in enumerate(srv_ports['single_homed']):
            int_num = str(int(sh_first[1]) + index)                     # Adds the index to the start port number
            port['interface'] = sh_first[0] + '/' + int_num             # Creates a new dict element for interface number
            sh_ports.append(port)                                   # Adds all single-homed port dictonaries to a list

        # Create dual-homed interfaces,POs and VPC
        for index, port in enumerate(srv_ports['dual_homed']):
            int_num = str(int(dh_first[1]) + index)
            port['interface'] = dh_first[0] + '/' + int_num             # Used 2 different ways to add to dictionary, could have used either
            port.update({'vpc': srv_ports_adv['dual_homed']['vpc'] + index, 'po': srv_ports_adv['dual_homed']['po'] + index})
            dh_ports.append(port)                                   # Adds all dual-homed port dictonaries to a list

        ### 2. FAIL-FAST: Only return new dictionaires if havent reached the interface limit
        num_sh = []
        num_dh = []
        # Works out the max number of interfaces that would be available
        sh_limit = int(srv_ports_adv['single_homed']['last_int'].split('/')[1]) - int(sh_first[1]) + 1
        dh_limit = int(srv_ports_adv['dual_homed']['last_int'].split('/')[1]) - int(dh_first[1]) + 1

        # Gets switch names from port dictionaries
        for sh_swi in sh_ports:
            num_sh.append(sh_swi ['switch'])
        for dh_swi in dh_ports:
            num_dh.append(dh_swi ['switch'])

        # Counts the number of ports on each switch and returns error if is higher than limit
        for sw_name, sw_count in dict(Counter(num_sh)).items():
            if sw_count > sh_limit:     # If the number of switch ports is more than the limit
                return 'Error: No single-homed ports left on ' + sw_name
        for sw_name, sw_count in dict(Counter(num_dh)).items():
            if sw_count > dh_limit:     # If the number of switch ports is more than the limit
                return 'Error: No dual-homed ports left on ' + sw_name

        # 3. Returns a dictionary containing both dictionaries
        return {'sh_ports': sh_ports, 'dh_ports': dh_ports}