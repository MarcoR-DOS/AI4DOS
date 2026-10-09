/* Host and actual DOS/8086 functional stress; never linked into release. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#ifdef __WATCOMC__
#include <direct.h>
#define SEP "\\"
#else
#include <unistd.h>
#define SEP "/"
#endif
#include "transcr.h"
#include "chatfile.h"
#include "ui.h"
#include "controls.h"
#include "l10n.h"
static void checked(int value,unsigned line)
{if(!value){printf("FAIL line %u\n",line);exit(1);}}
#define CHECK(x) checked(!!(x),__LINE__)
static char block[513];
static unsigned read_saved(const char *path,char *out,unsigned cap)
{
    FILE *f;unsigned n;f=fopen(path,"rb");CHECK(f!=NULL);n=(unsigned)fread(out,1,cap-1,f);out[n]=0;CHECK(!ferror(f));CHECK(fclose(f)==0);return n;
}
static int visible(const char *text)
{unsigned i;for(i=0;i<18;++i)if(strstr(ui_line(i),text))return 1;return 0;}
static void type_name(const char *name)
{while(*name)controls_handle((unsigned char)*name++,0);}
static void save_modal(const char *name)
{
    controls_handle(0x3f00,0);type_name(name);controls_handle(13,0);
    CHECK(!controls_active());
}
static void transcript_core(void)
{
    FILE *f;char text[300];unsigned i,accepted,size;unsigned long sum=0;
    transcript_reset();CHECK(transcript_can_message(ROLE_USER,"You","Hello."));
    CHECK(transcript_begin(ROLE_USER,"Other"));CHECK(transcript_append("Hello.\n")==7);transcript_end();
    CHECK(transcript_begin(ROLE_AI,"You"));transcript_append("first\n\nlast\n\n");transcript_end();
    CHECK(transcript_begin(ROLE_SYSTEM,"System"));transcript_append("notice");transcript_end();
    CHECK(transcript_messages()==3&&transcript_role(0)==ROLE_USER&&transcript_role(1)==ROLE_AI&&transcript_role(2)==ROLE_SYSTEM);
    f=fopen("ROLES.TXT","wb");CHECK(f!=NULL&&transcript_save(f));CHECK(fclose(f)==0);
    read_saved("ROLES.TXT",text,sizeof(text));
    CHECK(strcmp(text,"Other:\r\nHello.\r\n\r\nYou:\r\nfirst\r\n\r\nlast\r\n\r\nSystem:\r\nnotice\r\n\r\n")==0);
    transcript_reset();memset(block,'x',512);block[512]=0;CHECK(transcript_begin(ROLE_AI,"AI"));
    while(transcript_size()<TRANSCRIPT_WARNING)CHECK(transcript_append(block)==512);
    CHECK(transcript_warning()&&!transcript_warning());
    do{accepted=transcript_append(block);CHECK(accepted<=512&&transcript_size()<=TRANSCRIPT_CAPACITY-4);}while(!transcript_full());
    transcript_end();size=transcript_size();CHECK(size<=TRANSCRIPT_CAPACITY);
    CHECK(transcript_append("overflow")==0&&!transcript_begin(ROLE_USER,"You"));CHECK(size==transcript_size());
    f=fopen("LIMIT.TXT","wb");CHECK(f!=NULL&&transcript_save(f));CHECK(fclose(f)==0);
    f=fopen("LIMIT.TXT","rb");CHECK(f!=NULL);for(i=0;fgetc(f)!=EOF;++i)++sum;CHECK(i>60000&&i<=TRANSCRIPT_CAPACITY);fclose(f);CHECK(sum==i);
    transcript_reset();CHECK(!transcript_full()&&transcript_size()==0&&transcript_messages()==0);
}
static void filenames(void)
{
    static const char *good[]={"HELLO.TXT","a","lower.txt","12345678.123","A_B-C.LOG"};
    static const char *bad[]={"",".TXT","A.","A..TXT","123456789.TXT","A.1234","A B.TXT","A/B.TXT","A\\B.TXT","*.TXT","CON","con.txt","PRN.TXT","AUX","NUL","COM1.LOG","lpt9","../A","C:A.TXT"};
    char output[13];unsigned i;
    for(i=0;i<sizeof(good)/sizeof(good[0]);++i){CHECK(chat_filename(good[i],output)&&(strchr(good[i],'.')?strcmp(good[i],output)==0:strlen(output)==strlen(good[i])+4&&strncmp(output,good[i],strlen(good[i]))==0&&strcmp(output+strlen(good[i]),".TXT")==0));}
    for(i=0;i<sizeof(bad)/sizeof(bad[0]);++i)CHECK(!chat_filename(bad[i],output));
}
static void ui_stress(Language lang)
{
    unsigned i,j,round,size;char text[250],name[13],path[40],content[500],anchor[77];FILE *f;struct stat st;
    language_set(lang);CHECK(ui_init(850));ui_busy(0);
    /* Product labels and language fallback survive the actual DOS Save path. */
    {
        static const char *labels[]={"ChatGPT","Claude","Gemini","Mistral","NVIDIA","OpenRouter",0};
        const char *label;unsigned k;
        for(k=0;k<7;++k){
            label=labels[k]?labels[k]:tr(TXT_AI);ui_clear_chat();
            ui_begin(ROLE_AI,labels[k]);ui_append("provider test");ui_end();
            sprintf(text,"%s: provider test",label);CHECK(visible(text));
            CHECK(transcript_role(0)==ROLE_AI);
            remove("CHATS" SEP "LABEL.TXT");CHECK(chat_save("LABEL.TXT",0)==CHAT_SAVE_OK);
            read_saved("CHATS" SEP "LABEL.TXT",content,sizeof(content));
            sprintf(text,"%s:\r\nprovider test\r\n\r\n",label);CHECK(strcmp(content,text)==0);
        }
        ui_clear_chat();
    }
    ui_help();controls_handle(27,0);ui_overlay_end();
    ui_begin(ROLE_USER,"You");ui_append("Hello.");ui_end();
    ui_begin(ROLE_AI,"You");ui_append("An AI role with a user-looking label.");ui_end();
    CHECK(transcript_role(0)==ROLE_USER&&transcript_role(1)==ROLE_AI);
    remove("CHATS" SEP "TEST.TXT");save_modal("TEST.TXT");CHECK(stat("CHATS",&st)==0);
    read_saved("CHATS" SEP "TEST.TXT",content,sizeof(content));CHECK(strstr(content,"You:\r\nHello."));
    /* Exact input remains visible and invalid; cancel does not write a corrected name. */
    controls_handle(0x3f00,0);type_name("BAD/NAME");controls_handle(13,0);CHECK(controls_active());controls_handle(27,0);
    CHECK(stat("CHATS" SEP "BADNAME",&st)!=0);
    controls_handle(0x3f00,0);type_name("CANCEL.TXT");controls_handle(27,0);
    CHECK(stat("CHATS" SEP "CANCEL.TXT",&st)!=0);
    controls_handle(0x3f00,0);type_name("TEST.TXT");controls_handle(13,0);CHECK(controls_active());
    controls_handle(13,0);CHECK(controls_active());controls_handle(27,0); /* no silent overwrite */
    controls_handle(0x3f00,0);type_name("TEST.TXT");controls_handle(13,0);controls_handle(0x3f00,0);CHECK(!controls_active());
    /* A recovery file must survive and the existing saved chat must remain intact. */
    f=fopen("CHATS" SEP "A4SAVE.$$$","wb");CHECK(f!=NULL);fputs("recovery",f);fclose(f);
    CHECK(chat_save("TEST.TXT",1)==CHAT_SAVE_ERROR);remove("CHATS" SEP "A4SAVE.$$$");
    read_saved("CHATS" SEP "TEST.TXT",content,sizeof(content));CHECK(strstr(content,"Hello."));
    /* Hundreds of records, repeated ring eviction/scroll/save/full/new cycles. */
    for(round=0;round<3;++round){
        ui_clear_chat();
        for(i=0;i<240;++i){
            sprintf(text,"M%03u: ",i);memset(text+6,'a'+i%20,170);strcpy(text+176," tail word crosses the DATA frame boundary\n");
            ui_begin(i%2?ROLE_AI:ROLE_USER,0);
            for(j=0;text[j];){char part[18];unsigned n=(unsigned)strlen(text+j);if(n>17)n=17;memcpy(part,text+j,n);part[n]=0;ui_append(part);j+=n;}
            ui_end();
            if(i==149){
                CHECK(!strstr(ui_line(0),"M000")&&visible("M149"));
                ui_scroll_page(-1);CHECK(ui_scroll_directions()==(UI_SCROLL_UP|UI_SCROLL_DOWN));
                strcpy(anchor,ui_line(0));ui_begin(ROLE_AI,0);ui_append("new arriving reply\nnext line");ui_end();CHECK(strcmp(anchor,ui_line(0))==0);
                ui_scroll_lines(-2000);CHECK(ui_scroll_directions()==UI_SCROLL_DOWN);
                ui_scroll_lines(1);ui_scroll_lines(-1);ui_scroll_page(200);CHECK(ui_scroll_directions()==UI_SCROLL_UP);
                sprintf(name,"R%u%u.TXT",(unsigned)lang,round);strcpy(path,"CHATS" SEP);strcat(path,name);remove(path);save_modal(name);
                f=fopen(path,"rb");CHECK(f!=NULL);CHECK(fread(content,1,sizeof(content)-1,f)>0);content[sizeof(content)-1]=0;fclose(f);CHECK(strstr(content,"M000"));
            }
        }
        CHECK(transcript_messages()>240&&transcript_size()>50000&&!transcript_full());
        /* Finish until hard limit, then ensure UI/scrollback freeze and Save remains available. */
        ui_begin(ROLE_AI,0);while(!transcript_full())ui_append(block);ui_end();
        size=transcript_size();
        ui_begin(ROLE_AI,0);ui_append("must not overwrite");ui_end();CHECK(size==transcript_size());
        CHECK(visible(tr(TXT_TRANSCRIPT_FULL)));
        sprintf(name,"F%u%u.TXT",(unsigned)lang,round);strcpy(path,"CHATS" SEP);strcat(path,name);remove(path);save_modal(name);
        CHECK(transcript_full());ui_clear_chat();CHECK(!transcript_full()&&transcript_size()==0);
        ui_begin(ROLE_USER,0);ui_append("After new chat");ui_end();ui_begin(ROLE_AI,0);ui_append("Reply after new");ui_end();CHECK(transcript_messages()==2);
    }
    ui_shutdown();
}
static void encoding_ui_save(void)
{
    unsigned cp;FILE *f;char saved[100];
    const char text[]={ (char)0x84,(char)0x94,(char)0x81,(char)0x8e,(char)0x99,(char)0x9a,(char)0xe1,0 };
    for(cp=437;cp<=850;cp+=413){
        CHECK(ui_init(cp));CHECK(ui_codepage()==cp);ui_busy(0);
        ui_begin(ROLE_USER,"You");ui_append(text);ui_end();
        CHECK(strstr(ui_line(0),text)!=NULL);
        f=fopen("ENCODE.TXT","wb");CHECK(f&&transcript_save(f));CHECK(fclose(f)==0);
        f=fopen("ENCODE.TXT","rb");CHECK(f!=NULL);memset(saved,0,sizeof(saved));
        CHECK(fread(saved,1,sizeof(saved)-1,f)>0);fclose(f);CHECK(strstr(saved,text)!=NULL);
        ui_shutdown();
    }
    remove("ENCODE.TXT");
}
int main(void)
{
    encoding_ui_save();transcript_core();filenames();ui_stress(LANG_EN);ui_stress(LANG_DE);
    puts("AI4DOS TRANSCRIPT SAVE SCROLL STRESS PASS: EN DE, 1440+ messages, multi-DATA wrap, repeated 128-ring eviction/scroll/save/full/new, roles/CRLF/8.3/limits/overwrite/recovery");return 0;
}
