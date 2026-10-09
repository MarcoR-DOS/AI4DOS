/* Host-only transport harness for the same client main/parser/HMAC. Not DOS networking. */
#include <arpa/inet.h>
#include <errno.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>
#include <string.h>
#include "net.h"
static int fd=-1;
int net_open(const char *server,unsigned port)
{
    struct sockaddr_in addr;struct timeval timeout;int one=1;
    memset(&addr,0,sizeof(addr));addr.sin_family=AF_INET;addr.sin_port=htons((unsigned short)port);
    if(inet_pton(AF_INET,server,&addr.sin_addr)!=1)return 0;
    fd=socket(AF_INET,SOCK_STREAM,0);if(fd<0)return 0;
    timeout.tv_sec=180;timeout.tv_usec=0;
    setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));
    setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout));
#ifdef SO_NOSIGPIPE
    setsockopt(fd,SOL_SOCKET,SO_NOSIGPIPE,&one,sizeof(one));
#else
    (void)one;
#endif
    if(connect(fd,(struct sockaddr *)&addr,sizeof(addr))!=0){net_close();return 0;}return 1;
}
int net_write(const char *line)
{
    char buffer[1027];size_t size=strlen(line),at=0;ssize_t n;
    if(size>1024)return 0;memcpy(buffer,line,size);buffer[size++]='\r';buffer[size++]='\n';
    while(at<size){n=send(fd,buffer+at,size-at,0);if(n<0&&errno==EINTR)continue;if(n<=0)return 0;at+=(size_t)n;}
    return 1;
}
int net_read(char *line,unsigned cap)
{
    unsigned used=0;char c;ssize_t n;
    for(;;){n=recv(fd,&c,1,0);if(n<0&&errno==EINTR)continue;if(n!=1)return 0;
        if(c=='\n'){if(used&&line[used-1]=='\r')--used;line[used]=0;return 1;}
        if(!c||used+1>=cap)return 0;line[used++]=c;
    }
}
void net_close(void){if(fd>=0)close(fd);fd=-1;}

void net_disconnect(void){net_close();}
