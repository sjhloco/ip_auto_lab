import yaml
from pprint import pprint

with open('services.yml', 'r') as x:
    services = yaml.load(x)

l3vni = services['base_vni']['l3vni']
tn_vlan = services['base_vni']['tn_vlan']
l2vni = services['base_vni']['l2vni']

for tn in services['tenants']:
    if tn['l3_tenant'] is True:
        tn['l3vni'] = l3vni
        tn['tn_vlan'] = tn_vlan
    l3vni = l3vni + 1
    tn_vlan = tn_vlan + 1
    for vl in tn['vlans']:
        vl['l2vni'] = l2vni + vl['num']
    l2vni = l2vni + 10000

for x in services['tenants']:
    pprint(x)




