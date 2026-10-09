/* Deterministic transport-clock test; same network.c, no packet-driver emulation. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "net.h"
static unsigned long ticks;
static int fail,payload,disconnected,stopped,started;
int ui_poll_wait(void){return 1;}
int mtcp_adapter_start(const char *s,unsigned p){(void)s;(void)p;++started;return 0;}
int mtcp_adapter_pump(void){return fail?-1:1;}
unsigned long mtcp_adapter_ticks(void){ticks+=1000;return ticks;}
int mtcp_adapter_recv(char *b,unsigned cap)
{(void)cap;if(payload){strcpy(b,"DATA one\r\nEND\r\n");payload=0;return 15;}return 0;}
int mtcp_adapter_send(const char *b,unsigned n){(void)b;return (int)n;}
void mtcp_adapter_disconnect(void){++disconnected;}
void mtcp_adapter_stop(void){++stopped;}
int main(void)
{
    char line[32];assert(net_open("test",1983));
    payload=1;assert(net_read(line,sizeof(line))&&strcmp(line,"DATA one")==0);
    /* Socket reports closed after its last recv; buffered complete END survives. */
    fail=1;assert(net_read(line,sizeof(line))&&strcmp(line,"END")==0);
    assert(!net_read(line,sizeof(line)));net_disconnect();assert(disconnected==1&&!stopped);
    fail=0;assert(net_open("test",1983));
    assert(!net_read(line,sizeof(line))); /* Gateway silent: inactivity timeout. */
    net_disconnect();payload=1;assert(net_open("test",1983));
    assert(net_read(line,sizeof(line))&&strcmp(line,"DATA one")==0);
    net_close();assert(stopped==1&&started==3);
    puts("AI4DOS NETWORK PASS: EOF, buffered END, timeout, disconnect/reopen/reset");return 0;
}
