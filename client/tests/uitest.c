#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../src/ui.c"
#include "video.h"
#include "glyphs.h"
#include "editor.h"
#include "config.h"
#include <unistd.h>
static void check_editor(void)
{
    LineEditor e;unsigned i;editor_init(&e);
    for(i=0;i<1000;++i)assert(editor_key(&e,'x',0));
    assert(!editor_key(&e,'y',0)&&e.length==1000&&e.text[1000]==0);
    editor_key(&e,0,0x47);editor_key(&e,0,0x53);assert(e.length==999&&e.cursor==0);
    assert(editor_key(&e,'A',0));assert(e.text[0]=='A'&&e.cursor==1);
    editor_key(&e,8,0);assert(e.length==999&&e.cursor==0);
    editor_key(&e,0,0x4f);assert(e.cursor==e.length);
    editor_key(&e,0,0x53);assert(e.length==999);
    assert(editor_key(&e,0x84,0));
}
static void check_glyph_video(void)
{
    VideoPlan p;unsigned i;unsigned long count;
    assert(glyph_codepage(0,850)==850&&glyph_codepage(437,850)==437);
    assert(glyph_codepage(1,437)==0&&glyph_codepage(0,858)==0);
    for(i=0;i<GLYPH_COUNT;++i)assert(glyph_byte((Glyph)i,437)==glyph_byte((Glyph)i,850));
    assert(glyph_byte(GLYPH_TL,437)==0xda&&glyph_byte(GLYPH_BR,850)==0xd9);
    assert(glyph_byte(GLYPH_DOUBLE_TL,437)==0xc9&&glyph_byte(GLYPH_DOUBLE_BR,850)==0xbc);
    assert(glyph_byte(GLYPH_HLINE,0)=='-'&&glyph_byte(GLYPH_LTEE,0)=='+');
    p=video_plan(7,VIDEO_VGA);assert(p.mode==7&&p.segment==0xb000&&!p.bios_cells);
    p=video_plan(3,VIDEO_LEGACY);assert(p.mode==3&&p.segment==0xb800&&p.bios_cells);
    p=video_plan(0x13,VIDEO_EGA);assert(p.mode==3&&!p.bios_cells);
    assert(video_init());video_put_cell(2,2,'x',7);count=video_write_count();
    video_put_cell(2,2,'x',7);video_put_cell(25,80,'x',7);assert(video_write_count()==count);
    video_shutdown();
}
static void check_wrap_roles(void)
{
    char text[400],saved[18][77];Role roles[18];unsigned i;
    strcpy(text,"prefix ");memset(text+7,'x',90);strcpy(text+97," a word crossing a frame boundary\nfinal line");
    assert(ui_init(437));ui_begin(ROLE_AI,"You");ui_append(text);
    assert(ui_line_role(0)==ROLE_AI&&strncmp(ui_line(0),"You: prefix",11)==0);
    for(i=0;i<18;++i){strcpy(saved[i],ui_line(i));roles[i]=ui_line_role(i);assert(strlen(ui_line(i))<=76);}ui_shutdown();
    assert(ui_init(850));ui_begin(ROLE_AI,"You");
    for(i=0;text[i];++i){char part[2];part[0]=text[i];part[1]=0;ui_append(part);}
    for(i=0;i<18;++i){assert(strcmp(saved[i],ui_line(i))==0);assert(roles[i]==ui_line_role(i));}
    for(i=0;i<30;++i)ui_append("\nrecent");assert(strcmp(ui_line(17),"recent")==0);
    assert(ui_line_role(17)==ROLE_AI);ui_shutdown();
}
static void check_modals_and_scroll(void)
{
    char saved[18][77];unsigned i;unsigned long writes;
    remove("CHATS/TE.TXT");
    assert(ui_init(850));ui_busy(0);editor_key(&editor,'d',0);editor_key(&editor,'r',0);
    ui_begin(ROLE_AI,0);ui_append("alpha beta");ui_end();
    assert(strcmp(ui_line(0),"AI: alpha beta")==0); /* inline, no label-only line */
    for(i=0;i<18;++i)strcpy(saved[i],ui_line(i));
    assert(controls_handle(0x3e00,0)==CONTROL_HANDLED&&controls_active());
    assert(strncmp(painted[0],"Help",4)==0&&strstr(painted[2],"Send message"));
    assert(strstr(painted[3],"F1 or /info")&&strstr(painted[3],"Info"));
    assert(strstr(painted[4],"F2 or /new")&&strstr(painted[5],"F4 or /help"));
    assert(strstr(painted[6],"Save chat")&&strstr(painted[7],"F10 or /quit"));
    assert(strstr(painted[9],"PgUp/PgDn")&&strstr(painted[10],"Up/Down arrows"));
    assert(strstr(painted[12],"Back to chat"));
    assert(controls_handle(13,0)==CONTROL_HANDLED); /* modal does not submit input */
    assert(controls_handle(27,0)==CONTROL_HANDLED&&!controls_active());
    for(i=0;i<18;++i)assert(strcmp(saved[i],ui_line(i))==0);
    assert(strcmp(editor.text,"dr")==0&&strncmp(painted[0],"AI: alpha beta",14)==0);
    ui_set_session("012345abcdef");controls_handle(0x3b00,0);assert(strstr(painted[3],"012345abcdef"));controls_handle(27,0);
    controls_handle(0x3f00,0);controls_handle('T',0);controls_handle('E',0);controls_handle(13,0);
    assert(!controls_active()&&strstr(ui_line(2),"System: Saved: CHATS\\TE"));controls_handle(27,0);
    assert(strcmp(editor.text,"dr")==0);
    controls_handle(0x4400,0);assert(controls_active());controls_handle(27,0);assert(!controls_active());
    controls_handle(0x4400,0);assert(controls_handle(0x4400,0)==CONTROL_EXIT);controls_handle(27,0);
    ui_busy(1);assert(controls_handle(0x3e00,1)==CONTROL_HANDLED&&!controls_active());ui_busy(0);
    ui_clear_chat();ui_begin(ROLE_AI,0);for(i=0;i<150;++i){char text[30];sprintf(text,"line %03u\n",i);ui_append(text);}ui_end();
    assert(count==128&&strstr(ui_line(17),"149"));assert(ui_scroll_directions()==UI_SCROLL_UP);
    ui_scroll_page(-1);assert(ui_scroll_directions()==(UI_SCROLL_UP|UI_SCROLL_DOWN));
    ui_scroll_lines(-300);assert(ui_scroll_directions()==UI_SCROLL_DOWN);
    assert(!strstr(ui_line(0),"000"));ui_scroll_lines(300);assert(ui_scroll_directions()==UI_SCROLL_UP);
    writes=video_write_count();paint_chat();assert(video_write_count()==writes);ui_shutdown();
}
static void check_localization(void)
{
    Config cfg;FILE *f;unsigned lang,page,i;const char *values[]={"","en","de","xx","DE"};
    assert(language_get()==LANG_EN);
    for(i=0;i<5;++i){
        f=fopen("LANGTEST.CFG","w");assert(f);
        fputs("SERVER=localhost\nPORT=1983\nDEVICE=test\nSECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n",f);
        if(values[i][0])fprintf(f,"LANGUAGE=%s\n",values[i]);fclose(f);
        assert(config_load("LANGTEST.CFG",&cfg));assert(cfg.language==(i==2?LANG_DE:LANG_EN));
    }
    remove("LANGTEST.CFG");
    for(lang=0;lang<LANG_COUNT;++lang)for(page=0;page<3;++page){
        language_set((Language)lang);assert(ui_init(page==0?437:page==1?850:1));
        for(i=0;i<TXT_COUNT;++i)assert(tr((TextId)i)[0]);
        assert(strstr(AI4DOS_HEADER,AI4DOS_VERSION));
        assert(strlen(tr(TXT_NEW_CHAT))+strlen(tr(TXT_HELP_KEY))+strlen(tr(TXT_SAVE))+strlen(tr(TXT_EXIT))+10<=76);
        assert(ui_get_status()==UI_CONNECTING&&strcmp(ui_status_label(1),"CONNECTING")==0);
        ui_status(UI_ONLINE);assert(strcmp(ui_status_label(1),"ONLINE")==0);ui_info();
        assert(strstr(painted[0],"Version " AI4DOS_VERSION AI4DOS_VERSION_SUFFIX));assert(strstr(painted[1],"0.3"));
        assert(strstr(painted[3],lang?"Sitzung: -":"Session: -"));
        assert(strstr(painted[4],"Status: Online"));assert(strstr(painted[5],lang?"Verbunden":"Connected"));
        assert(strlen("License: GPL-3.0-only")<=76&&strncmp(painted[14],"License: GPL-3.0-only",21)==0);
        assert(strlen("mTCP: GPL-3.0-or-later")<=76&&strncmp(painted[15],"mTCP: GPL-3.0-or-later",22)==0);
        assert(strlen("Watcom runtime: OWPL 1.0 - source available")<=76&&strncmp(painted[16],"Watcom runtime: OWPL 1.0 - source available",43)==0);
        assert(strlen("Source: github.com/open-watcom/open-watcom-v2")<=76&&strncmp(painted[17],"Source: github.com/open-watcom/open-watcom-v2",45)==0);
        for(i=0;i<76;++i){
            if(i>=21)assert(painted[14][i]==' ');
            if(i>=22)assert(painted[15][i]==' ');
            if(i>=43)assert(painted[16][i]==' ');
            if(i>=45)assert(painted[17][i]==' ');
        }
        for(i=6;i<14;++i)assert(strspn(painted[i]," ")==76);
        for(i=0;i<18;++i)assert(!strstr(painted[i],"OK AI4DOS")&&!strstr(painted[i],"UTF-8"));
        ui_overlay_end();ui_status(UI_TX_RX);assert(strcmp(ui_status_label(1),"TX/RX")==0);
        ui_status(UI_ONLINE);assert(strcmp(ui_status_label(1),"ONLINE")==0);
        ui_status(UI_ERROR);ui_info();assert(strstr(painted[4],lang?"Fehler":"Error"));
        assert(strstr(painted[5],lang?"Getrennt":"Disconnected"));ui_overlay_end();
        ui_help();assert(strncmp(painted[0],lang?"Hilfe":"Help",lang?5:4)==0);
        assert(strstr(painted_footer,lang?(page<2?"ESC Zur\201ck":"ESC Zurueck"):"ESC Back"));
        ui_status(UI_TX_RX);ui_overlay_end();assert(ui_get_status()==UI_TX_RX);
        ui_clear_chat();ui_begin(ROLE_USER,0);ui_append("hello");ui_end();
        ui_begin(ROLE_AI,0);ui_append("reply\n\n");ui_end();ui_begin(ROLE_USER,0);ui_append("again");ui_end();
        assert(strstr(ui_line(0),"hello")&&ui_line(1)[0]==0);
        assert(strstr(ui_line(2),"reply")&&ui_line(3)[0]==0&&strstr(ui_line(4),"again"));
        ui_clear_chat();ui_begin(ROLE_AI,0);ui_append("first\n\nlast\n");ui_end();
        assert(strstr(ui_line(0),"first")&&ui_line(1)[0]==0&&strcmp(ui_line(2),"last")==0);
        ui_shutdown();
    }
    language_set((Language)99);assert(language_get()==LANG_EN);
}
static void check_warning_persistence(void)
{
    char text[513];unsigned i;
    language_set(LANG_EN);assert(ui_init(850));ui_busy(1);ui_begin(ROLE_AI,0);
    memset(text,'x',512);text[512]=0;
    for(i=0;i<100;++i)ui_append(text);
    assert(!strstr(painted_footer,"Transcript almost full"));
    ui_end();assert(strstr(ui_line(16),"System: Transcript almost full")||strstr(ui_line(17),"System: Transcript almost full"));
    assert(controls_handle(0,1)==CONTROL_NONE&&!strstr(painted_footer,"Transcript almost full"));
    ui_end();ui_shutdown();
}
static void check_static_footer(void)
{
    static const unsigned codepages[]={437,850,1};
    static const unsigned directions[]={0,UI_SCROLL_UP,UI_SCROLL_DOWN,UI_SCROLL_UP|UI_SCROLL_DOWN};
    char baseline[81],expected[81];unsigned lang,codepage,state,status,i,n;
    for(lang=0;lang<LANG_COUNT;++lang)for(codepage=0;codepage<3;++codepage){
        language_set((Language)lang);assert(ui_init(codepages[codepage]));strcpy(baseline,painted_footer);
        assert(strncmp(baseline+2,"PgUp/Dn   ",10)==0);
        for(state=0;state<4;++state){
            if(state==1){
                ui_clear_chat();ui_begin(ROLE_AI,0);
                for(i=0;i<150;++i)ui_append("scroll line\n");ui_end();
            }else if(state==2)ui_scroll_lines(-300);
            else if(state==3)ui_scroll_lines(1);
            assert(ui_scroll_directions()==directions[state]);
            strcpy(expected,baseline);n=10;
            if(directions[state]&UI_SCROLL_UP)expected[n++]=(char)glyph_byte(GLYPH_SCROLL_UP,ui_codepage());
            if(directions[state]&UI_SCROLL_DOWN)expected[n++]=(char)glyph_byte(GLYPH_SCROLL_DOWN,ui_codepage());
            assert(memcmp(expected,painted_footer,sizeof(expected))==0);
            for(status=0;status<=UI_ERROR;++status){
                ui_status((UiStatus)status);ui_busy(status%2);
                ui_notice(tr(TXT_RECONNECT_HINT));
                assert(memcmp(expected,painted_footer,sizeof(expected))==0);
            }
            ui_status((UiStatus)99);assert(strcmp(ui_status_label(1),"ERROR")==0);
            assert(memcmp(expected,painted_footer,sizeof(expected))==0);
        }
        ui_scroll_lines(300);expected[10]=(char)glyph_byte(GLYPH_SCROLL_UP,ui_codepage());expected[11]=' ';
        assert(ui_scroll_directions()==UI_SCROLL_UP&&memcmp(expected,painted_footer,sizeof(expected))==0);
        ui_clear_chat();assert(ui_scroll_directions()==0&&memcmp(baseline,painted_footer,sizeof(baseline))==0);
        ui_shutdown();
    }
}
static void check_provider_labels(void)
{
    static const char *labels[]={"ChatGPT","Claude","Gemini","Mistral","NVIDIA","OpenRouter",0};
    unsigned lang,i;FILE *file;char text[128],expected[100];const char *label;
    for(lang=0;lang<LANG_COUNT;++lang){
        language_set((Language)lang);assert(ui_init(437));
        for(i=0;i<7;++i){
            label=labels[i]?labels[i]:tr(TXT_AI);ui_clear_chat();
            ui_begin(ROLE_AI,labels[i]);ui_append("hello");ui_end();
            sprintf(expected,"%s: hello",label);assert(strcmp(ui_line(0),expected)==0);
            assert(ui_line_role(0)==ROLE_AI&&transcript_role(0)==ROLE_AI);
            file=tmpfile();assert(file&&transcript_save(file));rewind(file);
            text[fread(text,1,sizeof(text)-1,file)]=0;fclose(file);
            sprintf(expected,"%s:\r\nhello\r\n\r\n",label);assert(strcmp(text,expected)==0);
        }
        ui_help();assert(strncmp(painted[16],"https://github.com/MarcoR-DOS/AI4DOS",33)==0);
        ui_shutdown();
    }
}
int main(void)
{assert(chdir("client/build")==0);check_localization();check_editor();check_glyph_video();check_wrap_roles();check_modals_and_scroll();check_warning_persistence();check_provider_labels();check_static_footer();puts("AI4DOS UI CORE PASS (language/config/status/info/spacing/modals/scroll)");return 0;}
