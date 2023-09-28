# Server decommissioning with Ansible

The intent of this repo is to provide a new Ansible Controller user with the necessary tools to automate the decommissioning of servers on vmware and infoblox.

Playbook breakdown:
- ```stage-decom-vm.yml``` - stages a vm you intend to decomission with a set wait period. A separate scheduled job will run daily to verify if the wait period has been reached for the staged server.
- ```update-decom-report.yml``` - generates of a report of servers that are staged for decommissioning and the date they will be removed
- ```check-and-decommission.yml``` - will verify if the wait period has been reached. If so, Ansible will initiate decomissioning steps in a Workflow




