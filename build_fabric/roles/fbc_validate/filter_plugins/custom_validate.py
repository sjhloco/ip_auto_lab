""" Generates compliance reports using napalm_validate with an input file of the actual state
rather than naplam_validate state to allow the vlidation of features that dont have naplam_getters

Methods:
-compliance_report: Replaces the compliance_report method with this custom one that still runs
validate.compare but with expected state and actual state yaml files
-custom_validate: Formats the data recieved from the device (parsed by PYats genie) into the same
format as the expected state yaml file for napalm_validate to then run complaince check on
-fix_home_path: Converts ~/ to full path for naplm_vaidate and compliance_report as dont recognise

A pass or fail is returned to the Ansibel Assert module, as well as the compliance report joined to
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
            'custom_validate': self.custom_validate,
            'fix_home_path': self.fix_home_path,
        }

    # REPORT: Uses naplam_validate on custom data fed into it (still supports '_mode: strict') to validate and create reports
    def compliance_report(self, expected_state, actual_state, directory, hostname):
        report = {}
        for cmd, expected_results in expected_state.items():
            key = cmd
            try:                # Feeds files into napalm_validate
                report[key] = validate.compare(expected_results, actual_state)
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

    # PROCESS: Formats the actual state into data models to pass through the reporting function
    def custom_validate(self, expected_state, output, directory, hostname):
        actual_state = {}

        # OSPF: Creates a dictionary from the device output to match the format of the validation file
        if list(expected_state.keys())[0] == "show ip ospf neighbors detail":
            for intf in output['vrf']['default']['address_family']['ipv4']['instance']['underlay']['areas']['0.0.0.0']['interfaces'].values():
                for nhbr in intf['neighbors'].values():
                    actual_state[nhbr['neighbor_router_id']] = {'state': nhbr['state']}
        # PO: Creates a dictionary from the device output to match the format of the validation file
        elif list(expected_state.keys())[0] == "show port-channel summary":
            actual_state = defaultdict(dict)
            for po_dict in output.values():
                for po, po_details in po_dict.items():
                    actual_state[po]['oper_status'] = po_details['oper_status']
                    actual_state[po]['members'] = po_details['members']
        # VDC: Creates a dictionary from the device output to match the format of the validation file
        elif list(expected_state.keys())[0] == "show vpc":
            actual_state['vpc_peer_keepalive_status'] = output['vpc_peer_keepalive_status']
            actual_state['vpc_peer_status'] = output['vpc_peer_status']

        # Feeds the validation file and new data model through the reporting function
        result = self.compliance_report(expected_state, actual_state, directory, hostname)
        # Only the compliance report outcome is sent to Ansible Assert module, not the full report.
        if result["complies"] == True:
            return "'custom_validate passed'"
        else:
            return "'custom_validate failed'"
        # return result["complies"]
    # FIX: napalm_validate doesnt recognise ~/ for home drive, also used in report method
    def fix_home_path(self, input_path):
        if re.match('^~/', input_path):
            return os.path.expanduser(input_path)
        else:
            return input_path




