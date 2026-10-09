/* Generic fixed far-buffer/CRLF/limit design selectively adapted from Georgi.
   Records carry an explicit role and payload length; labels are presentation.
   Save exports only readable text, never internal record headers. */
#include <string.h>
#include "transcr.h"
#ifdef __WATCOMC__
static unsigned char __far text_buffer[TRANSCRIPT_CAPACITY];
#else
static unsigned char text_buffer[TRANSCRIPT_CAPACITY];
#endif
#define RECORD_HEADER 3U
#define END_RESERVE 4U
static unsigned used,record_start,body_start,messages;
static int active,full,warned;
static unsigned record_length(unsigned offset)
{return (unsigned)text_buffer[offset+1]|((unsigned)text_buffer[offset+2]<<8);}
static void finish_length(void)
{
    unsigned n=used-record_start-RECORD_HEADER;
    text_buffer[record_start+1]=(unsigned char)n;
    text_buffer[record_start+2]=(unsigned char)(n>>8);
}
void transcript_reset(void){used=messages=0;active=full=warned=0;}
unsigned transcript_size(void){return used;}
unsigned transcript_messages(void){return messages;}
Role transcript_role(unsigned index)
{
    unsigned offset=0,i;
    if(index>=messages)return ROLE_SYSTEM;
    for(i=0;i<index;++i)offset+=RECORD_HEADER+record_length(offset);
    return (Role)text_buffer[offset];
}
int transcript_full(void){return full;}
int transcript_warning(void)
{if(!warned&&used>=TRANSCRIPT_WARNING){warned=1;return 1;}return 0;}
static unsigned normalized_byte(unsigned char ch)
{
    if(ch=='\r'||(ch<32&&ch!='\n'&&ch!='\t')||ch==127)return 0;
    return ch=='\n'?2U:1U;
}
static unsigned long normalized_size(const char *text)
{unsigned long n=0;while(*text)n+=normalized_byte((unsigned char)*text++);return n;}
int transcript_can_message(Role role,const char *label,const char *text)
{
    unsigned long need;
    if((unsigned)role>ROLE_SYSTEM||strlen(label)>74||active||full)return 0;
    need=RECORD_HEADER+strlen(label)+3UL+normalized_size(text)+END_RESERVE;
    if(need>TRANSCRIPT_CAPACITY-used){full=1;return 0;}return 1;
}
int transcript_begin(Role role,const char *label)
{
    unsigned n=(unsigned)strlen(label);
    if((unsigned)role>ROLE_SYSTEM||n>74||active||full)return 0;
    if((unsigned long)n+RECORD_HEADER+3U+END_RESERVE>TRANSCRIPT_CAPACITY-used){full=1;return 0;}
    record_start=used;text_buffer[used++]=(unsigned char)role;used+=2;
    memcpy(text_buffer+used,label,n);used+=n;
    text_buffer[used++]=':';text_buffer[used++]='\r';text_buffer[used++]='\n';
    body_start=used;active=1;++messages;finish_length();return 1;
}
unsigned transcript_append(const char *text)
{
    unsigned accepted=0,n;unsigned char ch;
    if(!active||full)return 0;
    while((ch=(unsigned char)text[accepted])!=0){
        n=normalized_byte(ch);
        if(n>TRANSCRIPT_CAPACITY-used-END_RESERVE){full=1;break;}
        if(n){
            if(ch=='\n')text_buffer[used++]='\r';
            text_buffer[used++]=ch=='\t'?' ':ch;
        }
        ++accepted;
    }
    if(used==TRANSCRIPT_CAPACITY-END_RESERVE)full=1;
    finish_length();return accepted;
}
void transcript_end(void)
{
    if(!active)return;
    /* Remove only terminal newlines; preserve blank lines inside the message. */
    while(used>=body_start+2&&text_buffer[used-2]=='\r'&&text_buffer[used-1]=='\n')used-=2;
    text_buffer[used++]='\r';text_buffer[used++]='\n';
    text_buffer[used++]='\r';text_buffer[used++]='\n';
    finish_length();active=0;if(used==TRANSCRIPT_CAPACITY)full=1;
}
int transcript_save(FILE *fp)
{
    unsigned offset=0,n;
    if(active||!fp)return 0;
    while(offset<used){
        if(used-offset<RECORD_HEADER)return 0;
        n=record_length(offset);
        if(n>used-offset-RECORD_HEADER)return 0;
        if(fwrite(text_buffer+offset+RECORD_HEADER,1,n,fp)!=n)return 0;
        offset+=RECORD_HEADER+n;
    }
    return !ferror(fp);
}
