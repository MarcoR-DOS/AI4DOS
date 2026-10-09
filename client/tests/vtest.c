/* DOS-only emulator video/keyboard/layout test; never linked into AI4DOS. */
#include <assert.h>
#include <bios.h>
#include <dos.h>
#include <stdio.h>
#include <string.h>
#include "ui.h"
#include "video.h"
#include "glyphs.h"
#include "controls.h"
#include "l10n.h"
#include "version.h"
#undef assert
#define assert(x) do { if(!(x)){FILE *e=fopen("build\\VFAIL.LOG","w");if(e){fprintf(e,"FAIL line %u\n",(unsigned)__LINE__);fclose(e);}return 1;} } while(0)
static unsigned short __far *cells;
static int screen_text(unsigned row,unsigned col,const char *text)
{
    while(*text)if((cells[row*80+col++]&255)!=(unsigned char)*text++)return 0;
    return 1;
}
static void key(unsigned ascii,unsigned scan)
{
    unsigned __far *head=(unsigned __far *)MK_FP(0x40,0x1a);
    unsigned __far *tail=(unsigned __far *)MK_FP(0x40,0x1c);
    *head=0x1e;*tail=0x20;*(unsigned __far *)MK_FP(0x40,0x1e)=ascii|(scan<<8);
}
static unsigned entered;
static int input_keys(void)
{
    static const unsigned char text[]="hello-ui";
    if(entered<sizeof(text)-1)key(text[entered++],0);
    else key(13,0x1c);
    return 1;
}
int main(int argc,char **argv)
{
    union REGS r;unsigned mode,shape,pos,page,rows,i,cp;char input[1001];FILE *f;
    assert(argc>1);r.h.ah=0x0f;int86(0x10,&r,&r);mode=r.h.al&0x7f;page=r.h.bh;
    if(strcmp(argv[1],"MDA")==0)mode=7; /* Hercules BIOS startup mode 3 is not a valid mono text mode. */
    if(strcmp(argv[1],"VGA")==0||strcmp(argv[1],"EGA")==0){r.x.ax=0x1112;r.h.bl=0;int86(0x10,&r,&r);}
    rows=*(unsigned char __far *)MK_FP(0x40,0x84);
    r.h.ah=1;r.x.cx=0x0607;int86(0x10,&r,&r);
    r.h.ah=2;r.h.bh=(unsigned char)page;r.x.dx=0x0409;int86(0x10,&r,&r);
    r.h.ah=3;r.h.bh=(unsigned char)page;int86(0x10,&r,&r);shape=r.x.cx;pos=r.x.dx;
    for(i=0;i<6;++i){cp=i%3==0?437:i%3==1?850:1;language_set(i<3?LANG_EN:LANG_DE);assert(ui_init(cp));
        cells=(unsigned short __far *)MK_FP(video_get_mode()==7?0xb000:0xb800,0);
        assert((cells[0]&255)==glyph_byte(GLYPH_DOUBLE_TL,cp));assert((cells[79]&255)==glyph_byte(GLYPH_DOUBLE_TR,cp));
        assert(screen_text(1,2,AI4DOS_HEADER));assert(screen_text(1,68,"CONNECTING")); /* title row 1 / col 2 */
        assert((cells[162]&255)==glyph_byte(GLYPH_HLINE,cp));
        assert((cells[161]&255)==' '&&(cells[238]&255)==' ');
        assert((cells[1682]&255)==glyph_byte(GLYPH_HLINE,cp));
        assert((cells[1762]&255)=='>'&&(cells[1764]&255)==' ');
        assert((cells[1920]&255)==' ');assert(screen_text(24,2,"PgUp/Dn"));
        assert((cells[1840]&255)==glyph_byte(GLYPH_DOUBLE_BL,cp));assert((cells[1919]&255)==glyph_byte(GLYPH_DOUBLE_BR,cp));
        r.h.ah=3;r.h.bh=0;int86(0x10,&r,&r);assert(r.x.cx&0x2000);
        ui_status(UI_ONLINE);assert(screen_text(1,72,"ONLINE"));
        ui_status(UI_TX_RX);assert(screen_text(1,73,"TX/RX"));
        ui_status(UI_ERROR);assert(screen_text(1,73,"ERROR"));
        ui_status(UI_ONLINE);
        entered=0;assert(ui_input(input,input_keys)==1&&strcmp(input,"hello-ui")==0);
        ui_begin(ROLE_USER,0);ui_append(input);ui_end();ui_begin(ROLE_AI,0);
        ui_append("Test reply: hello-ui\nA word wraps across DATA frames, while the hardware cursor stays hidden.");ui_end();
        r.h.ah=3;r.h.bh=0;int86(0x10,&r,&r);assert(r.x.cx&0x2000);
        if(i==1){f=fopen("build\\SCREEN.BIN","wb");assert(f);assert(fwrite(cells,2,2000,f)==2000);fclose(f);}
        ui_busy(0);r.h.ah=3;r.h.bh=0;int86(0x10,&r,&r);assert(!(r.x.cx&0x2000)&&r.x.dx==0x1604);
        controls_handle(0x3e00,0);assert(screen_text(3,2,tr(TXT_HELP))&&screen_text(5,2,"Enter"));assert(screen_text(24,2,tr(TXT_BACK)));
        r.h.ah=3;r.h.bh=0;int86(0x10,&r,&r);assert(r.x.cx&0x2000);
        controls_handle(27,0);assert(screen_text(3,2,tr(TXT_USER)));
        ui_set_session("012345abcdef");controls_handle(0x3b00,0);assert(screen_text(3,2,"Version " AI4DOS_VERSION AI4DOS_VERSION_SUFFIX));assert(screen_text(4,2,tr(TXT_WIRE_PROTOCOL)));assert(screen_text(6,2,tr(TXT_SESSION)));assert(screen_text(7,2,"Status: Online"));controls_handle(27,0);
        controls_handle(0x3f00,0);controls_handle('T',0);assert(screen_text(22,2,tr(TXT_SAVE_AS)));
        r.h.ah=3;r.h.bh=0;int86(0x10,&r,&r);assert(!(r.x.cx&0x2000)&&r.x.dx==0x1600+3+strlen(tr(TXT_SAVE_AS)));
        controls_handle(27,0);assert((cells[1762]&255)=='>');
        controls_handle(0x4400,0);assert(screen_text(24,2,tr(TXT_EXIT_CONFIRM)));controls_handle(27,0);
        controls_handle(0x3e00,0);key(27,1);ui_error_wait();
        assert(ui_get_status()==UI_ERROR&&screen_text(1,73,"ERROR"));
        assert(screen_text(24,2,"PgUp/Dn"));
        r.h.ah=3;r.h.bh=0;int86(0x10,&r,&r);assert(r.x.cx&0x2000);
        ui_busy(1);key(0,0x3c);ui_poll_wait();assert(ui_input(input,0)==2);
        assert(screen_text(24,2,"PgUp/Dn"));
        ui_shutdown();r.h.ah=0x0f;int86(0x10,&r,&r);assert((r.h.al&0x7f)==mode&&r.h.bh==page);
        r.h.ah=3;r.h.bh=(unsigned char)page;int86(0x10,&r,&r);assert(r.x.cx==shape&&r.x.dx==pos);
        if(strcmp(argv[1],"VGA")==0||strcmp(argv[1],"EGA")==0)assert(*(unsigned char __far *)MK_FP(0x40,0x84)==rows);
    }
    printf("AI4DOS VIDEO PASS %s: EN/DE CP437 CP850 ASCII, closed 80x25 frame, BIOS keyboard/editor, cursor, mode/font restore\n",argv[1]);return 0;
}
