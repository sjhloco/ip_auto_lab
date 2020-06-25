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
        return desired_state
        # return actual_state
        # return result

############################################ Device data-model generators ############################################
# Creates the data model from the out retruned by the device

    def device_dm(self, desired_state, json_output, actual_state):
        # actual_state = json_output

        actual_state = defaultdict(dict)
        actual_state['peer-link_po'] = json_output['TABLE_peerlink']['ROW_peerlink']['peerlink-ifindex']
        actual_state['peer-link_vlans'] = json_output['TABLE_peerlink']['ROW_peerlink']['peer-up-vlan-bitset']
        actual_state['vpc_peer_keepalive_status'] = json_output['vpc-peer-keepalive-status']
        actual_state['vpc_peer_status'] = json_output['vpc-peer-status']
        for vpc in json_output['TABLE_vpc']['ROW_vpc']:
            actual_state[vpc['vpc-ifindex']]['consistency_status'] = vpc['vpc-consistency-status']
            actual_state[vpc['vpc-ifindex']]['port_status'] = vpc['vpc-port-state']
            actual_state[vpc['vpc-ifindex']]['vpc_num'] = vpc['vpc-id']
            actual_state[vpc['vpc-ifindex']]['active_vlans'] = vpc['up-vlan-bitset']

        return actual_state