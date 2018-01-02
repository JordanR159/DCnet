#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <net/ethernet.h>
#include <netinet/in.h>
#include <netinet/ip6.h>
#include <netinet/icmp6.h>
#include <netpacket/packet.h>
#include <pthread.h>

/* DCnet host/VM prefix	*/
uint8_t	DCnet_ip6_prefix[] = {0xdc, 0x98, 0, 0, 0, 0, 0, 0,
				0, 0, 0x98, 0x98, 0x98, 0, 0, 0};

/* DCnet server hostnames */
char	*DCnet_srvnames[] = { "nebula111.cs.purdue.edu",
			      "nebula112.cs.purdue.edu",
			      "nebula113.cs.purdue.edu" };

/* UID of this machine */
int	src_uid = 0;

/* Request and response times */
struct	timeval *req_times, *rep_times;

/* Format of request thread argument */
struct	req_thr_arg {
	int	uid;	/* UID of host		*/
	int	n_ping;	/* No. of pings		*/
	int	ic_dlen;/* ICMP data length	*/
	int	ipg;	/* Inter-pkt gap in us	*/
};

/* Prototypes for thread functions */
void	*req_thr_func (void *);
void	*rep_thr_func (void *);

#define	N_PING_DEF	10000
#define	IC_DLEN_DEF	100
#define	IPG_DEF		1000

char	*usage = "%s -i <ping interval (ms)> -n <no. of pings> -d <ICMP data size> -o <output file>\n";

#define	cond_fprintf(file, ...)	{ if(file) { fprintf(file, __VA_ARGS__); } }

/*---------------------------------------------------------------------------------------
 * main  -  Main function, creates request and reply threads
 *---------------------------------------------------------------------------------------
 */
int	main (
		int	argc,	/* No. of cmd-line arguments	*/
		char	*argv[]	/* Cmd-line arguments		*/
	     )
{
	pthread_t	req_thr, rep_thr;	/* Thread objects	*/
	struct		req_thr_arg req_arg;	/* Request thread arg	*/
	struct		timeval td;		/* Time difference	*/
	char		hostname[256];		/* Hostname of src	*/
	FILE		*opfile;		/* Output file		*/
	int		lost;			/* No. of lost replies	*/
	int		opt;			/* getopt return value	*/
	int		err;			/* Return value		*/
	int		i;			/* Loop index		*/

	/* Get the hostname of this machine */
	err = gethostname(hostname, 255);
	if(err == -1) {
		perror("gethostname()");
		exit(1);
	}

	for(i = 0; i < 3; i++) {
		if(!strncmp(hostname, DCnet_srvnames[i], 9)) {
			break;
		}
	}
	if(i >= 3) {
		printf("Please run this on one of the DCnet servers\n");
		exit(1);
	}

	src_uid = i * 2;

	/* Fill in default values for req thread argument */
	req_arg.uid = 0;
	req_arg.n_ping = N_PING_DEF + 5;
	req_arg.ic_dlen = IC_DLEN_DEF;
	req_arg.ipg = IPG_DEF;

	/* Process command line arguments */
	while((opt = getopt(argc, argv, "i:n:d:o:h")) != -1) {

		switch(opt) {

			case 'i': /* Inter-pkt gap in ms */
				req_arg.ipg = atof(optarg) * 1000;
				break;

			case 'n': /* No. of pings */
				req_arg.n_ping = atoi(optarg) + 5;
				break;

			case 'd': /* Size of ICMP data */
				req_arg.ic_dlen = atoi(optarg);
				break;

			case 'o':
				opfile = fopen(optarg, "w");
				if(!opfile) {
					printf("Cannot open output file, will not compute response times\n");
				}
				break;

			case 'h': /* Usage message */
				printf(usage, argv[0]);
				exit(0);
				break;

			default: /* Unknown option */
				printf("Unrecognized option %s\n", optarg);
				printf(usage, argv[0]);
				exit(1);
		}
	}

	/* Non-getopt option must be present */
	if(optind > (argc-1)) {
		printf("Required UID\n");
		printf(usage, argv[0]);
		exit(1);
	}

	/* Non-getopt option is the UID */
	req_arg.uid = atoi(argv[optind]);

	/* Allocate memory for request times */
	req_times = (struct timeval *)calloc(req_arg.n_ping, sizeof(struct timeval));
	if(!req_times) {
		printf("calloc failed\n");
		exit(1);
	}

	/* Allocate memory for request times */
	rep_times = (struct timeval *)calloc(req_arg.n_ping, sizeof(struct timeval));
	if(!rep_times) {
		printf("calloc failed\n");
		exit(1);
	}

	/* Create the response thread */
	err = pthread_create(&rep_thr, NULL, rep_thr_func, NULL);
	if(err != 0) {
		printf("Cannot create response thread\n");
		exit(1);
	}

	/* Create the request thread */
	err = pthread_create(&req_thr, NULL, req_thr_func, &req_arg);
	if(err != 0) {
		printf("Cannot create request thread\n");
		exit(1);
	}

	/* Sleep for enough time */
	sleep(((req_arg.n_ping * req_arg.ipg)/1000000) + 5);

	/* Calculate the number of lost responses */
	lost = 0;
	for(i = 5; i < req_arg.n_ping; i++) {
		cond_fprintf(opfile, "%d ", i);
		if(req_times[i].tv_sec != 0) {
			cond_fprintf(opfile, "%ld,%ld ", req_times[i].tv_sec, req_times[i].tv_usec);
			if(rep_times[i].tv_sec == 0) {
				cond_fprintf(opfile, "-1,-1 -1\n");
				lost++;
			}
			else {
				cond_fprintf(opfile, "%ld,%ld ", rep_times[i].tv_sec, rep_times[i].tv_usec);
				timersub(&rep_times[i], &req_times[i], &td);
				cond_fprintf(opfile, "%f\n", ((float)(td.tv_sec*1000000 + td.tv_usec))/1000);
			}
		}
		else {
			cond_fprintf(opfile, "-1,-1 -1,-1, -1\n");
		}
	}

	printf("%d\n", lost);

	free(req_times);
	free(rep_times);

	return 0;
}

/*---------------------------------------------------------------------------------------
 * icmp6_cksum  -  Compute and return ICMPv6 checksum
 *---------------------------------------------------------------------------------------
 */
uint16_t	icmp6_cksum (
		struct	ip6_hdr *ip6	/* IPv6 packet	*/
		)
{
	uint32_t	total;		/* Total sum	*/
	uint16_t	cksum;		/* Final cksum	*/
	uint16_t	*ptr16;		/* Pointer	*/
	uint32_t	plen;		/* Payload len	*/
	int		i;		/* Loop index	*/
	uint8_t		last[2];	/* Last 2 bytes	*/

	/* Pseudo header for checksum */
	struct	{
		uint8_t		src[16];	/* IP source		*/
		uint8_t 	dst[16];	/* IP dest		*/
		uint32_t	plen;		/* IP payload len	*/
		uint8_t		pad[3];		/* Padding (zero)	*/
		uint8_t		nxt;		/* IP next header	*/
	} pseudo;

	/* Set the fields in the pseudo header */
	memset(&pseudo, 0, sizeof(pseudo));
	memcpy(pseudo.src, ip6->ip6_src.s6_addr, 16);
	memcpy(pseudo.dst, ip6->ip6_dst.s6_addr, 16);
	plen = ntohs(ip6->ip6_plen);
	pseudo.plen = htonl(plen);
	pseudo.nxt = 58;

	total = 0;

	/* Start adding shorts in the pseudo header */
	ptr16 = (uint16_t *)&pseudo;
	for(i = 0; i < 20; i++) {
		total += htons(*ptr16);
		ptr16++;
	}

	/* Add shorts in the payload */
	ptr16 = (uint16_t *)(ip6 + 1);
	for(i = 0; i < (plen/2); i++) {
		total += htons(*ptr16);
		ptr16++;
	}

	/* If length is odd, add one zero byte at the end */
	if(plen & 0x00000001) {
		last[0] = *((uint8_t *)ptr16);
		last[1] = 0;
		total += htons(*((uint16_t *)last));
	}

	/* Iteratively add the 16-bit carry until there is no carry */
	while((total&0xFFFF0000) != 0) {
		total = (total&0x0000FFFF) + ((total>>16)&0x0000FFFF);
	}

	/* Take the complement of the final sum */
	cksum = ((~(total&0x0000FFFF))&0x0000FFFF);

	return cksum;
}

/*---------------------------------------------------------------------------------------
 * req_thr_func  -  Thread that sends Ping requests at a fixed rate
 *---------------------------------------------------------------------------------------
 */
void	*req_thr_func (
		void	*thr_arg	/* Thread argument	*/
		)
{
	struct	req_thr_arg *req_arg;	/* Thread arguments	*/
	struct	ip6_hdr *ip6;		/* IPv6 header		*/
	struct	icmp6_hdr *ic6;		/* ICMPv6 header	*/
	struct	sockaddr_in6 dst_addr;	/* Destination address	*/
	struct	timeval t1, t2, td;	/* Times		*/
	uint16_t cksum;			/* ICMPv6 checksum	*/
	int	slp_time;		/* Sleep time in usecs	*/
	int	req_sock;		/* Socket		*/
	int	ic_seq;			/* ICMP sequence number	*/
	int	err;			/* Error return value	*/
	int	i;			/* Loop index		*/

	req_arg = (struct req_thr_arg *)thr_arg;

	/* Create a raw socket to send pings */
	req_sock = socket(AF_INET6, SOCK_RAW, IPPROTO_RAW);
	if(req_sock == -1) {
		perror("socket()");
		exit(1);
	}

	/* Allocate memory for the packet */
	ip6 = (struct ip6_hdr *)malloc(40 + 4 + req_arg->ic_dlen);
	if(!ip6) {
		printf("req_thr_func: cannot allocate memory\n");
		exit(1);
	}

	ic_seq = 0;

	gettimeofday(&t1, NULL);

	/* Send ping packets in this loop */
	for(i = 0; i < req_arg->n_ping; i++) {

		/* Fill in the IPv6 header */
		memset(ip6, 0, sizeof(*ip6));
		ip6->ip6_vfc = 0x60;
		ip6->ip6_plen = htons(4 + req_arg->ic_dlen);
		ip6->ip6_nxt = 58; /* IPv6 next = ICMPv6 */
		ip6->ip6_hlim = 255;
		memcpy(ip6->ip6_src.s6_addr, DCnet_ip6_prefix, 16);
		ip6->ip6_src.s6_addr[15] = src_uid;
		memcpy(ip6->ip6_dst.s6_addr, DCnet_ip6_prefix, 16);
		ip6->ip6_dst.s6_addr[15] = req_arg->uid;

		/* Fill in the ICMPv6 header */
		ic6 = (struct icmp6_hdr *)(ip6 + 1);
		ic6->icmp6_type = 128; /* ICMPv6 echo rquest */
		ic6->icmp6_code = 0;
		ic6->icmp6_cksum = 0;
		ic6->icmp6_data16[0] = htons(0xdc98);
		ic6->icmp6_data16[1] = htons(0xdc98);
		ic6->icmp6_data32[1] = htonl(ic_seq);

		/* Compute the ICMPv6 checksum */
		cksum = icmp6_cksum(ip6);
		ic6->icmp6_cksum = htons(cksum);

		/* Initialize the destination address */
		memset(&dst_addr, 0, sizeof(dst_addr));
		dst_addr.sin6_family = AF_INET6;
		dst_addr.sin6_addr = ip6->ip6_dst;

		gettimeofday(&t2, NULL);
		timersub(&t2, &t1, &td);

		/* Calculate sleep time based on inter-pkt gap */
		slp_time = req_arg->ipg - ((td.tv_sec * 1000000) + td.tv_usec) - 70;
		if(slp_time > 0) {
			usleep(slp_time);
		}

		gettimeofday(&t1, NULL);

		/* Send the packet */
		err = sendto(req_sock, ip6, 40+4+req_arg->ic_dlen, 0, (struct sockaddr *)&dst_addr, sizeof(dst_addr));
		if(err < 0) {
			perror("sendto()");
			exit(1);
		}

		req_times[ic_seq++] = t1;
	}

	/* Free the memory allocated for the packet */
	free(ip6);

	return NULL;
}

/*---------------------------------------------------------------------------------------
 * rep_thr_func  -  Thread that collects ping responses
 *---------------------------------------------------------------------------------------
 */
void	*rep_thr_func (
		void	*thr_arg	/* Thread argument	*/
		)
{
	struct	ip6_hdr *ip6;		/* IPv6 header		*/
	struct	icmp6_hdr *ic6;		/* ICMPv6 header	*/
	struct	sockaddr_ll src_addr;	/* Source address	*/
	struct	timeval t1;		/* Time			*/
	socklen_t src_alen;		/* Src address length	*/
	void	*pkt;			/* Packet pointer	*/
	int	rep_sock;		/* Socket		*/
	int	ic_seq;			/* Sequence number	*/
	int	err;			/* Return value		*/

	/* Create socket to receive packets */
	rep_sock = socket(AF_PACKET, SOCK_RAW, htons(ETHERTYPE_IPV6));
	if(rep_sock == -1) {
		perror("socket()");
		exit(1);
	}

	/* Allocate memory for packet */
	pkt = malloc(1500);
	if(!pkt) {
		printf("rep_thr_func: cannot allocate memory\n");
		exit(1);
	}

	/* Receive packets in this loop */
	while(1) {

		/* Receive a packet on the socket */
		src_alen = sizeof(src_addr);
		err = recvfrom(rep_sock, pkt, 1500, 0, (struct sockaddr *)&src_addr, &src_alen);
		if(err < 0) {
			perror("recvfrom()");
			exit(1);
		}

		gettimeofday(&t1, NULL);

		/* Skip the ethernet header */
		ip6 = (struct ip6_hdr *)((uint8_t *)pkt + 14);

		/* Check if ICMPv6 */
		if(ip6->ip6_nxt != 58) {
			continue;
		}

		ic6 = (struct icmp6_hdr *)(ip6 + 1);

		/* Check if ICMPv6 echo reply */
		if(ic6->icmp6_type != 129) {
			continue;
		}

		/* Check if this is our DCnet packet */
		if((ntohs(ic6->icmp6_data16[0]) != 0xdc98) || (ntohs(ic6->icmp6_data16[1]) != 0xdc98)) {
			continue;
		}

		/* Extract the sequence number */
		ic_seq = ntohl(ic6->icmp6_data32[1]);

		rep_times[ic_seq] = t1;
	}

	return NULL;
}
