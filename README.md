# stesworld.com - Making dreams for the dreamers

Initial lab from the ipspace automation course. 

At present the company has one DC built with a Leaf and Spine EVPN/VXLAN topology. It has one Internet breakout via GTT and a dedicated Express Route circuit to Azure. 

The plan in the future is to either expand to a second DC or provide Internet redundancy in the current DC.
<br/>Option1: *Build second DC that will operate as active/active with the current DC with Internet redundancy provided via the opposite DC*
<br/>Option2: *Expand current DC by adding more leaf switches as well as adding another border leaf and internet breakout for redundancy.*

They will also be adding a Direct connect link to AWS t provide cloud provider redudancy, although how this is incoporated will depned on the above option taken.

The main goal of the companies IT department is to grasp orchestration/automation and "infrastructure/network as code". Currently they are predominantly a Cisco shop but are keen to try other vendors which may be better designed and more flexible to this ethos.

They are currently in the process of incorporating orchestration/automation workflows into their current day to day operations with the vision in the future that 99% of BAU or maintenance work will be done in this manner.

Although the current network was built in the traditional hands on method, any expansion MUST be done via orchestration/automation tools.

### Configuration backups

*backup_configs* will backup all device configs upload them to this repo in the *configurations* directory.

### Reporting

*network_state_report* creates custom reports of network elements within the fabric.

### Data Models

*data_model* creates config snippets using declarative data models.
