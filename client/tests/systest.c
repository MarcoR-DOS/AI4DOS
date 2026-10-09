/* Exercise the production interactive main with real UI/transcript, scripted
   local transport and input, natively and on DOS/8086. No provider/network calls. */
#define AI4DOS_UI_TEST
#define main client_main
#define ui_input scripted_input
#include "../src/main.c"
#undef main
#undef ui_input
#define ui_status checked_status_impl
#include "../src/ui.c"
#undef ui_status
#include <stdlib.h>
#ifdef __WATCOMC__
#include <dos.h>
#endif
#include "transcr.h"

#define CHECK(x) do { if(!(x)){fprintf(stderr,"FAIL %s:%u: %s\n",scenario,__LINE__,#x);exit(1);} } while(0)
#define GREETING "OK AI4DOS/0.2 UTF-8"
#define CHALLENGE "CHALLENGE 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
#define START GREETING,CHALLENGE,"OK AUTH","SESSION 0123456789ab"
#define RESUME GREETING,CHALLENGE,"OK AUTH","OK RESUME"
#define REPLY "BEGIN ChatGPT","DATA local reply","END"
static const char *scenario;
static const char * const *frames;
static unsigned frame_at,input_at,opens,wire_messages;
static int fail_open,fail_write;
static const int *inputs;
static const TextId *expected;
static unsigned expected_count;
static char export_text[5000],baseline_footer[81];
static const char *expected_text(unsigned index)
{return expected[index]==TXT_COUNT?(strcmp(scenario,"gateway timeout")==0?
    "UPSTREAM response generation failed":"UPSTREAM_UNAVAILABLE provider unavailable"):tr(expected[index]);}
static void check_footer(void)
{
    char expected_footer[81];unsigned directions=ui_scroll_directions(),n=10;
    strcpy(expected_footer,baseline_footer);
    if(directions&UI_SCROLL_UP)expected_footer[n++]=(char)glyph_byte(GLYPH_SCROLL_UP,ui_codepage());
    if(directions&UI_SCROLL_DOWN)expected_footer[n++]=(char)glyph_byte(GLYPH_SCROLL_DOWN,ui_codepage());
    CHECK(strcmp(painted_footer,expected_footer)==0);
#ifdef __WATCOMC__
    {
        unsigned col;unsigned short __far *cells=(unsigned short __far *)MK_FP(0xb000,0);
        for(col=0;col<80;++col)CHECK((cells[24*80+col]&255)==(unsigned char)expected_footer[col]);
    }
#endif
}

void ui_status(UiStatus status)
{
    checked_status_impl(status);
    check_footer();
    CHECK(strcmp(ui_status_label(1),"CONNECTING")==0||strcmp(ui_status_label(1),"ONLINE")==0||
          strcmp(ui_status_label(1),"TX/RX")==0||strcmp(ui_status_label(1),"ERROR")==0);
}

static int visible(const char *text)
{
    unsigned row;
    for(row=0;row<UI_CHAT_ROWS;++row)if(strstr(ui_line(row),text))return 1;
    return 0;
}
static void snapshot(void)
{
    FILE *fp=tmpfile();unsigned n,i,systems=0;char wanted[160];
    check_footer();
    CHECK(fp!=NULL);CHECK(transcript_save(fp));rewind(fp);
    n=(unsigned)fread(export_text,1,sizeof(export_text)-1,fp);export_text[n]=0;fclose(fp);
    for(i=0;i<transcript_messages();++i){
        Role role=transcript_role(i);
        CHECK(role==ROLE_SYSTEM||role==ROLE_USER||role==ROLE_AI);
        if(role==ROLE_SYSTEM)++systems;
    }
    CHECK(systems<=expected_count);
    for(i=0;i<systems;++i){
        char body[160];unsigned len;
        strcpy(body,expected_text(i));len=(unsigned)strlen(body);
        while(len&&(body[len-1]=='\n'||body[len-1]=='\r'))body[--len]=0;
        sprintf(wanted,"System:\r\n%s\r\n\r\n",body);
        CHECK(strstr(export_text,wanted)!=NULL);
    }
    if(systems){sprintf(wanted,"System: %s",expected_text(systems-1));CHECK(visible(wanted));}
    if(ui_get_status()==UI_ONLINE)CHECK(strcmp(ui_status_label(1),"ONLINE")==0);
    else CHECK(ui_get_status()==UI_ERROR&&strcmp(ui_status_label(1),"ERROR")==0);
    if(wire_messages&&strstr(export_text,"local reply"))CHECK(strstr(export_text,"ChatGPT:\r\nlocal reply")!=NULL);
}
int scripted_input(char *text,int (*poll)(void))
{
    int action=inputs[input_at++];(void)poll;snapshot();
    if(action==1)strcpy(text,wire_messages?"after":"hello");
    return action;
}
int net_open(const char *server,unsigned port)
{CHECK(strcmp(server,"127.0.0.1")==0&&port==12345);++opens;return !(fail_open&&opens==(unsigned)fail_open);}
int net_read(char *text,unsigned cap)
{
    const char *frame=frames[frame_at++];
    if(!frame)return 0;
    CHECK(strlen(frame)<cap);strcpy(text,frame);return 1;
}
int net_write(const char *text)
{
    CHECK(strstr(text,"System:")==NULL);
    if(strncmp(text,"MSG ",4)==0){
        CHECK(strcmp(text,wire_messages?"MSG after":"MSG hello")==0);++wire_messages;
        if(fail_write&&wire_messages==1)return 0;
    }else CHECK(strcmp(text,"HELLO test-device")==0||strncmp(text,"AUTH ",5)==0||strcmp(text,"NEW")==0||strcmp(text,"RESUME 0123456789ab")==0||strcmp(text,"QUIT")==0);
    return 1;
}
void net_disconnect(void){}
void net_close(void){}
int mtcp_adapter_pump(void){return 1;}
static void run(const char *name,const char * const *script,const int *actions,
                const TextId *messages,unsigned count,Language lang,int unavailable,int write_failure)
{
    FILE *fp;unsigned i,systems=0;char *args[]={"client","SYSTEM.CFG",NULL};
    scenario=name;language_set(lang);CHECK(ui_init(850));strcpy(baseline_footer,painted_footer);ui_shutdown();frames=script;inputs=actions;expected=messages;expected_count=count;
    frame_at=input_at=opens=wire_messages=0;fail_open=unavailable;fail_write=write_failure;
    fp=fopen("SYSTEM.CFG","w");CHECK(fp!=NULL);
    fprintf(fp,"SERVER=127.0.0.1\nPORT=12345\nDEVICE=test-device\nSECRET=local-test-key\nLANGUAGE=%s\nCODEPAGE=850\n",lang==LANG_DE?"de":"en");fclose(fp);
    CHECK(client_main(2,args)==0);
    for(i=0;i<transcript_messages();++i)if(transcript_role(i)==ROLE_SYSTEM)++systems;
    CHECK(systems==count);remove("SYSTEM.CFG");
}
int main(void)
{
    static const char * const success[]={START,REPLY,"OK BYE"};
    static const char * const bad_auth[]={GREETING,CHALLENGE,"ERROR AUTH_FAILED device authentication failed"};
    static const char * const interrupted[]={START,"BEGIN Claude","DATA partial",NULL,RESUME,REPLY,"OK BYE"};
    static const char * const resumed[]={START,REPLY,RESUME,REPLY,"OK BYE"};
    static const char * const lost_session[]={START,REPLY,GREETING,CHALLENGE,"OK AUTH","ERROR SESSION session unavailable"};
    static const char * const busy_session[]={START,REPLY,GREETING,CHALLENGE,"OK AUTH","ERROR SESSION_BUSY session busy"};
    static const char * const provider_error[]={START,"BEGIN ChatGPT","DATA partial","ERROR UPSTREAM_UNAVAILABLE provider unavailable"};
    static const char * const gateway_timeout[]={START,"BEGIN ChatGPT","DATA partial","ERROR UPSTREAM response generation failed"};
    static const char * const invalid_data[]={START,"BEGIN ChatGPT","DATA partial","DATA bad\\q"};
    static const char * const invalid_frame[]={START,"OK BYE"};
    static const char * const retry[]={START,REPLY,"OK BYE"};
    static const char * const write_drop[]={START,RESUME,REPLY,"OK BYE"};
    static const int normal[]={1,0},stop[]={0},reconnect[]={1,3,1,0},idle[]={1,-1,3,1,0},lost[]={1,-1,3,0},recover[]={3,1,0};
    static const TextId connected[]={TXT_SYSTEM_CONNECTING,TXT_SYSTEM_CONNECTED};
    static const TextId unreachable[]={TXT_SYSTEM_CONNECTING,TXT_SYSTEM_UNREACHABLE,TXT_RECONNECT_HINT};
    static const TextId auth[]={TXT_SYSTEM_CONNECTING,TXT_SYSTEM_AUTH_FAILED,TXT_RECONNECT_HINT};
    static const TextId restored[]={TXT_SYSTEM_CONNECTING,TXT_SYSTEM_CONNECTED,TXT_SYSTEM_LOST,TXT_RECONNECT_HINT,TXT_SYSTEM_CONNECTING,TXT_SYSTEM_RESTORED};
    static const TextId stream_restored[]={TXT_SYSTEM_CONNECTING,TXT_SYSTEM_CONNECTED,TXT_SYSTEM_LOST,TXT_INTERRUPTED,TXT_SYSTEM_CONNECTING,TXT_SYSTEM_RESTORED};
    static const TextId manual[]={TXT_SYSTEM_CONNECTING,TXT_SYSTEM_CONNECTED,TXT_SYSTEM_CONNECTING,TXT_SYSTEM_RESTORED};
    static const TextId session_missing[]={TXT_SYSTEM_CONNECTING,TXT_SYSTEM_CONNECTED,TXT_SYSTEM_LOST,TXT_RECONNECT_HINT,TXT_SYSTEM_CONNECTING,TXT_SESSION_LOST};
    static const TextId new_failed[]={TXT_SYSTEM_CONNECTING,TXT_SYSTEM_CONNECTED,TXT_SYSTEM_LOST,TXT_RECONNECT_HINT,TXT_SYSTEM_CONNECTING,TXT_SYSTEM_UNREACHABLE,TXT_RECONNECT_HINT};
    static const int fresh_fail[]={1,-1,2,0};
    static const TextId recovered[]={TXT_SYSTEM_CONNECTING,TXT_SYSTEM_UNREACHABLE,TXT_RECONNECT_HINT,TXT_SYSTEM_CONNECTING,TXT_SYSTEM_CONNECTED};
    static const TextId session_busy[]={TXT_SYSTEM_CONNECTING,TXT_SYSTEM_CONNECTED,TXT_SYSTEM_LOST,TXT_RECONNECT_HINT,TXT_SYSTEM_CONNECTING,TXT_SESSION_BUSY};
    static const TextId upstream[]={TXT_SYSTEM_CONNECTING,TXT_SYSTEM_CONNECTED,TXT_COUNT,TXT_INTERRUPTED};
    static const TextId parser_error[]={TXT_SYSTEM_CONNECTING,TXT_SYSTEM_CONNECTED,TXT_INVALID_REPLY,TXT_INTERRUPTED};
    static const TextId invalid[]={TXT_SYSTEM_CONNECTING,TXT_SYSTEM_CONNECTED,TXT_UNEXPECTED_FRAME,TXT_RECONNECT_HINT};
    static const int error_stop[]={1,0};
    unsigned lang;
    for(lang=0;lang<LANG_COUNT;++lang){
        run("gateway timeout",gateway_timeout,error_stop,upstream,4,(Language)lang,0,0);
        run("parser error",invalid_data,error_stop,parser_error,4,(Language)lang,0,0);
        run("resume busy",busy_session,lost,session_busy,6,(Language)lang,0,0);
        run("provider timeout/error",provider_error,error_stop,upstream,4,(Language)lang,0,0);
        run("protocol error",invalid_frame,error_stop,invalid,4,(Language)lang,0,0);
        run("start",success,normal,connected,2,(Language)lang,0,0);
        run("unreachable",success,stop,unreachable,3,(Language)lang,1,0);
        run("auth rejected",bad_auth,stop,auth,3,(Language)lang,0,0);
        run("stream loss/resume",interrupted,reconnect,stream_restored,6,(Language)lang,0,0);
        run("idle loss/resume",resumed,idle,restored,6,(Language)lang,0,0);
        run("manual reconnect/resume",resumed,reconnect,manual,4,(Language)lang,0,0);
        run("missing session",lost_session,lost,session_missing,6,(Language)lang,0,0);
        run("first successful retry",retry,recover,recovered,5,(Language)lang,1,0);
        run("write loss/resume",write_drop,reconnect,restored,6,(Language)lang,0,1);
        run("failed offline new preserves history",success,fresh_fail,new_failed,7,(Language)lang,2,0);
    }
    puts("AI4DOS SYSTEM PASS: EN/DE 15 scenarios: start/unreachable/auth/loss/reconnect/resume/timeout/provider/parser/save/roles/wire isolation/static footer/status");
    return 0;
}
