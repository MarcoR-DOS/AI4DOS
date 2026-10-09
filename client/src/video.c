#include <string.h>
#include "video.h"
#ifdef __WATCOMC__
#include <dos.h>
#endif
static unsigned short painted[VIDEO_ROWS*VIDEO_COLS];
static VideoPlan plan;
static unsigned long writes;
static int active,visible;
#ifdef __WATCOMC__
static unsigned old_mode,old_page,old_shape,old_pos,old_rows,ui_shape;
static VideoAdapter adapter;
static volatile unsigned short __far *screen;
static void bios_mode(unsigned mode)
{union REGS r;r.x.ax=mode;int86(0x10,&r,&r);}
static void font(unsigned function)
{union REGS r;r.x.ax=function;r.h.bl=0;int86(0x10,&r,&r);}
#endif
VideoPlan video_plan(unsigned old_mode,VideoAdapter adapter_kind)
{
    VideoPlan p;p.mode=(old_mode&0x7f)==7?7:3;
    p.segment=p.mode==7?0xb000:0xb800;
    p.bios_cells=(p.mode==3&&adapter_kind==VIDEO_LEGACY);return p;
}
int video_init(void)
{
#ifdef __WATCOMC__
    union REGS r;unsigned columns;
    r.h.ah=0x0f;int86(0x10,&r,&r);old_mode=r.h.al&0x7f;old_page=r.h.bh;
    r.h.ah=3;r.h.bh=(unsigned char)old_page;int86(0x10,&r,&r);old_shape=r.x.cx;old_pos=r.x.dx;
    adapter=VIDEO_LEGACY;
    r.x.ax=0x1a00;r.x.bx=0;int86(0x10,&r,&r);
    if(r.h.al==0x1a)adapter=VIDEO_VGA;
    else {r.h.ah=0x12;r.h.bl=0x10;r.h.bh=0xff;int86(0x10,&r,&r);if(r.h.bh<=1&&r.h.bl<=3)adapter=VIDEO_EGA;}
    old_rows=25;
    if(adapter!=VIDEO_LEGACY)old_rows=*(unsigned char __far *)MK_FP(0x40,0x84)+1U;
    plan=video_plan(old_mode,adapter);
    /* Legacy monochrome BIOSes can report mode 3; the equipment word identifies MDA. */
    if(adapter==VIDEO_LEGACY&&(*(unsigned __far *)MK_FP(0x40,0x10)&0x30)==0x30){
        plan=video_plan(7,adapter);old_mode=7; /* Restore a valid monochrome text mode. */
    }
    bios_mode(plan.mode);
    if(adapter==VIDEO_VGA)font(0x1114);else if(adapter==VIDEO_EGA)font(0x1111);
    r.x.ax=0x0500;int86(0x10,&r,&r);
    r.h.ah=0x0f;int86(0x10,&r,&r);columns=r.h.ah;
    active=1;
    if(columns!=80){video_shutdown();return 0;}
    if(adapter!=VIDEO_LEGACY&&*(unsigned char __far *)MK_FP(0x40,0x84)!=24){video_shutdown();return 0;}
    r.h.ah=3;r.h.bh=0;int86(0x10,&r,&r);ui_shape=r.x.cx;
    screen=(volatile unsigned short __far *)MK_FP(plan.segment,0);
#else
    plan=video_plan(3,VIDEO_VGA);active=1;
#endif
    visible=1;writes=0;memset(painted,0xff,sizeof(painted));video_hide_cursor();video_clear();return 1;
}
void video_hide_cursor(void)
{
    if(!active||!visible)return;
#ifdef __WATCOMC__
    {union REGS r;r.h.ah=1;r.x.cx=0x2000;int86(0x10,&r,&r);}
#endif
    visible=0;
}
void video_set_cursor(unsigned row,unsigned col,int show)
{
    if(!active)return;
    if(!show){video_hide_cursor();return;}
    if(row>=25||col>=80)return;
#ifdef __WATCOMC__
    {union REGS r;r.h.ah=2;r.h.bh=0;r.h.dh=(unsigned char)row;r.h.dl=(unsigned char)col;int86(0x10,&r,&r);
    if(!visible){r.h.ah=1;r.x.cx=ui_shape;int86(0x10,&r,&r);}}
#endif
    visible=1;
}
void video_put_cell(unsigned row,unsigned col,unsigned char ch,unsigned char attr)
{
    unsigned offset;unsigned short cell;
    if(!active||row>=25||col>=80)return;
    offset=row*80U+col;cell=(unsigned short)ch|((unsigned short)attr<<8);
    if(painted[offset]==cell)return;
#ifdef __WATCOMC__
    if(plan.bios_cells){union REGS r;r.h.ah=2;r.h.bh=0;r.h.dh=(unsigned char)row;r.h.dl=(unsigned char)col;int86(0x10,&r,&r);
        r.h.ah=9;r.h.al=ch;r.h.bh=0;r.h.bl=attr;r.x.cx=1;int86(0x10,&r,&r);}
    else screen[offset]=cell;
#endif
    painted[offset]=cell;++writes;
}
void video_clear(void)
{unsigned row,col;for(row=0;row<25;++row)for(col=0;col<80;++col)video_put_cell(row,col,' ',7);}
unsigned video_get_mode(void){return plan.mode;}
unsigned long video_write_count(void){return writes;}
void video_shutdown(void)
{
    if(!active)return;video_hide_cursor();
#ifdef __WATCOMC__
    {union REGS r;bios_mode(old_mode);
    if((old_mode==3||old_mode==7)&&adapter!=VIDEO_LEGACY){
        if(old_rows==43||old_rows==50)font(0x1112);
        else if(old_rows==25)font(adapter==VIDEO_VGA?0x1114:0x1111);
    }
    r.h.ah=5;r.h.al=(unsigned char)old_page;int86(0x10,&r,&r);
    r.h.ah=1;r.x.cx=old_shape;int86(0x10,&r,&r);
    r.h.ah=2;r.h.bh=(unsigned char)old_page;r.x.dx=old_pos;int86(0x10,&r,&r);}
#endif
    active=0;visible=0;
}
