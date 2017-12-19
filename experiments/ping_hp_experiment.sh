#!/bin/bash

output_dir=ping_hp_output

# Ping data sizes
first=200
last=8800
step=200
sizes=(`seq $first $step $last`)
sizes+=(8952)

n102_1="dc98::9898:9800:d2"
n102_r_1="dc99::9999:9900:d2"

mkdir -p $output_dir
rm -rf ${output_dir}/*
echo -e "#ping_size\tno-rewriting\trewriting" > ${output_dir}/plotdata

for s in ${sizes[*]}
do
	# Perform single ping to load caches
	ssh nebula101 "ping6 -c 1 $n102_1" > /dev/null

	# Perform experiment without rewriting
	output_file=${output_dir}/ping_s${s}_output
	ssh nebula101 "sudo ping6 $n102_1 -i 0.01 -c 100 -s $s" > $output_file
	avg1=`tail -1 $output_file | gawk '{print $4}' | gawk 'BEGIN {FS = "/"}; {print $2}'`

	# Perform single ping to load caches
	ssh nebula101 "ping6 -c1 $n102_r_1" > /dev/null

	# Perform experiment with rewriting
	output_file=${output_dir}/ping_s${s}_r_output
	ssh nebula101 "sudo ping6 $n102_r_1 -i 0.01 -c 100 -s $s" > $output_file
	avg2=`tail -1 $output_file | gawk '{print $4}' | gawk 'BEGIN {FS = "/"}; {print $2}'`

	echo -e "${s}\t${avg1}\t${avg2}" >> $output_dir/plotdata
done
