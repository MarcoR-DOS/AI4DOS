#include <string.h>
#include "protocol.h"

static int hex(const char *s, unsigned n)
{
    unsigned i;
    if(strlen(s)!=n)return 0;
    for(i=0;i<n;++i)if(!((s[i]>='0'&&s[i]<='9')||(s[i]>='a'&&s[i]<='f')))return 0;
    return 1;
}
static int copy(char *dst,const char *src)
{
    unsigned n=(unsigned)strlen(src);
    if(n>=DATA_CAP)return 0;
    memcpy(dst,src,n+1);return 1;
}
static int decode(char *dst,const char *src)
{
    unsigned n=0;char c;
    if(strlen(src)>512)return 0;
    while((c=*src++)!=0){
        if(c=='\\'){
            c=*src++;
            if(c=='n')c='\n';else if(c=='r')c='\r';else if(c=='t')c='\t';
            else if(c!='\\')return 0;
        }else if((unsigned char)c<32||c==127)return 0;
        if(n+1>=DATA_CAP)return 0;dst[n++]=c;
    }
    dst[n]=0;return 1;
}
void protocol_init(Protocol *p){p->state=WAIT_GREETING;p->session[0]=0;}
int protocol_expect_session(Protocol *p){if(p->state!=READY)return 0;p->state=WAIT_SESSION;return 1;}
int protocol_expect_resume(Protocol *p,const char *session)
{if(p->state!=READY||!hex(session,12))return 0;if(session!=p->session)strcpy(p->session,session);p->state=WAIT_RESUME;return 1;}
int protocol_expect_reply(Protocol *p){if(p->state!=READY||!p->session[0])return 0;p->state=WAIT_BEGIN;return 1;}
int protocol_expect_close(Protocol *p){if(p->state!=READY)return 0;p->state=WAIT_BYE;return 1;}
EventType protocol_parse(Protocol *p,const char *line,Event *e)
{
    e->type=EV_INVALID;e->role=ROLE_SYSTEM;e->text[0]=0;
    if(strlen(line)>=LINE_CAP)return EV_INVALID;
    if(strncmp(line,"ERROR ",6)==0&&copy(e->text,line+6)){
        p->state=FAILED;return e->type=EV_ERROR;
    }
    switch(p->state){
    case WAIT_GREETING:
        if(strcmp(line,WIRE_GREETING)==0||strcmp(line,"OK AI4DOS/0.2 UTF-8")==0){p->state=WAIT_CHALLENGE;e->type=EV_GREETING;}break;
    case WAIT_CHALLENGE:
        if(strncmp(line,"CHALLENGE ",10)==0&&hex(line+10,64)){
            copy(e->text,line+10);p->state=WAIT_AUTH;e->type=EV_CHALLENGE;
        }break;
    case WAIT_AUTH:
        if(strcmp(line,"OK AUTH")==0){p->state=READY;e->type=EV_AUTH;}break;
    case WAIT_SESSION:
        if(strncmp(line,"SESSION ",8)==0&&hex(line+8,12)){
            strcpy(p->session,line+8);copy(e->text,line+8);p->state=READY;e->type=EV_SESSION;
        }break;
    case WAIT_RESUME:
        if(strcmp(line,"OK RESUME")==0){p->state=READY;e->type=EV_RESUME;}break;
    case WAIT_BEGIN:
        if(strcmp(line,"BEGIN")==0||strncmp(line,"BEGIN ",6)==0){
            const char *label=line+6;
            if(line[5]){
                unsigned i,n=(unsigned)strlen(label);
                if(!n||n>74)return EV_INVALID;
                for(i=0;i<n;++i)if((unsigned char)label[i]<32||label[i]==127)return EV_INVALID;
                if(strcmp(label,"ChatGPT")==0||strcmp(label,"Claude")==0||strcmp(label,"Gemini")==0||
                   strcmp(label,"Mistral")==0||strcmp(label,"NVIDIA")==0||strcmp(label,"OpenRouter")==0)
                    copy(e->text,label);
            }
            p->state=IN_REPLY;e->type=EV_BEGIN;e->role=ROLE_AI;
        }break;
    case IN_REPLY:
        if(strcmp(line,"END")==0){p->state=READY;e->type=EV_END;e->role=ROLE_AI;}
        else if(strncmp(line,"DATA ",5)==0&&decode(e->text,line+5)){e->type=EV_DATA;e->role=ROLE_AI;}break;
    case WAIT_BYE:
        if(strcmp(line,"OK BYE")==0){e->type=EV_BYE;}break;
    default:break;
    }
    return e->type;
}
