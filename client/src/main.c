#include <stdio.h>
#include <errno.h>
#include <string.h>
#include "config.h"
#include "protocol.h"
#include "sha256.h"
#include "net.h"
#include "ramdiag.h"
#include "charset.h"
#if defined(__WATCOMC__) || defined(AI4DOS_UI_TEST)
#include "ui.h"
static int using_ui,local_failure_presented;
#endif
static char failure[DATA_CAP];
static void report_error(const char *text)
{
#if defined(__WATCOMC__) || defined(AI4DOS_UI_TEST)
    if(using_ui){ui_status(UI_ERROR);strncpy(failure,text,sizeof(failure)-1);failure[sizeof(failure)-1]=0;return;}
#endif
    fputs(text,stderr);
}
static Config cfg;
static Protocol protocol;
static Event event;
static char line[LINE_CAP],message[1002],command[LINE_CAP];
static char session_id[13];
static unsigned chat_codepage;
static TextId reconnect_notice=TXT_RECONNECT_HINT;
static int local_network_error;
static int transport_failed,connection_attempt,auth_rejected,ever_connected;
/* Local presentation only: never serialize transcript records onto the wire. */
static void system_message(TextId text)
{
#if defined(__WATCOMC__) || defined(AI4DOS_UI_TEST)
    if(using_ui){
        /* Important connection events are visible even after scrolling up. */
        ui_scroll_lines(32767);
        ui_begin(ROLE_SYSTEM,"System");ui_append(tr(text));ui_end();return;
    }
#endif
    fputs("System: ",stdout);fputs(tr(text),stdout);putchar('\n');fflush(stdout);
}
static int write_line(const char *text)
{
    int ok=net_write(text);
    if(!ok)transport_failed=1;
    return ok;
}
static int read_event(EventType expected)
{
    EventType type;
    if(!net_read(line,sizeof(line))){transport_failed=1;report_error(tr(TXT_READ_FAILED));return 0;}
    type=protocol_parse(&protocol,line,&event);
    if(type==EV_ERROR){
        if(strncmp(event.text,"AUTH_FAILED ",12)==0||strcmp(event.text,"AUTH_FAILED")==0)auth_rejected=1;
        if(strncmp(event.text,"SESSION ",8)==0){
            reconnect_notice=TXT_SESSION_LOST;report_error(tr(reconnect_notice));
        }else if(strncmp(event.text,"SESSION_BUSY ",13)==0){
            reconnect_notice=TXT_SESSION_BUSY;report_error(tr(reconnect_notice));
        }else report_error(event.text);
        return 0;
    }
    if(type!=expected){report_error(tr(TXT_UNEXPECTED_FRAME));return 0;}return 1;
}
/* One deliberate attempt: reset transport/parser, authenticate, then NEW or RESUME.
   The credential stays in the loaded config only until shutdown for fresh HMACs. */
static int connect_session(int fresh)
{
    unsigned char digest[32];char hex[65];int ok;
#if defined(__WATCOMC__) || defined(AI4DOS_UI_TEST)
    local_failure_presented=0;
#endif
    connection_attempt=1;local_network_error=0;transport_failed=auth_rejected=0;failure[0]=0;
#if defined(__WATCOMC__) || defined(AI4DOS_UI_TEST)
    if(using_ui)ui_clear_notice();
#endif
    system_message(TXT_SYSTEM_CONNECTING);
    net_disconnect();protocol_init(&protocol);reconnect_notice=TXT_RECONNECT_HINT;
    if(!net_open(cfg.server,cfg.port)){local_network_error=net_start_error();transport_failed=1;report_error(tr(TXT_CONNECT_FAILED));return 0;}
    if(!read_event(EV_GREETING))return 0;
    sprintf(command,"HELLO %s",cfg.device);
    if(!write_line(command)||!read_event(EV_CHALLENGE))return 0;
    hmac_sha256((const unsigned char *)cfg.secret,strlen(cfg.secret),
                (const unsigned char *)event.text,strlen(event.text),digest);
    digest_to_hex(digest,hex);memset(digest,0,sizeof(digest));
    sprintf(command,"AUTH %s",hex);memset(hex,0,sizeof(hex));
    ok=write_line(command);memset(command,0,sizeof(command));
    if(!ok||!read_event(EV_AUTH))return 0;
    if(fresh||!session_id[0]){
        if(!protocol_expect_session(&protocol)||!write_line("NEW")||!read_event(EV_SESSION))return 0;
        strcpy(session_id,protocol.session);
    }else{
        if(!protocol_expect_resume(&protocol,session_id))return 0;
        sprintf(command,"RESUME %s",session_id);
        if(!write_line(command)||!read_event(EV_RESUME))return 0;
    }
    connection_attempt=0;return 1;
}
static void output(Role role,const char *text)
{
    if(role!=ROLE_AI)return;
    /* The parsed Event owns the payload; line is free until the next net_read. */
    utf8_to_dos(text,line,sizeof(line),chat_codepage);
#if defined(__WATCOMC__) || defined(AI4DOS_UI_TEST)
    if(using_ui){ui_append(line);return;}
#endif
    fputs(line,stdout);
    fflush(stdout); /* Each DATA frame is displayed before waiting for END. */
}
int main(int argc,char **argv)
{
    unsigned i,n;int result=1;
#if defined(__WATCOMC__) || defined(AI4DOS_UI_TEST)
    int input_result,online=0,reply_active=0,exiting=0;
#endif
    ram_mark(0);
    transport_failed=connection_attempt=auth_rejected=ever_connected=0;
    failure[0]=0;protocol_init(&protocol);
    if(!config_load(argc>1?argv[1]:"AI4DOS.CFG",&cfg)){
        sprintf(failure,"ERROR: %.128s %s\n",argc>1?argv[1]:"AI4DOS.CFG",
                errno==ENOENT?"not found.":errno==EINVAL?"is invalid.":"could not be read.");
#if !defined(__WATCOMC__) && !defined(AI4DOS_UI_TEST)
        fputs(failure,stderr);
#endif
        goto done;
    }
    language_set(cfg.language);language_codepage(cfg.codepage);chat_codepage=cfg.codepage;
    ram_mark(1);
#if defined(__WATCOMC__) || defined(AI4DOS_UI_TEST)
    if(!ui_init(cfg.codepage)){report_error(tr(TXT_VIDEO_FAILED));goto done;}
    using_ui=1;chat_codepage=ui_codepage();
#endif
    if(!connect_session(1))goto done;
    system_message(TXT_SYSTEM_CONNECTED);ever_connected=1;
    ram_mark(4);
#if defined(__WATCOMC__) || defined(AI4DOS_UI_TEST)
    online=1;ui_set_session(session_id);ui_status(UI_ONLINE);
#endif
#if defined(__WATCOMC__) || defined(AI4DOS_UI_TEST)
next_message:
#endif
    if(argc>2){if(strlen(argv[2])>1000)goto done;strcpy(message,argv[2]);}
    else{
#if defined(__WATCOMC__) || defined(AI4DOS_UI_TEST)
        input_result=ui_input(message,online?mtcp_adapter_pump:0);
        if(input_result==0)goto close_session;
        if(input_result==2||input_result==3){
            ui_busy(1);ui_status(UI_CONNECTING);
            if(input_result==2&&online){
                if(!protocol_expect_session(&protocol)||!write_line("NEW")||!read_event(EV_SESSION))goto done;
                strcpy(session_id,protocol.session);ui_clear_chat();
            }else{
                if(!connect_session(input_result==2))goto done;
                if(input_result==2)ui_clear_chat();
                system_message(input_result==3&&ever_connected?TXT_SYSTEM_RESTORED:TXT_SYSTEM_CONNECTED);
                ever_connected=1;
            }
            online=1;failure[0]=0;ui_set_session(session_id);ui_status(UI_ONLINE);
            ui_clear_notice();goto next_message;
        }
        if(input_result<0){transport_failed=1;report_error(tr(TXT_INPUT_DISCONNECTED));goto done;}
#else
        fputs(tr(TXT_USER),stdout);fputs(": ",stdout);fflush(stdout);if(!fgets(message,sizeof(message),stdin))goto done;
#endif
    }
    n=(unsigned)strlen(message);while(n&&(message[n-1]=='\r'||message[n-1]=='\n'))message[--n]=0;
    if(!n||n>1000){report_error(tr(TXT_MESSAGE_LENGTH));goto done;}
    for(i=0;i<n;++i)if((unsigned char)message[i]<32||(unsigned char)message[i]==127){report_error(tr(TXT_ASCII_ONLY));goto done;}
    if(dos_to_utf8(message,command+4,1001,chat_codepage)<1){report_error(tr(TXT_MESSAGE_LENGTH));goto done;}
    memcpy(command,"MSG ",4);
#if defined(__WATCOMC__) || defined(AI4DOS_UI_TEST)
    ui_busy(1);ui_begin(ROLE_USER,0);ui_append(message);ui_end();
    ui_status(UI_TX_RX);
#endif
    if(!protocol_expect_reply(&protocol))goto done;
    if(!write_line(command)||!read_event(EV_BEGIN))goto done;
#if defined(__WATCOMC__) || defined(AI4DOS_UI_TEST)
    ui_begin(ROLE_AI,event.text[0]?event.text:tr(TXT_AI));reply_active=1;
#else
    fputs(event.text[0]?event.text:tr(TXT_AI),stdout);fputs(": ",stdout);fflush(stdout);
#endif
    for(;;){
        if(!net_read(line,sizeof(line))){transport_failed=1;report_error(tr(TXT_READ_FAILED));goto done;}
        switch(protocol_parse(&protocol,line,&event)){
        case EV_DATA:output(event.role,event.text);break;
        case EV_END:goto reply_done;
        case EV_ERROR:report_error(event.text);goto done;
        default:report_error(tr(TXT_INVALID_REPLY));goto done;
        }
    }
reply_done:
    ram_mark(5);
#if defined(__WATCOMC__) || defined(AI4DOS_UI_TEST)
    ui_end();reply_active=0;ui_status(UI_ONLINE);
    if(argc<3)goto next_message;
close_session:
    exiting=1;ui_busy(1);
    if(!online){result=0;goto done;}
#else
    putchar('\n');fflush(stdout);
#endif
    if(!protocol_expect_close(&protocol)||!write_line("QUIT")||!read_event(EV_BYE))goto done;
    result=0;
done:
#if defined(__WATCOMC__) || defined(AI4DOS_UI_TEST)
    if(reply_active){ui_end();reply_active=0;reconnect_notice=TXT_INTERRUPTED;}
    if(result&&!exiting){
#else
    if(result){
#endif
        if(auth_rejected)system_message(TXT_SYSTEM_AUTH_FAILED);
        else if(local_network_error==-3||local_network_error==-4||local_network_error==-7||
                local_network_error==NET_START_NO_IP||local_network_error==NET_START_INVALID_SERVER||local_network_error==NET_START_NO_GATEWAY){
            if(local_network_error==NET_START_NO_IP){
                system_message(TXT_SYSTEM_NOT_CONFIGURED);
                system_message(TXT_SYSTEM_NO_IP);
                system_message(TXT_SYSTEM_IP_HINT);
            }else if(local_network_error==NET_START_INVALID_SERVER)system_message(TXT_SYSTEM_INVALID_SERVER);
            else if(local_network_error==NET_START_NO_GATEWAY)system_message(TXT_SYSTEM_NO_GATEWAY);
            else{
                system_message(TXT_SYSTEM_NETWORK);
                system_message(local_network_error==-4?TXT_SYSTEM_PACKET:local_network_error==-3?TXT_SYSTEM_NET_CONFIG:TXT_SYSTEM_NET_INIT);
            }
#if defined(__WATCOMC__) || defined(AI4DOS_UI_TEST)
            local_failure_presented=using_ui;
#endif
            local_network_error=0;
        }
        else if(transport_failed)system_message(connection_attempt?TXT_SYSTEM_UNREACHABLE:TXT_SYSTEM_LOST);
#if defined(__WATCOMC__) || defined(AI4DOS_UI_TEST)
        else if(using_ui&&failure[0])ui_notice(failure);
#endif
        auth_rejected=transport_failed=0;
    }
#if defined(__WATCOMC__) || defined(AI4DOS_UI_TEST)
    if(result&&using_ui&&argc<3&&!exiting){
        net_disconnect();online=0;ui_busy(0);ui_status(UI_ERROR);
        ui_notice(tr(reconnect_notice));goto next_message;
    }
#endif
    ram_mark(6);
    if(result){
#if defined(__WATCOMC__) || defined(AI4DOS_UI_TEST)
        if(using_ui)ui_status(UI_ERROR);
#endif
    }
    net_close();
    memset(&cfg,0,sizeof(cfg));memset(command,0,sizeof(command));memset(session_id,0,sizeof(session_id));
    ram_mark(7);
#if defined(__WATCOMC__) || defined(AI4DOS_UI_TEST)
    if(using_ui){if(result&&argc<3)ui_error_wait();ui_shutdown();using_ui=0;}
    if(result&&!failure[0]&&!local_failure_presented)strcpy(failure,tr(TXT_FAILED));
    if(result&&failure[0]&&!local_failure_presented){fputs(failure,stderr);if(failure[strlen(failure)-1]!='\n')fputc('\n',stderr);}
    if(!result&&argc>2)puts(tr(TXT_SCRIPT_DONE));
#endif
    ram_report();
    return result;
}
