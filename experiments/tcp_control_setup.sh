#!/bin/bash

#              n101
#             /    \
#            /      \
#        (rename71)  \
#          n103      n107
#         /    \       \
#        /      \       \
#       /   (enp1s0f2)   \
#      n105   n106      n109
#       |       |         |
#       |       |         |
#      n111   n112      n113
#

# In this experiment, we send tcp flows from n111 and n112 to n113
# All the qdiscs at all interfaces are set to 'pfifo limit 1000'
# except at n107 rename71 (name will differ), for which it is 'pfifo limit 500'
# and n106 enp1s0f2, for which it is netem and variable delay

# First run rewriting_ovs_setup
#./rewriting_ovs_setup.sh

# Now set qdiscs for all switches

# nebula101
echo n101
ssh nebula101 "sudo tc qdisc del dev eth5 root handle 0:; sudo tc qdisc add dev eth5 root handle 0: pfifo limit 1000"
ssh nebula101 "sudo tc qdisc del dev eth6 root handle 0:; sudo tc qdisc add dev eth6 root handle 0: pfifo limit 1000"

# nebula102
echo n102
ssh nebula102 "sudo tc qdisc del dev eth7 root handle 0:; sudo tc qdisc add dev eth7 root handle 0: pfifo limit 1000"
ssh nebula102 "sudo tc qdisc del dev eth8 root handle 0:; sudo tc qdisc add dev eth8 root handle 0: pfifo limit 1000"

# nebula103
echo n103
ssh nebula103 "sudo tc qdisc del dev eth6 root handle 0:; sudo tc qdisc add dev eth6 root handle 0: pfifo limit 1000"
ssh nebula103 "sudo tc qdisc del dev eth7 root handle 0:; sudo tc qdisc add dev eth7 root handle 0: pfifo limit 1000"
ssh nebula103 "sudo tc qdisc del dev rename20 root handle 0:; sudo tc qdisc add dev rename20 root handle 0: pfifo limit 1000"
ssh nebula103 "sudo tc qdisc del dev rename21 root handle 0:; sudo tc qdisc add dev rename21 root handle 0: pfifo limit 1000"

# nebula104
echo n104
for i in `seq 0 3`; do ssh nebula104 "sudo tc qdisc del dev enp1s0f$i root handle 0:; sudo tc qdisc add dev enp1s0f$i root handle 0: pfifo limit 1000"; done

# nebula105
echo n105
for i in `seq 1 4`; do ssh nebula105 "sudo tc qdisc del dev p1p$i root handle 0:; sudo tc qdisc add dev p1p$i root handle 0: pfifo limit 1000"; done

# nebula106
echo n106
ssh nebula106 "sudo tc qdisc del dev enp1s0f0 root handle 0:; sudo tc qdisc add dev enp1s0f0 root handle 0: pfifo limit 1000"
ssh nebula106 "sudo tc qdisc del dev enp1s0f1 root handle 0:; sudo tc qdisc add dev enp1s0f1 root handle 0: pfifo limit 1000"
#ssh nebula106 "sudo tc qdisc del dev enp1s0f2 root handle 0:; sudo tc qdisc add dev enp1s0f2 root handle 0: netem delay 0ms"
ssh nebula106 "sudo tc qdisc del dev enp1s0f2 root handle 0:; sudo tc qdisc add dev enp1s0f2 root handle 0: pfifo limit 1000"
ssh nebula106 "sudo tc qdisc del dev enp1s0f3 root handle 0:; sudo tc qdisc add dev enp1s0f3 root handle 0: pfifo limit 1000"

# nebula107
echo n107
for i in `seq 0 3`; do ssh nebula107 "sudo tc qdisc del dev enp1s0f$i root handle 0:; sudo tc qdisc add dev enp1s0f$i root handle 0: pfifo limit 1000"; done

# nebula108
echo n108
for i in `seq 1 4`; do ssh nebula108 "sudo tc qdisc del dev p1p$i root handle 0:; sudo tc qdisc add dev p1p$i root handle 0: pfifo limit 1000"; done

# nebula109
echo n109
for i in `seq 1 4`; do ssh nebula110 "sudo tc qdisc del dev p1p$i root handle 0:; sudo tc qdisc add dev p1p$i root handle 0: pfifo limit 1000"; done

# nebula111
echo n111
#ssh nebula111 "sudo tc qdisc del dev hyp root handle 0:; sudo tc qdisc add dev hyp root handle 0: pfifo limit 1000"
#ssh nebula111 "sudo tc qdisc del dev hyp-conn root handle 0:; sudo tc qdisc add dev hyp-conn root handle 0: pfifo limit 1000"
ssh nebula111 "sudo tc qdisc del dev eth1 root handle 0:; sudo tc qdisc add dev eth1 root handle 0: pfifo limit 1000"
ssh nebula111 "sudo tc qdisc del dev dcnet-srv000 root handle 0:; sudo tc qdisc add dev dcnet-srv000 root handle 0: pfifo limit 1000"

# nebula112
echo n112
#ssh nebula112 "sudo tc qdisc del dev hyp root handle 0:; sudo tc qdisc add dev hyp root handle 0: pfifo limit 1000"
#ssh nebula112 "sudo tc qdisc del dev hyp-conn root handle 0:; sudo tc qdisc add dev hyp-conn root handle 0: pfifo limit 1000"
ssh nebula112 "sudo tc qdisc del dev eno2 root handle 0:; sudo tc qdisc add dev eno2 root handle 0: pfifo limit 1000"
ssh nebula112 "sudo tc qdisc del dev dcnet-srv010 root handle 0:; sudo tc qdisc add dev dcnet-srv010 root handle 0: pfifo limit 1000"

# nebula113
echo n113
#sudo tc qdisc del dev hyp root handle 0:; sudo tc qdisc add dev hyp root handle 0: pfifo limit 1000
#sudo tc qdisc del dev hyp-conn root handle 0:; sudo tc qdisc add dev hyp-conn root handle 0: pfifo limit 1000
sudo tc qdisc del dev em2 root handle 0:; sudo tc qdisc add dev em2 root handle 0: pfifo limit 1000
sudo tc qdisc del dev dcnet-srv100 root handle 0:; sudo tc qdisc add dev dcnet-srv100 root handle 0: pfifo limit 1000
