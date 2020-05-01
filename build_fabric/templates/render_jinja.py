# From http://networkbit.ch/python-jinja-template/
# Used to render a yaml file with a jinja2 template and print the output - good for testing Ansible
# Run the script using "python render_jinja.py input.yml template.j2"

from sys import argv            #Imports argv so that can enter values when run the script
from jinja2 import Environment, FileSystemLoader    #Imports from Jinja2
import yaml                                         #Import YAML from PyYAML

#Variables created when the script is run
script, yaml_input, jinja_template = argv

#Loads data from YAML file into Python dictionary
# config = yaml.load(open(yaml_input))
config = yaml.load(open(yaml_input), Loader=yaml.FullLoader)

#Loads the Jinja2 template
env = Environment(loader=FileSystemLoader('./'), trim_blocks=True, lstrip_blocks=True)
template = env.get_template(jinja_template)

#Render template using data and prints the output to screen
print(template.render(config))