#!/bin/bash

cat resptimes_opt_t6000_4 | head -n 9000 | tail -n 5000 | gawk '{print NR " " $4}' > plotdata2_opt
sed -i 's/.*-1//' plotdata2_opt
cat resptimes_noopt_t6000_4 | head -n 9000 | tail -n 5000 | gawk '{print NR " " $4}' > plotdata2_noopt
sed -i 's/.*-1//' plotdata2_noopt
