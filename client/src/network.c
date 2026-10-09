#include <string.h>
#include "net.h"
#include "protocol.h"
#include "ui.h"
#define TIMEOUT_TICKS (180UL*18UL)
static char incoming[128];
static unsigned at,count;
static int start_error;
int net_start_error(void){return start_error;}
static int wait_pump(unsigned long started)
{
    int state;
    if(!ui_poll_wait())return -1;
    state=mtcp_adapter_pump();
    if(state<0||mtcp_adapter_ticks()-started>TIMEOUT_TICKS)return -1;
    return state;
}
int net_open(const char *server,unsigned port)
{
    unsigned long started;
    at=count=0;
    start_error=mtcp_adapter_start(server,port);
    if(start_error!=0)return 0;
    started=mtcp_adapter_ticks();
    for(;;){int rc=wait_pump(started);if(rc<0){net_disconnect();return 0;}if(rc>0)return 1;}
}
int net_write(const char *line)
{
    static char buffer[LINE_CAP+2];unsigned n,pos=0;int rc;
    unsigned long started=mtcp_adapter_ticks();
    n=(unsigned)strlen(line);if(n>=LINE_CAP)return 0;
    memcpy(buffer,line,n);buffer[n++]='\r';buffer[n++]='\n';
    while(pos<n){
        if(wait_pump(started)<0)return 0;
        rc=mtcp_adapter_send(buffer+pos,n-pos);if(rc<0)return 0;
        if(rc>0){pos+=(unsigned)rc;started=mtcp_adapter_ticks();}
    }
    return 1;
}
int net_read(char *line,unsigned capacity)
{
    unsigned used=0;int rc;char ch;
    unsigned long started=mtcp_adapter_ticks();
    for(;;){
        if(at==count){
            if(wait_pump(started)<0)return 0;
            rc=mtcp_adapter_recv(incoming,sizeof(incoming));if(rc<0)return 0;if(rc==0)continue;
            at=0;count=(unsigned)rc;started=mtcp_adapter_ticks();
        }
        ch=incoming[at++];
        if(ch=='\n'){
            if(used&&line[used-1]=='\r')--used;
            line[used]=0;return 1;
        }
        if(ch==0||used+1>=capacity)return 0;
        line[used++]=ch;
    }
}
void net_disconnect(void){mtcp_adapter_disconnect();at=count=0;}
void net_close(void){mtcp_adapter_stop();at=count=0;}
