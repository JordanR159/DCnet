#!/bin/bash

output_dir="udp_ovs2_trs_output"
rewriting_ip="dc98::d4ae:52c8:c361"
tunneling_ip="dc91::9191:9100:4"

rm -rf ${output_dir}
mkdir -p ${output_dir}

plotdata_file=${output_dir}/plotdata
echo -e "#Msg_size\trewriting\ttunneling" > $plotdata_file

sizes=(2000 3500 5000 6500 8000)

for s in ${sizes[*]}
do
	echo "Msg size $s"

	# Kill qperf server if running
	for p in $(ps -aef | grep rajas | grep "qperf" | grep -v grep | gawk '{print $2}')
	do
		kill -9 $p
	done

	# Start the qperf server
	qperf > /dev/null 2>&1 &

	total=0
	avg1=0
	for i in `seq 1 5`
	do
		result_line=`ssh nebula111 "/home/rajas/bin/qperf ${rewriting_ip} -lca 0 -rca 0 -t 2 -m ${s} udp_lat" | tail -1`
		echo $result_line

		val=`echo $result_line | gawk '{print $3}'`
		unit=`echo $result_line | gawk '{print $4}'`

		if [ "$unit" = "ms" ]
		then
			val=`echo $val*1000 | bc -l`
		fi

		total=`echo $total + $val | bc -l`
	done

	avg1=`echo ${total}/5 | bc -l`

	# Kill qperf server if running
	for p in $(ps -aef | grep rajas | grep "qperf" | grep -v grep | gawk '{print $2}')
	do
		kill -9 $p
	done

	# Start the qperf server
	qperf > /dev/null 2>&1 &

	total=0
	avg2=0
	for i in `seq 1 5`
	do
		result_line=`ssh nebula111 "/home/rajas/bin/qperf ${tunneling_ip} -lca 0 -rca 0 -t 2 -m ${s} udp_lat" | tail -1`
		echo $result_line

		val=`echo $result_line | gawk '{print $3}'`
		unit=`echo $result_line | gawk '{print $4}'`

		if [ "$unit" = "ms" ]
		then
			val=`echo $val*1000 | bc -l`
		fi

		total=`echo $total + $val | bc -l`
	done

	avg2=`echo ${total}/5 | bc -l`

	echo -e "${s}\t${avg1}\t${avg2}" >> $plotdata_file

	# Kill qperf server if running
	for p in $(ps -aef | grep rajas | grep "qperf" | grep -v grep | gawk '{print $2}')
	do
		kill -9 $p
	done
done
