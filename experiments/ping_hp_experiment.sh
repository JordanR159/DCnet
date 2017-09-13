#!/bin/bash

output_dir=ping_hp_output

# Ping data sizes
first=200
last=8800
step=200
sizes=(`seq $first $step $last`)
sizes+=(8952)

mkdir -p $output_dir
rm -rf ${output_dir}/*
echo -e "#ping_size\tno-rewriting\trewriting" > ${output_dir}/plotdata

for s in ${sizes[*]}
do
	# Perform single ping to load caches
	ping6 n107_1 -c 1

	# Perform experiment without rewriting
	output_file=${output_dir}/ping_s${s}_output
	sudo ping6 n107_1 -i 0.01 -c 100 -s $s > $output_file
	avg1=`tail -1 $output_file | gawk '{print $4}' | gawk 'BEGIN {FS = "/"}; {print $2}'`

	# Perform single ping to load caches
	ping6 n107_r_1 -c 1

	# Perform experiment with rewriting
	output_file=${output_dir}/ping_s${s}_r_output
	sudo ping6 n107_r_1 -i 0.01 -c 100 -s $s > $output_file
	avg2=`tail -1 $output_file | gawk '{print $4}' | gawk 'BEGIN {FS = "/"}; {print $2}'`

	echo -e "${s}\t${avg1}\t${avg2}" >> $output_dir/plotdata
done
