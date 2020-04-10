
num_leafs = 2
num_borders =2
sp_to_lf = 1                        # First interface used for SPINE to LEAF links (1 to 10)
sp_to_bdr = 11
int_format = "Ethernet1/"

leaf = 'DC1-N9K-LEAF'
border = 'DC1-N9K-BORDER'
hostname = 'DC1-N9K-LEAF01'

spine = ['DC1-N9K-SPINE01', 'DC1-N9K-SPINE02', 'DC1-N9K-SPINE03', 'DC1-N9K-SPINE04']
# spine = ['DC1-N9K-SPINE01', 'DC1-N9K-SPINE02']
from collections import defaultdict
from pprint import pprint

spine_int = defaultdict(dict)

for sp_name in spine:
    for n in range(num_leafs):
        spine_int[sp_name][int_format + (str(sp_to_lf + n))] = 'UPLINK > ' + leaf + "{:02d} ".format(n +1) + int_format[:3] + int_format[-2:] + "{:01d}".format(int(sp_name[-2:]))
    for n in range(num_borders):
        spine_int[sp_name][int_format + (str(sp_to_bdr + n))] = 'UPLINK > ' + border + "{:02d} ".format(n +1) + int_format[:3] + int_format[-2:] + "{:01d}".format(int(sp_name[-2:]))
spine_int




tree = lambda: defaultdict(tree)
info = tree()

for sp_name in spine:
    for n in range(num_leafs):
        info['fbc1'][sp_name][int_format + (str(sp_to_lf + n))] = 'UPLINK > ' + leaf + "{:02d} ".format(n +1) + int_format[:3] + int_format[-2:] + "{:01d}".format(int(sp_name[-2:]))


mlag_leaf_ip: 1                          # Start IP for LEAF Peer Links, so LEAF1 is .1, LEAF2 .2, LEAF3 .3, etc
mlag_border_ip: 11                       # Start IP for BORDER Peer Links, so BORDER1 is .11, BORDER2 .12, etc

intf_fmt = "Ethernet1/"            # Switch interface, must be same on all switches. First 3 letters used in interface descriptions
ec_fmt = 'Port-channel'
mlag_peer = '127-128'
peer_po = 1

leaf = ['DC1-N9K-LEAF01', 'DC1-N9K-LEAF02', 'DC1-N9K-LEAF03', 'DC1-N9K-LEAF04']
border = ['DC1-N9K-BORDER01', 'DC1-N9K-BORDER02', 'DC1-N9K-BORDER03', 'DC1-N9K-LBORDER04']
mlag_int = defaultdict(dict)                   # Start IP for BORDER Peer Links, so BORDER1 is .11, BORDER2 .12, etc

for dev in leaf + border:
    for port in [intf_fmt + mlag_peer.split('-')[0], intf_fmt + mlag_peer.split('-')[1], ec_fmt + str(peer_po)]:
            if int(lf[-2:]) % 2 != 0:        #odd
                mlag_int[lf][port] = 'MLAG peer-link > ' + lf[:-2] + "{:02d} ".format(int(lf[-2:]) +1) + port
            else:                           #even
                mlag_int[lf][port] = 'MLAG peer-link > ' + lf[:-2] + "{:02d} ".format(int(lf[-2:]) -1) + port
mlag_int







mlag_peer_ip: 10.10.10.10/31

leaf = ['DC1-N9K-LEAF01', 'DC1-N9K-LEAF02', 'DC1-N9K-LEAF03', 'DC1-N9K-LEAF04']
border = ['DC1-N9K-BORDER01', 'DC1-N9K-BORDER02', 'DC1-N9K-BORDER03', 'DC1-N9K-BORDER04']
mlag_peer = defaultdict(dict)
lf_name = 'DC1-N9K-LEAF'

mlag_net = '10.255.255.0/28'    # VPC peer link addresses. Needs to be at least /28 to cover max leafs (10) and borders (4)
mlag_leaf_ip = 1                          # Start IP for LEAF Peer Links, so LEAF1 is .1, LEAF2 .2, LEAF3 .3, etc
mlag_border_ip = 11                       # Start IP for BORDER Peer Links, so BORDER1 is .11, BORDER2 .12, etc

for dev in leaf + border:
    if lf_name in dev:
        mlag_peer[dev]['mlag_peer_ip'] = str(ip_network(mlag_net, strict=False)[int(dev[-2:]) + mlag_leaf_ip -1]) + '/31'
    else:
        mlag_peer[dev]['mlag_peer_ip'] = str(ip_network(mlag_net, strict=False)[int(dev[-2:]) + mlag_border_ip -1]) + '/31'
 
 