""" Generates compliance reports using napalm_validate with an input file of the actual state
rather than naplam_validate state to allow the vlidation of features that dont have naplam_getters.
As cant use varaibles for Ansible filter plugin names has device specific methods that are called
by the main method (engine);

Methods:
-compliance_report: Replaces the compliance_report method with this custom one that still runs
validate.compare but with desired state and actual state yaml files
-custom_validate: CRuns the OS specific methods and passes the returned DM through napalm_validate
to create a omplaince report
-xxx_dm: Formats the data recieved from the device into the same format as the desired state yaml file.
Will have different methods for different OS types.
-fix_home_path: Converts ~/ to full path for naplm_vaidate and compliance_report as dont recognise

A pass or fail is returned to the Ansible Assert module, as well as the compliance report joined to
the napalm_validate complaince report
"""

from napalm.base import validate
from napalm.base.exceptions import ValidationException
import json
from collections import defaultdict
import os
import re

class FilterModule(object):
    def filters(self):
        return {
            'fix_home_path': self.fix_home_path,
            'custom_validate': self.custom_validate,
        }

    # FIX: napalm_validate doesnt recognise ~/ for home drive, also used in report method
    def fix_home_path(self, input_path):
        if re.match('^~/', input_path):
            return os.path.expanduser(input_path)
        else:
            return input_path

############################################ Method to run napalm_validate ############################################
# REPORT: Uses naplam_validate on custom data fed into it (still supports '_mode: strict') to validate and create reports

    def compliance_report(self, desired_state, actual_state, directory, hostname):
        report = {}
        for cmd, desired_results in desired_state.items():
            key = cmd
            try:                # Feeds files into napalm_validate
                report[key] = validate.compare(desired_results, actual_state)
            except NotImplementedError:
                report[key] = {"skipped": True, "reason": "NotImplemented"}

        complies = all([e.get("complies", True) for e in report.values()])
        report["skipped"] = [k for k, v in report.items() if v.get("skipped", False)]
        report["complies"] = complies

        #If a compliance report exists adds to it, if not creates a new one.
        filename = os.path.join(self.fix_home_path(directory), 'reports/', hostname + '_fbc_compliance_report.json')
        if os.path.exists(filename):
            with open(filename, 'r') as file_content:
                existing_report = json.load(file_content)
        else:
            existing_report = {}
        existing_report.update(report)
        with open(filename, 'w') as file_content:
            json.dump(existing_report, file_content)

        return report

############################################ Engine for custom_validate ############################################
# ENGINE: Runs OS specific method to get data model, puts it through napalm_validate and then repsonds to Ansible

    def custom_validate(self, desired_state, output, directory, hostname, os):
        json_output = json.loads(output)     # Output comes in as serilaised json (long sting), needs making into json
        actual_state = {}

        # Runs the OS specific method
        if os == 'nxos':
            actual_state = self.nxos_dm(desired_state, json_output, actual_state)

        # Feeds the validation file and new data model through the reporting function
        result = self.compliance_report(desired_state, actual_state, directory, hostname)
        # # Only the compliance report outcome is sent to Ansible Assert module, not the full report.
        if result["complies"] == True:
            return "'custom_validate passed'"
        else:
            return "'custom_validate failed'"

############################################ OS data-model generators ############################################
# NXOS: Formats the actual_state into data models to return to the engine that then passes it through the reporting method

    def nxos_dm(self, desired_state, json_output, actual_state):
        # OSPF: Creates a dictionary from the device output to match the format of the validation file
        if list(desired_state.keys())[0] == "show ip ospf neighbors detail":
            for nhbr in json_output['TABLE_ctx']['ROW_ctx']['TABLE_nbr']['ROW_nbr']:
                actual_state[nhbr['rid']] = {'state': nhbr['state']}

        # PO: Creates a dictionary from the device output to match the format of the validation file
        elif list(desired_state.keys())[0] == "show port-channel summary":
            actual_state = defaultdict(dict)
            # Required due to shit NXOS JSON making dict rather than lisy if only 1 Po
            if isinstance(json_output['TABLE_channel']['ROW_channel'], dict):
                json_output['TABLE_channel']['ROW_channel'] = [json_output['TABLE_channel']['ROW_channel']]
            for po in json_output['TABLE_channel']['ROW_channel']:
                actual_state[po['port-channel'].capitalize()]['oper_status'] = po['status']
                po_mbrs = {}
                # Required due to shit NXOS JSON not adding blank fields if no members
                if len(po) == 7:
                    for mbr in po['TABLE_member']['ROW_member']:
                        # Creates dict of members to add to as value in the PO dictionary
                        po_mbrs[mbr['port']] = {'mbr_status': mbr['port-status']}
                actual_state[po['port-channel'].capitalize()]['members'] = po_mbrs

        # VDC: Creates a dictionary from the device output to match the format of the validation file
        elif list(desired_state.keys())[0] == "show vpc":
            actual_state['vpc_peer_keepalive_status'] = json_output['vpc-peer-keepalive-status']
            actual_state['vpc_peer_status'] = json_output['vpc-peer-status']

        elif list(desired_state.keys())[0] == "show ip int brief include-secondary vrf all":
            vrf_list = []
            for intf in json_output['TABLE_intf']['ROW_intf']:
                vrf_list.append(intf['vrf-name-out'])
            for vrf in set(vrf_list):
                intf_list = defaultdict(dict)
                for intf in json_output['TABLE_intf']['ROW_intf']:
                    if vrf == intf['vrf-name-out']:
                        intf_list[intf['intf-name']]['proto-state'] = intf['proto-state']
                        intf_list[intf['intf-name']]['link-state'] = intf['link-state']
                        intf_list[intf['intf-name']]['admin-state'] = intf['admin-state']
                        intf.setdefault('prefix', None)
                        intf_list[intf['intf-name']]['prefix'] = intf['prefix']
                actual_state[vrf] = intf_list

        elif list(desired_state.keys())[0] == "show nve peers":
            for peer in json_output['TABLE_nve_peers']['ROW_nve_peers']:
                actual_state[peer['peer-ip']] = {'peer-state': peer['peer-state']}

        elif list(desired_state.keys())[0] == "show nve vni":
            for vni in json_output['TABLE_nve_vni']['ROW_nve_vni']:
                actual_state[vni['vni']] = {'type': vni['type'], 'state': vni['vni-state']}

        return actual_state