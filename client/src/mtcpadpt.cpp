#include <stdio.h>
#include <stdarg.h>
#include <malloc.h>
#include <stdlib.h>
#include <string.h>
#include "types.h"
#include "timer.h"
#include "utils.h"
#include "packet.h"
#include "arp.h"
#include "ip.h"
#include "tcp.h"
#include "tcpsockm.h"
#include "net.h"
#include "ramdiag.h"
extern "C" {
#include "ui.h"
}

/* mTCP Utils diagnostics belong in the active DOS UI. Non-stderr output
   retains ordinary stdio behavior. Bound and sanitize each diagnostic. */
extern "C" int ai4dos_mtcp_fprintf(FILE *stream, const char *format, ...)
{
    char text[256];
    unsigned i;
    int rc;
    va_list args;
    va_start(args, format);
    if (stream != stderr) {
        rc = vfprintf(stream, format, args);
        va_end(args);
        return rc;
    }
    rc = vsnprintf(text, sizeof(text), format, args);
    va_end(args);
    text[sizeof(text)-1] = 0;
    for (i = 0; text[i]; ++i)
        if ((unsigned char)text[i] < 32 || (unsigned char)text[i] > 126)
            text[i] = ' ';
    while (i && text[i-1] == ' ') text[--i] = 0;
    if (!i) return rc;
    ui_scroll_lines(32767);
    ui_begin(ROLE_SYSTEM, "System");
    ui_append(text);
    ui_end();
    return rc;
}

static TcpSocket *socket_ptr = 0;
static int stack_started = 0;
static int connected = 0;
static clockTicks_t connect_started = 0;
static uint16_t next_local_port = 0;

static void __interrupt __far break_handler(void) {}
static void __interrupt __far ctrl_c_handler(void) {}

static int parse_ipv4(const char *text, IpAddr_t address)
{
    unsigned a, b, c, d;
    char tail;
    if (sscanf(text, "%u.%u.%u.%u%c", &a, &b, &c, &d, &tail) != 4)
        return 0;
    if (a > 255 || b > 255 || c > 255 || d > 255) return 0;
    address[0] = (uint8_t)a;
    address[1] = (uint8_t)b;
    address[2] = (uint8_t)c;
    address[3] = (uint8_t)d;
    return 1;
}

/* Read the configuration already parsed by mTCP; mirror its subnet test.
   No DHCP requirement, routing changes, or packet-driver calls here. */
static int validate_connection(const char *server, IpAddr_t address)
{
    unsigned i;
    if (!parse_ipv4(server, address)) return NET_START_INVALID_SERVER;
    if (Ip::isSame(MyIpAddr, IpInvalid)) return NET_START_NO_IP;
    if (Ip::isSame(Gateway, IpInvalid) &&
        !Ip::isSame(address, IpBroadcastNonRoutable)) {
        for (i = 0; i < 4; ++i)
            if ((MyIpAddr[i] & Netmask[i]) != (address[i] & Netmask[i]))
                return NET_START_NO_GATEWAY;
    }
    return 0;
}

static int open_connection(const char *server, unsigned port)
{
    IpAddr_t address;
    uint16_t local_port;
    int rc;

    rc = validate_connection(server, address);
    if (rc != 0) return rc;
    socket_ptr = TcpSocketMgr::getSocket();
    if (socket_ptr == 0 || socket_ptr->setRecvBuffer(768) != 0) {
        return -5;
    }
    /* A restarted timer must not reuse the previous TCP four-tuple. */
    if (!next_local_port) next_local_port = (uint16_t)(2048U + (unsigned)(TIMER_GET_CURRENT() % 2000UL));
    local_port = next_local_port++;
    if (next_local_port >= 60000U) next_local_port = 2048U;
    if (socket_ptr->connectNonBlocking(local_port, address,
                                       (uint16_t)port) != 0) {
        return -6;
    }
    connect_started = TIMER_GET_CURRENT();
    connected = 0;
    return 0;
}

static int close_connection(void)
{
    clockTicks_t started;
    int done = 0;
    if (socket_ptr == 0) return 1;
    socket_ptr->closeNonblocking();
    started = TIMER_GET_CURRENT();
    while (!(done = socket_ptr->isCloseDone()) &&
           Timer_diff(started, TIMER_GET_CURRENT()) <
           TIMER_MS_TO_TICKS(5200UL)) {
        PACKET_PROCESS_SINGLE;
        Arp::driveArp();
        Tcp::drivePackets();
    }
    if (!done) done = socket_ptr->isCloseDone();
    if (!done) return 0;
    TcpSocketMgr::freeSocket(socket_ptr);
    socket_ptr = 0;
    connected = 0;
    return 1;
}

extern "C" int mtcp_adapter_start(const char *server, unsigned port)
{
    int rc;
    IpAddr_t address;
    if (stack_started) {
        if (!close_connection()) return -1;
        return open_connection(server, port);
    }
    if (Utils::parseEnv() != 0) return -3;
    rc = validate_connection(server, address);
    if (rc != 0) return rc;
    rc = Utils::initStack(1, 4, break_handler, ctrl_c_handler);
    if (rc != 0) return rc == -2 ? -4 : -7;
    stack_started = 1;
    ram_mark(2);
    rc = open_connection(server, port);
    if (rc != 0) mtcp_adapter_stop();
    return rc;
}

extern "C" int mtcp_adapter_pump(void)
{
    if (!stack_started || socket_ptr == 0) return -1;
    PACKET_PROCESS_MULT(4);
    Arp::driveArp();
    Tcp::drivePackets();
    if (!connected) {
        if (socket_ptr->isConnectComplete()) connected = 1;
        else if (socket_ptr->isClosed() ||
                 Timer_diff(connect_started, TIMER_GET_CURRENT()) >
                 TIMER_MS_TO_TICKS(10000UL)) return -1;
    }
    if (connected && socket_ptr->isRemoteClosed() &&
        !socket_ptr->recvDataWaiting()) return -1;
    return connected;
}

extern "C" int mtcp_adapter_recv(char *buffer, unsigned capacity)
{
    if (!connected || socket_ptr == 0 || capacity == 0) return 0;
    return socket_ptr->recv((uint8_t *)buffer, (uint16_t)capacity);
}

extern "C" int mtcp_adapter_send(const char *buffer, unsigned length)
{
    if (!connected || socket_ptr == 0) return -1;
    return socket_ptr->send((uint8_t *)buffer, (uint16_t)length);
}

extern "C" unsigned long mtcp_adapter_ticks(void)
{
    return stack_started ? (unsigned long)TIMER_GET_CURRENT() : 0UL;
}

extern "C" void mtcp_adapter_disconnect(void)
{
    if (stack_started) close_connection();
}

extern "C" void mtcp_adapter_stop(void)
{
    if (!stack_started) return;
    close_connection();
    Utils::endStack();
    socket_ptr = 0;
    connected = 0;
    stack_started = 0;
}

