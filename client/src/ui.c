/* Selectively migrated Georgi UI geometry, viewport, wrap, row-cache and modal
   drawing. Hardware, role identity and glyph selection remain AI4DOS APIs. */
#include <stdio.h>
#include <string.h>
#include "ui.h"
#include "video.h"
#include "glyphs.h"
#include "editor.h"
#include "controls.h"
#include "protocol.h"
#include "l10n.h"
#include "version.h"
#include "transcr.h"
#ifdef __WATCOMC__
#include <bios.h>
#endif
#define SCROLL_LINES 128
#define INPUT_LEFT 4
#define INPUT_WIDTH 74
static char lines[SCROLL_LINES][UI_CHAT_WIDTH+1];
static unsigned char kinds[SCROLL_LINES];
static char painted[UI_CHAT_ROWS][UI_CHAT_WIDTH+1],painted_footer[81];
static char session_text[13],notice_text[77],pending_notice[77];
static UiStatus current_status;
static unsigned head,count,view_top,cp,overlay;
static Role current_role;
static int active,busy,skip_spaces,new_requested,message_active,follow_tail,record_active;
static LineEditor editor;
static unsigned physical(unsigned logical){return(head+logical)%SCROLL_LINES;}
const char *ui_label(Role role)
{switch(role){case ROLE_USER:return tr(TXT_USER);case ROLE_AI:return tr(TXT_AI);case ROLE_SYSTEM:return tr(TXT_SYSTEM);}return tr(TXT_SYSTEM);}
static unsigned content_lines(void)
{unsigned n=count;while(n&&lines[physical(n-1)][0]==0)--n;return n;}
static unsigned tail_top(void)
{unsigned n=content_lines();return n>UI_CHAT_ROWS?n-UI_CHAT_ROWS:0;}
const char *ui_line(unsigned row)
{unsigned n=view_top+row;return row<UI_CHAT_ROWS&&n<count?lines[physical(n)]:"";}
Role ui_line_role(unsigned row)
{unsigned n=view_top+row;return row<UI_CHAT_ROWS&&n<count?(Role)kinds[physical(n)]:ROLE_SYSTEM;}
unsigned ui_scroll_directions(void)
{return (view_top?UI_SCROLL_UP:0)|(view_top<tail_top()?UI_SCROLL_DOWN:0);}
static void row_text(unsigned row,unsigned col,const char *text,unsigned width)
{unsigned i,len=(unsigned)strlen(text);for(i=0;i<width;++i)video_put_cell(row,col+i,(unsigned char)(i<len?text[i]:' '),7);}
static void paint_footer(const char *text)
{unsigned c;for(c=0;c<80;++c)if(text[c]!=painted_footer[c]){video_put_cell(24,c,(unsigned char)text[c],7);painted_footer[c]=text[c];}}
static void footer_message(const char *text)
{char row[81];unsigned n=(unsigned)strlen(text);if(n>76)n=76;memset(row,' ',80);row[80]=0;memcpy(row+2,text,n);paint_footer(row);}
static void footer(void)
{
    const char *labels[5];
    unsigned widths[5],total=0,free,gap,extra,pos=2,n,i,directions;char row[81];
    labels[0]="PgUp/Dn   ";labels[1]=tr(TXT_NEW_CHAT);labels[2]=tr(TXT_HELP_KEY);labels[3]=tr(TXT_SAVE);labels[4]=tr(TXT_EXIT);
    if(overlay)return;
    memset(row,' ',80);row[80]=0;
    for(i=0;i<5;++i){widths[i]=(unsigned)strlen(labels[i]);total+=widths[i];}
    free=76-total;gap=free/4;extra=free%4;directions=ui_scroll_directions();
    for(i=0;i<5;++i){
        if(i==0){memcpy(row+pos,"PgUp/Dn",7);n=pos+8;
            if(directions&UI_SCROLL_UP)row[n++]=(char)glyph_byte(GLYPH_SCROLL_UP,cp);
            if(directions&UI_SCROLL_DOWN)row[n++]=(char)glyph_byte(GLYPH_SCROLL_DOWN,cp);
        }else memcpy(row+pos,labels[i],widths[i]);
        pos+=widths[i];if(i<4)pos+=gap+((i<(extra+1)/2||i>=4-extra/2)?1:0);
    }
    paint_footer(row);
}
static void paint_input(void)
{
    unsigned start=0,pos=editor.cursor;
    if(overlay)return;video_hide_cursor();
    if(pos>=INPUT_WIDTH)start=pos-INPUT_WIDTH+1;
    row_text(22,2,">",2);row_text(22,INPUT_LEFT,editor.text+start,INPUT_WIDTH);
    if(!busy)video_set_cursor(22,INPUT_LEFT+pos-start,1);
}
static void paint_chat(void)
{
    unsigned i,n;char row[77];if(overlay)return;video_hide_cursor();
    for(i=0;i<18;++i){memset(row,' ',76);row[76]=0;n=(unsigned)strlen(ui_line(i));memcpy(row,ui_line(i),n);
        if(strcmp(row,painted[i])!=0){row_text(i+3,2,row,76);memcpy(painted[i],row,77);}}
    footer();paint_input();
}
static unsigned new_line(void)
{
    unsigned idx;if(count<SCROLL_LINES)idx=physical(count++);
    else{head=(head+1)%SCROLL_LINES;idx=physical(count-1);if(!follow_tail&&view_top)--view_top;}
    lines[idx][0]=0;kinds[idx]=(unsigned char)current_role;if(follow_tail)view_top=tail_top();return idx;
}
static unsigned wrap_full_line(unsigned idx,unsigned len)
{
    unsigned split=len,new_idx,src;char word[77];
    while(split&&lines[idx][split-1]!=' ')--split;
    if(!split)return new_line();src=split;
    while(split>1&&lines[idx][split-2]==' ')--split;
    memcpy(word,lines[idx]+src,len-src);word[len-src]=0;lines[idx][split-1]=0;
    new_idx=new_line();strcpy(lines[new_idx],word);return new_idx;
}
static void horizontal(unsigned row,Glyph left,Glyph right)
{unsigned c;video_put_cell(row,0,glyph_byte(left,cp),7);for(c=1;c<79;++c)video_put_cell(row,c,glyph_byte(GLYPH_DOUBLE_HLINE,cp),7);video_put_cell(row,79,glyph_byte(right,cp),7);}
static void separator(unsigned row)
{unsigned c;for(c=2;c<=77;++c)video_put_cell(row,c,glyph_byte(GLYPH_HLINE,cp),7);}
UiStatus ui_get_status(void){return current_status;}
const char *ui_status_label(int header)
{
    static const char * const headers[]={"CONNECTING","ONLINE","TX/RX","ERROR"};
    static const TextId ids[]={TXT_CONNECTING,TXT_ONLINE,TXT_TX_RX,TXT_ERROR};
    return header?headers[current_status]:tr(ids[current_status]);
}
void ui_status(UiStatus status)
{
    const char *text;unsigned n;
    current_status=(unsigned)status<=UI_ERROR?status:UI_ERROR;
    if(!active||overlay)return;text=ui_status_label(1);n=(unsigned)strlen(text);
    video_hide_cursor();row_text(1,64,"",14);row_text(1,78-n,text,n);paint_input();
}
void ui_set_session(const char *session)
{strncpy(session_text,session,12);session_text[12]=0;}
int ui_init(unsigned requested)
{
    unsigned row;head=count=view_top=0;busy=1;overlay=0;new_requested=skip_spaces=0;current_role=ROLE_SYSTEM;
    memset(lines,0,sizeof(lines));memset(painted,0,sizeof(painted));memset(painted_footer,0,sizeof(painted_footer));
    session_text[0]=notice_text[0]=pending_notice[0]=0;record_active=0;transcript_reset();message_active=0;follow_tail=1;current_status=UI_CONNECTING;editor_init(&editor);controls_init();cp=glyph_codepage(requested,glyph_detect());language_codepage(cp);
    if(!video_init())return 0;active=1;
    horizontal(0,GLYPH_DOUBLE_TL,GLYPH_DOUBLE_TR);horizontal(23,GLYPH_DOUBLE_BL,GLYPH_DOUBLE_BR);
    for(row=1;row<23;++row){video_put_cell(row,0,glyph_byte(GLYPH_DOUBLE_VLINE,cp),7);video_put_cell(row,79,glyph_byte(GLYPH_DOUBLE_VLINE,cp),7);}
    separator(2);separator(21);row_text(1,2,AI4DOS_HEADER,sizeof(AI4DOS_HEADER)-1);paint_chat();ui_status(UI_CONNECTING);return 1;
}
unsigned ui_codepage(void){return cp;}
void ui_shutdown(void){if(active)video_shutdown();active=0;}
void ui_busy(int value){busy=value;if(active){video_hide_cursor();footer();paint_input();}}
void ui_clear_chat(void)
{head=count=view_top=0;skip_spaces=message_active=0;follow_tail=1;notice_text[0]=pending_notice[0]=0;record_active=0;transcript_reset();current_role=ROLE_SYSTEM;editor_init(&editor);paint_chat();}
void ui_begin(Role role,const char *label)
{
    unsigned idx;if(!label)label=ui_label(role);
    record_active=transcript_begin(role,label);
    if(!record_active&&role!=ROLE_SYSTEM){message_active=0;ui_notice(tr(TXT_TRANSCRIPT_FULL));return;}
    message_active=1;current_role=role;skip_spaces=0;
    if(role==ROLE_USER){follow_tail=1;view_top=tail_top();}
    idx=new_line();strncpy(lines[idx],label,74);lines[idx][74]=0;strcat(lines[idx],": ");
    if(follow_tail)view_top=tail_top();paint_chat();
}
void ui_append(const char *text)
{
    unsigned idx,len,accepted;char ch;if(!message_active)return;
    accepted=record_active?transcript_append(text):(unsigned)strlen(text);if(!count)new_line();idx=physical(count-1);
    while(accepted--&&(ch=*text++)!=0){
        if(ch=='\r')continue;if(ch=='\n'){idx=new_line();skip_spaces=0;continue;}if(ch=='\t')ch=' ';
        if((unsigned char)ch<32||ch==127)continue;if(skip_spaces&&ch==' ')continue;skip_spaces=0;
        len=(unsigned)strlen(lines[idx]);
        if(len>=76){if(ch==' '){while(len&&lines[idx][len-1]==' ')lines[idx][--len]=0;idx=new_line();skip_spaces=1;continue;}
            idx=wrap_full_line(idx,len);len=(unsigned)strlen(lines[idx]);}
        lines[idx][len]=ch;lines[idx][len+1]=0;
    }
    if(follow_tail)view_top=tail_top();paint_chat();
    if(current_role==ROLE_SYSTEM)return;
    if(transcript_full())ui_notice(tr(TXT_TRANSCRIPT_FULL));
    else if(transcript_warning())ui_notice(tr(TXT_TRANSCRIPT_WARNING));
}
void ui_end(void)
{
    if(!message_active)return;if(record_active)transcript_end();message_active=record_active=0;
    /* A provider's trailing LF must not add another message separator. */
    while(count&&lines[physical(count-1)][0]==0)--count;
    new_line();current_role=ROLE_SYSTEM;skip_spaces=0;
    if(follow_tail||view_top>tail_top())view_top=tail_top();paint_chat();
    if(pending_notice[0]){char text[77];strcpy(text,pending_notice);pending_notice[0]=0;ui_notice(text);}
}
void ui_scroll_lines(int delta)
{long n=(long)view_top+delta;if(n<0)n=0;if((unsigned long)n>tail_top())n=(long)tail_top();view_top=(unsigned)n;follow_tail=view_top==tail_top();paint_chat();}
void ui_scroll_page(int pages){ui_scroll_lines(pages*18);}
static void info_row(unsigned row,const char *text)
{
    char padded[77];unsigned n=(unsigned)strlen(text);if(n>76)n=76;
    memset(padded,' ',76);padded[76]=0;memcpy(padded,text,n);
    if(strcmp(painted[row],padded)!=0){row_text(row+3,2,padded,76);memcpy(painted[row],padded,77);}
}
void ui_help(void)
{
    static const TextId help[]={TXT_HELP,TXT_COUNT,TXT_HELP_SEND,TXT_HELP_INFO,TXT_HELP_NEW,
        TXT_HELP_HELP,TXT_HELP_SAVE,TXT_HELP_EXIT,TXT_COUNT,TXT_HELP_PAGES,
        TXT_HELP_LINES,TXT_COUNT,TXT_HELP_BACK,TXT_HELP_RECONNECT};
    unsigned i;overlay=1;video_hide_cursor();
    for(i=0;i<18;++i)info_row(i,i<sizeof(help)/sizeof(help[0])?tr(help[i]):"");
    info_row(16,"https://github.com/MarcoR-DOS/AI4DOS");
    footer_message(tr(TXT_BACK));
}
void ui_info(void)
{
    unsigned i;char row[77];overlay=1;video_hide_cursor();for(i=0;i<18;++i)info_row(i,"");
    sprintf(row,"%s " AI4DOS_VERSION AI4DOS_VERSION_SUFFIX,tr(TXT_VERSION));info_row(0,row);
    sprintf(row,"%s: " WIRE_VERSION,tr(TXT_WIRE_PROTOCOL));info_row(1,row);
    sprintf(row,"%s: %.12s",tr(TXT_SESSION),session_text[0]?session_text:"-");info_row(3,row);
    sprintf(row,"%s: %s",tr(TXT_STATUS),ui_status_label(0));info_row(4,row);
    sprintf(row,"%s: %s",tr(TXT_SERVER),tr(current_status==UI_ONLINE||current_status==UI_TX_RX?TXT_CONNECTED:TXT_DISCONNECTED));info_row(5,row);
    info_row(14,"License: GPL-3.0-only");
    info_row(15,"mTCP: GPL-3.0-or-later");
    info_row(16,"Watcom runtime: OWPL 1.0 - source available");
    info_row(17,"Source: github.com/open-watcom/open-watcom-v2");
    footer_message(tr(TXT_BACK));
}
void ui_save_prompt(const char *name,const char *hint,int editing)
{
    unsigned len=(unsigned)strlen(name),prefix=(unsigned)strlen(tr(TXT_SAVE_AS));char row[77];overlay=2;video_hide_cursor();if(len>76-prefix)len=76-prefix;
    memset(row,' ',76);row[76]=0;memcpy(row,tr(TXT_SAVE_AS),prefix);memcpy(row+prefix,name,len);row_text(22,2,row,76);footer_message(hint);
    if(editing)video_set_cursor(22,2+prefix+len,1);
}
void ui_exit_prompt(void)
{overlay=3;video_hide_cursor();footer_message(tr(TXT_EXIT_CONFIRM));}
void ui_overlay_end(void)
{overlay=0;ui_status(current_status);paint_chat();}
static unsigned poll_key(void)
{
#ifdef __WATCOMC__
    if(_bios_keybrd(_KEYBRD_READY))return _bios_keybrd(_KEYBRD_READ);
#endif
    return 0;
}
int ui_poll_wait(void)
{
    unsigned key;if(!active)return 1;key=poll_key();if(key==0x3c00)new_requested=1;
    controls_handle(key,1);
    if(key==0x4800)ui_scroll_lines(-1);else if(key==0x5000)ui_scroll_lines(1);
    else if(key==0x4900)ui_scroll_page(-1);else if(key==0x5100)ui_scroll_page(1);
    return 1;
}
int ui_input(char *text,int (*poll_network)(void))
{
    unsigned key;int control;ui_busy(0);
    for(;;){
        if(poll_network&&poll_network()<0)return -1;
        if(new_requested){new_requested=0;return 2;}
        key=poll_key();if(!key)continue;control=controls_handle(key,0);
        if(control==CONTROL_EXIT)return 0;if(control==CONTROL_HANDLED)continue;
        if((key&255)==0){
            if((key>>8)==0x48){ui_scroll_lines(-1);continue;}if((key>>8)==0x50){ui_scroll_lines(1);continue;}
            if((key>>8)==0x49){ui_scroll_page(-1);continue;}if((key>>8)==0x51){ui_scroll_page(1);continue;}
            if((key>>8)==0x3c)return 2;
        }
        if((key&255)==13){
            if(!editor.length)continue;
            if(strcmp(editor.text,"/reconnect")==0){editor_init(&editor);return 3;}
            if(strcmp(editor.text,"/new")==0){editor_init(&editor);return 2;}
            key=strcmp(editor.text,"/info")==0?0x3b00:strcmp(editor.text,"/help")==0?0x3e00:
                strcmp(editor.text,"/save")==0?0x3f00:strcmp(editor.text,"/quit")==0?0x4400:0;
            if(key){editor_init(&editor);paint_input();controls_handle(key,0);continue;}
            if(current_status==UI_ERROR){ui_notice(tr(TXT_RECONNECT_HINT));continue;}
            if(!transcript_can_message(ROLE_USER,ui_label(ROLE_USER),editor.text)){ui_notice(tr(TXT_TRANSCRIPT_FULL));continue;}
            strcpy(text,editor.text);editor_init(&editor);ui_busy(1);return 1;
        }
        if(editor_key(&editor,(unsigned char)key,(unsigned char)(key>>8)))paint_input();
    }
}

void ui_error_wait(void)
{
    unsigned key;ui_busy(1);controls_init();ui_overlay_end();ui_status(UI_ERROR);ui_notice(tr(TXT_BACK));
    do{key=poll_key();}while((key&255)!=27&&key!=0x4400);
}

void ui_notice(const char *text)
{
    if(message_active){strncpy(pending_notice,text,76);pending_notice[76]=0;return;}
    if(strcmp(notice_text,text)==0)return;
    strncpy(notice_text,text,76);notice_text[76]=0;
    ui_scroll_lines(32767);
    /* Full transcripts still show the limit notice, without overwriting history. */
    ui_begin(ROLE_SYSTEM,0);ui_append(notice_text);ui_end();
}
void ui_clear_notice(void)
{if(!transcript_full())notice_text[0]=0;}
