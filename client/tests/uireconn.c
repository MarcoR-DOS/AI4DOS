/* Emulator-only keys and readbacks; actual main/protocol/mTCP remain unchanged. */
#include <bios.h>
static unsigned reconnect_key(unsigned service);
#define _bios_keybrd reconnect_key
#define ui_status tested_status
#define ui_init tested_init
#define ui_shutdown tested_shutdown
#define ui_notice tested_notice
#include "../src/ui.c"
#undef _bios_keybrd
#undef ui_status
#undef ui_init
#undef ui_shutdown
#undef ui_notice
static unsigned failures,resumes,new_chats;
static unsigned saved_size,saved_messages;
static unsigned long saved_hash;
static char saved_session[13];
static UiStatus previous_status=UI_CONNECTING;
static unsigned long transcript_prefix_hash(unsigned bytes)
{
    unsigned i;int ch;unsigned long h=5381;FILE *f=fopen("RECPRE.TMP","wb");
    if(!f)return 0;
    if(!transcript_save(f)){fclose(f);return 0;}fclose(f);
    f=fopen("RECPRE.TMP","rb");if(!f)return 0;
    for(i=0;i<bytes;++i){ch=fgetc(f);if(ch==EOF){h=0;break;}h=(h*33UL)^(unsigned char)ch;}
    fclose(f);remove("RECPRE.TMP");return h;
}
int ui_init(unsigned cp)
{
    int ok=tested_init(cp);FILE *f=fopen("RECON.LOG","w");
    if(f){fputs("CONNECTING\n",f);fclose(f);}return ok;
}
void ui_status(UiStatus status)
{
    FILE *f;
    if(status==UI_CONNECTING){
        saved_size=transcript_size();saved_messages=transcript_messages();
        saved_hash=transcript_prefix_hash(saved_size-3U*saved_messages);strcpy(saved_session,session_text);
    }
    tested_status(status);
    f=fopen("RECON.LOG","a");if(f){fprintf(f,"%s %s\n",ui_status_label(1),session_text);fclose(f);}
    if(status==UI_ONLINE&&previous_status==UI_CONNECTING&&saved_session[0]){
        if(strcmp(saved_session,session_text)==0){
            ++resumes;
            /* Existing exported history stays intact; two local system records
               document the attempt and restored connection. */
            if(transcript_messages()!=saved_messages+2U||
               transcript_role(saved_messages)!=ROLE_SYSTEM||
               transcript_role(saved_messages+1U)!=ROLE_SYSTEM||
               saved_hash!=transcript_prefix_hash(saved_size-3U*saved_messages))++failures;
        }else{
            ++new_chats;
            if(transcript_messages()!=0&&
               !(transcript_messages()==1&&transcript_role(0)==ROLE_SYSTEM))++failures;
        }
    }
    previous_status=status;
}
void ui_notice(const char *text)
{
    FILE *f=fopen("RECON.LOG","a");if(f){fprintf(f,"NOTICE %s\n",text);fclose(f);}
    tested_notice(text);
}
void ui_shutdown(void)
{
    FILE *f=fopen("RECON.LOG","a");
    if(f){fprintf(f,"RESULT %u %u %u\n",failures,resumes,new_chats);fclose(f);}
    tested_shutdown();
}
static unsigned reconnect_key(unsigned service)
{
    static const char *steps[]={"first\r","drop\r","/save\r","PART1\r","\001","/reconnect\r",
      "after1\r","drop\r","/reconnect\r","after2\r","/save\r","RESUMED\r","\002","drop\r","/reconnect\r",
      "new-after\r","lose\r","/reconnect\r","/save\r","LOST\r","\002",
      "final\r","/save\r","FINAL\r","/quit\r","\003"};
    static unsigned step,at;
    unsigned key;
    if(busy||step>=sizeof(steps)/sizeof(steps[0]))return 0;
    key=(unsigned char)steps[step][at];
    if(key==1)key=0x4900;else if(key==2)key=0x3c00;else if(key==3)key=0x4400;
    if(service==_KEYBRD_READ){
        if(!steps[step][++at]){++step;at=0;}
    }
    return key;
}
