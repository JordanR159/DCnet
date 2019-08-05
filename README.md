# DCnet
## Dependencies
The following commands install all dependencies required to run Mininet and the ONOS controller:
```
sudo apt install mininet
sudo apt install default-jdk
sudo apt install maven
wget http://repo1.maven.org/maven2/org/onosproject/onos-releases/2.1.0/onos-2.1.0.tar.gz
tar xvf onos-2.1.0.tar.gz
```

## Generating Mininet Topology
The following command generates the folded Clos topology in Mininet according to DCnet specifications and creates configuration files to use with the Ryu controller:
```
sudo python folded_clos.py [--leaf NUM] [--spine NUM] [--pod NUM] [--ratio NUM] [--fanout NUM]
```
All arguments are optional, with the default values and effects being:


--leaf   (Default 4) : Number of leaves in a pod

--spine  (Default 2) : Number of spines in a pod

--pod    (Default 4) : Number of pods in a data center

--ratio  (Default 2) : Number of super spines per spine

--fanout (Default 3) : Number of hosts per leaf

--dc     (Default 2) : Number of data centers in topology


Running this command starts the Mininet CLI and creates three configuration files, switch_config.csv, host_config.csv, and top_config.csv, for use by the ONOS controller.

## Running ONOS Controller
To start ONOS, go to the directory containing onos-2.1.0 that was extracted from the tarball and use the commands:
```
cd onos-2.1.0/bin
./onos-service
```

This starts the service that listens for a connection from Mininet. Then, access the web gui through http://localhost:8181/onos/ui, and use credentials:
```
Username: onos
Password: rocks
```

Once logged in to the gui, enable OpenFlow and reactive forwarding on the applications tab.

To start the DCnet application for ONOS, change directory to DCnet/controller, and build the app using:
```
mvn clean install -Dcheckstyle.skip
```

In the target directory this generates an oar file named onos-app-dcnet-2.1.0.oar that can be used by ONOS. Change directory back to onos-2.1.0/bin, and use the command:
```
./onos-app 127.0.0.1 reinstall! <Path to oar>
```

Which installs the DCnet application into the ONOS controller and activates it. If the application needs to be uninstalled, use the command:
```
./onos-app 127.0.0.1 uninstall org.onosproject.dcnet
```

Once installed, it might be necessary to restart the ONOS controller so that it can read the configuration files set up by Mininet and add the switches from Mininet. Use ctrl-C on the terminal running onos-service and enter the command again to restart ONOS. After this, hosts should be able to ping each other on Mininet, and after the first ping packet is transmitted between hosts, the necessary translation rules will be installed by DCnet to make further pinging much quicker.
