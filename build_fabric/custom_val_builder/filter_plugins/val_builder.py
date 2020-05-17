""" Used to test creating compliance reports to be used with custom_validate in playbook
Uses napalm_validate with an input file of the actual state rather than naplam_validate state

Can take an input of a static dictionary file of the expected output or the actual device output.
If using the input file it is stored in files/file_input.json

ansible-playbook playbook.yml -i hosts --tag tmpl
ansible-playbook playbook.yml -i hosts --tag dev_val
ansible-playbook playbook.yml -i hosts --tag file_val

Unhash desired_state, actual_state or result dependant on what you want returned to screen.
The desired state is saved to files/desired_sate.yml and report to files/compliance_report.json

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
        }

############################################ Method to run napalm_validate ############################################
# REPORT: Uses naplam_validate on custom data fed into it (still supports '_mode: strict') to validate and create reports

    def compliance_report(self, desired_state, actual_state):
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

        # Create a new compliance report
        with open('files/compliance_report.json', 'w') as file_content:
            json.dump(report, file_content)
        return report

############################################ Engine for custom_validate ############################################
# ENGINE: Runs method to get data model, puts it through napalm_validate and then repsonds to Ansible

    def custom_validate(self, desired_state, output, input_method):
        json_output = json.loads(output)     # Output comes in as serilaised json (long sting), needs making into json

        # Runs against a static input file of the device output (in json)
        if input_method == 'file':
            actual_state = json_output
        # Feeds the device input into the device_dm method create the Data Model
        elif input_method == 'device':
            actual_state = self.device_dm(desired_state, json_output, actual_state = {})

        # Feeds the validation file (desired state) and new data model through the reporting function
        result = self.compliance_report(desired_state, actual_state)

        # Unhash what you want to display on screen
        # return desired_state
        # return actual_state
        return result

############################################ Device data-model generators ############################################
# Creates the data model from the out retruned by the device

    def device_dm(self, desired_state, json_output, actual_state):
        # actual_state = json_output
        if list(desired_state.keys())[0] == "show ip int brief include-secondary vrf all":
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

        return actual_state

