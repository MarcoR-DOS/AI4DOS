/* DOS-only F1 delta check; reads video memory without captures or network. */
#include <stdio.h>
#include <string.h>
#include <dos.h>
#include "ui.h"
#include "video.h"
#include "glyphs.h"
#include "l10n.h"
#include "version.h"
#include "protocol.h"
#define CHECK(x) do { if(!(x)){printf("FAIL line %u\n",(unsigned)__LINE__);return 1;} } while(0)
static unsigned short saved[2000];
static unsigned short __far *cells;
static int row_equals(unsigned row,const char *text)
{
    unsigned col,n=(unsigned)strlen(text);
    if(n>76)return 0;
    for(col=0;col<76;++col)
        if(cells[row*80+col+2]!=((unsigned short)(col<n?(unsigned char)text[col]:' ')|0x0700))return 0;
    return 1;
}
int main(void)
{
    static const unsigned pages[]={437,850,1};
    static const char * const notices[]={
        "License: GPL-3.0-only",
        "mTCP: GPL-3.0-or-later",
        "Watcom Runtime: OWPL 1.0 - source available",
        "Source: github.com/open-watcom/open-watcom-v2"};
    unsigned lang,page,state,status,busy,i,row,col,n;char text[77];
    for(lang=0;lang<LANG_COUNT;++lang)for(page=0;page<3;++page){
        language_set((Language)lang);CHECK(ui_init(pages[page]));
        cells=(unsigned short __far *)MK_FP(video_get_mode()==7?0xb000:0xb800,0);
        ui_set_session("012345abcdef");
        for(state=0;state<4;++state){
            if(state==1){ui_begin(ROLE_AI,0);for(i=0;i<150;++i)ui_append("scroll line\n");ui_end();}
            else if(state==2)ui_scroll_lines(-300);
            else if(state==3)ui_scroll_lines(1);
            for(status=0;status<=UI_ERROR;++status)for(busy=0;busy<2;++busy){
                ui_status((UiStatus)status);ui_busy(busy);
                for(i=0;i<2000;++i)saved[i]=cells[i];
                ui_info();
                sprintf(text,"%s: 012345abcdef",tr(TXT_SESSION));CHECK(row_equals(3,text));
                sprintf(text,"%s: %s",tr(TXT_STATUS),ui_status_label(0));CHECK(row_equals(4,text));
                sprintf(text,"%s: %s",tr(TXT_SERVER),tr(status==UI_ONLINE||status==UI_TX_RX?TXT_CONNECTED:TXT_DISCONNECTED));CHECK(row_equals(5,text));
                CHECK(row_equals(6,""));CHECK(row_equals(7,""));
                CHECK(row_equals(8,"AI4DOS"));
                sprintf(text,"%s: " AI4DOS_VERSION AI4DOS_VERSION_SUFFIX,tr(TXT_VERSION));CHECK(row_equals(9,text));
                CHECK(row_equals(10,"Wire Protocol: " WIRE_VERSION));
                CHECK(row_equals(11,notices[0]));
                CHECK(row_equals(12,"Source: github.com/MarcoR-DOS/AI4DOS"));
                CHECK(row_equals(13,""));CHECK(row_equals(14,""));
                CHECK(row_equals(15,"Third-Party Licenses"));
                for(i=1;i<4;++i)CHECK(row_equals(15+i,notices[i]));
                CHECK(row_equals(19,""));CHECK(row_equals(20,""));
                CHECK(row_equals(24,tr(TXT_BACK)));
                for(row=0;row<24;++row)for(col=0;col<80;++col)
                    if(row<3||row>20||col<2||col>77)CHECK(cells[row*80+col]==saved[row*80+col]);
                CHECK(cells[1920]==saved[1920]&&cells[1921]==saved[1921]);
                CHECK(cells[1998]==saved[1998]&&cells[1999]==saved[1999]);
                for(i=0;i<4;++i){n=(unsigned)strlen(notices[i]);CHECK(n<=76);for(col=0;col<n;++col)CHECK((unsigned char)notices[i][col]>=32&&(unsigned char)notices[i][col]<127);}
                ui_overlay_end();
                for(i=0;i<2000;++i)CHECK(cells[i]==saved[i]);
            }
        }
        ui_shutdown();
    }
    puts("AI4DOS F1 PASS: EN/DE CP437/CP850/ASCII, 192 states, exact rows, frame/header/input/footer/scroll restored");
    return 0;
}
