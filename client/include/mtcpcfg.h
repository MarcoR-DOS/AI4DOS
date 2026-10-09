#ifndef AI4DOS_MTCP_CONFIG_H
#define AI4DOS_MTCP_CONFIG_H
#define CFG_H "mtcpcfg.h"
#define MTCP_PROGRAM_NAME "ai4dos"
#include "global.cfg"
#define NOTRACE
#define COMPILE_ARP
#define COMPILE_TCP
#undef PACKET_BUFFERS
#define PACKET_BUFFERS 4
#undef TCP_MAX_SOCKETS
#define TCP_MAX_SOCKETS 1
#undef TCP_MAX_XMIT_BUFS
#define TCP_MAX_XMIT_BUFS 4
#undef TCP_SOCKET_RING_SIZE
#define TCP_SOCKET_RING_SIZE 4
#undef TCP_CLOSE_TIMEOUT
#define TCP_CLOSE_TIMEOUT 5000UL
#endif
