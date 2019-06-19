# DCnet
## Dependencies
The following commands install all dependencies required to run Mininet and the Ryu controller:
```
sudo apt install mininet
sudo apt install python2.7
sudo apt install python-pip
sudo apt install python-ryu
sudo pip install ryu
```

## Generating Mininet Topology
The following command generates the folded Clos topology in Mininet according to DCnet specifications and creates configuration files to use with the Ryu controller:
```
sudo python folded_clos.py [--leaf NUM] [--spine NUM] [--pod NUM] [--ratio NUM] [--fanout NUM]
```
All arguments are optional, with the default values and effects being:


--leaf   (Default 4) : Number of leaves in a pod

--spine  (Default 2) : Number of spines in a pod

--pod    (Default 4) : Number of pods in topology

--ratio  (Default 2) : Number of super spines per spine

--fanout (Default 3) : Number of hosts per leaf


Running this command starts the Mininet CLI and creates two configuration files, switch_config.csv and host_config.csv, for use by the Ryu controller.

## Running Ryu Controller
WIP
