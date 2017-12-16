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

#define	IC_DLEN_DEFAULT		100
#define	NPING_DEFAULT		10000
#define	PING_IPG_DEFAULT	1000

uint8_t	ip6_prefix[] = {0xdc, 0x98, 0, 0, 0, 0, 0, 0,
			0, 0, 0x98, 0x98, 0x98, 0, 0, 0};

struct	req_thr_arg {
	int	uid;
	int	ic_dlen;
	int	nping;
	int	ping_ipg;
};

struct	timeval *req_times, *rep_times;

void	*req_thr_func (void *);
void	*rep_thr_func (void *);

int	main (
		int	argc,
		char	*argv[]
	     )
{
	pthread_t	req_thr, rep_thr;
	struct	req_thr_arg req_arg;
	int	opt;
	int	lost;
	int	i;

	req_arg.ic_dlen = IC_DLEN_DEFAULT;
	req_arg.ping_ipg = PING_IPG_DEFAULT;
	req_arg.nping = NPING_DEFAULT;

	while((opt = getopt(argc, argv, "i:n:d:h")) != -1) {

		switch(opt) {

			case 'i':
				req_arg.ping_ipg = atoi(optarg) * 1000;
				break;

			case 'n':
				req_arg.nping = atoi(optarg);
				break;

			case 'd':
				req_arg.ic_dlen = atoi(optarg);
				break;

			case 'h':
				printf("Usage: %s -i <ping interval ms> -n <ping count> -d <data size> UID\n", argv[0]);
				exit(0);

			default:
				break;
		}
	}

	if(optind > (argc-1)) {
		printf("UID required\n");
		printf("Usage: %s -i <ping interval ms> -n <ping count> -d <data size> UID\n", argv[0]);
		exit(1);
	}

	req_arg.uid = atoi(argv[optind]);

	req_times = (struct timeval *)calloc(req_arg.nping, sizeof(struct timeval));
	if(!req_times) {
		exit(1);
	}

	rep_times = (struct timeval *)calloc(req_arg.nping, sizeof(struct timeval));
	if(!rep_times) {
		exit(1);
	}

	pthread_create(&req_thr, NULL, req_thr_func, &req_arg);

	pthread_create(&rep_thr, NULL, rep_thr_func, NULL);

	sleep(((req_arg.nping * req_arg.ping_ipg)/1000000) + 5);

	lost = 0;
	for(i = 0; i < req_arg.nping; i++) {
		if(req_times[i].tv_sec != 0) {
			if(rep_times[i].tv_sec == 0) {
				lost++;
			}
		}
	}
	printf("%d\n", lost);

	return 0;
}

uint16_t	icmp6_cksum (
		struct	ip6_hdr *ip6
		)
{
	uint32_t total;
	uint16_t *ptr16;
	int	plen;
	int	i;
	uint16_t cksum;

#pragma pack(1)
	struct	{
		uint8_t	ipsrc[16];
		uint8_t ipdst[16];
		uint32_t iplen;
		uint8_t zeros[3];
		uint8_t ipnxt;
	} pseudo;
#pragma pack()

	memcpy(pseudo.ipsrc, ip6->ip6_src.s6_addr, 16);
	memcpy(pseudo.ipdst, ip6->ip6_dst.s6_addr, 16);
	pseudo.iplen = ip6->ip6_plen;
	memset(pseudo.zeros, 0, 3);
	pseudo.ipnxt = 58;

	total = 0;
	ptr16 = (uint16_t *)&pseudo;
	for(i = 0; i < 20; i++) {
		total += htons(*ptr16);
		ptr16++;
	}

	plen = ntohs(ip6->ip6_plen);
	ptr16 = (uint16_t *)(ip6 + 1);
	for(i = 0; i < plen/2; i++) {
		total += htons(*ptr16);
		ptr16++;
	}

	if(plen & 1) {
		uint8_t last[2];
		last[0] = *((uint8_t *)ptr16);
		last[1] = 0;
		total += htons(*((uint16_t *)last));
	}

	while((total&0xFFFF0000) != 0) {
		total = (total&0xFFFF) + ((total>>16)&0xFFFF);
	}

	cksum = (~(total&0xFFFF))&0xFFFF;

	return cksum;
}

void	*req_thr_func (
		void	*arg
		)
{
	int	req_sock;
	struct	ip6_hdr *ip6;
	struct	icmp6_hdr *ic6;
	struct	req_thr_arg *r_arg;
	uint16_t cksum;
	struct	sockaddr_in6 dstaddr;
	struct	timeval t1, t2, td;
	int	err;
	int	slp_time;
	int	ic_seq = 0;
	int	i;

	r_arg = (struct req_thr_arg *)arg;

	req_sock = socket(AF_INET6, SOCK_RAW, IPPROTO_RAW);
	if(req_sock == -1) {
		perror("socket()");
		exit(1);
	}

	ip6 = (struct ip6_hdr *)malloc(40 + 4 + r_arg->ic_dlen);
	if(!ip6) {
		exit(1);
	}

	for(i = 0; i < r_arg->nping; i++) {

		gettimeofday(&t1, NULL);

		memset(ip6, 0, sizeof(*ip6));
		ip6->ip6_vfc = 0x60;
		ip6->ip6_plen = htons(4 + r_arg->ic_dlen);
		ip6->ip6_nxt = 58;
		ip6->ip6_hlim = 255;
		memcpy(ip6->ip6_src.s6_addr, ip6_prefix, 16);
		ip6->ip6_src.s6_addr[15] = 0;
		memcpy(ip6->ip6_dst.s6_addr, ip6_prefix, 16);
		ip6->ip6_dst.s6_addr[15] = r_arg->uid;

		ic6 = (struct icmp6_hdr *)(ip6 + 1);
		memset(ic6, 0, sizeof(*ic6));
		ic6->icmp6_type = 128;
		ic6->icmp6_code = 0;
		ic6->icmp6_cksum = 0;
		ic6->icmp6_data16[0] = htons(0xdc98);
		ic6->icmp6_data16[1] = htons(0xdc98);
		ic6->icmp6_data32[1] = ic_seq++;

		cksum = icmp6_cksum(ip6);
		ic6->icmp6_cksum = htons(cksum);

		memset(&dstaddr, 0, sizeof(dstaddr));
		dstaddr.sin6_family = AF_INET6;
		dstaddr.sin6_addr = ip6->ip6_dst;

		gettimeofday(&t2, NULL);

		timersub(&t2, &t1, &td);

		slp_time = r_arg->ping_ipg - (td.tv_sec * 1000000 + td.tv_usec);
		if(slp_time > 0) {
			usleep(slp_time);
		}

		gettimeofday(&req_times[ic_seq-1], NULL);
		err = sendto(req_sock, ip6, 40+4+r_arg->ic_dlen, 0, (struct sockaddr *)&dstaddr, sizeof(dstaddr));
		if(err < 0) {
			perror("sendto()");
			break;
		}
	}

	return NULL;
}

void	*rep_thr_func (
		void	*arg
		)
{
	int	rep_sock;
	char	*pkt;
	struct	ip6_hdr *ip6;
	struct	icmp6_hdr *ic6;
	struct	timeval t1;
	struct	sockaddr_ll their_addr;
	socklen_t their_alen;
	int	err;
	int	ic_seq;

	rep_sock = socket(AF_PACKET, SOCK_RAW, htons(ETHERTYPE_IPV6));
	if(rep_sock == -1) {
		perror("socket()");
		exit(1);
	}

	pkt = (char *)malloc(1500);
	if(!pkt) {
		exit(1);
	}

	while(1) {

		their_alen = sizeof(their_addr);
		err = recvfrom(rep_sock, pkt, 1500, 0, (struct sockaddr *)&their_addr, &their_alen);
		if(err < 0) {
			perror("recvfrom()");
			break;
		}

		gettimeofday(&t1, NULL);

		ip6 = (struct ip6_hdr *)(pkt + 14);
		if(ip6->ip6_nxt != 58) {
			continue;
		}

		ic6 = (struct icmp6_hdr *)(ip6 + 1);

		if(ic6->icmp6_type != 129) {
			continue;
		}

		if(ntohs(ic6->icmp6_data16[0]) != 0xdc98) {
			continue;
		}

		if(ntohs(ic6->icmp6_data16[1]) != 0xdc98) {
			continue;
		}

		ic_seq = ic6->icmp6_data32[1];
		//printf("Reply %d\n", ic_seq);

		rep_times[ic_seq] = t1;
	}

	return NULL;
}
