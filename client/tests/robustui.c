/* DOSBox-X fixture: actual main/network/mTCP with BIOS keys only replaced.
   Read back video cells and transcript before production UI shutdown. */
#include <bios.h>
#include <dos.h>
#include <stdlib.h>
static unsigned qa_key(unsigned service);
#define _bios_keybrd qa_key
#define ui_init qa_init
#define ui_shutdown qa_shutdown
#include "../src/ui.c"
#undef _bios_keybrd
#undef ui_init
#undef ui_shutdown
static unsigned errors,offline_seen,online_seen,modal_saved;
static unsigned short before[2000];
static unsigned short __far *cells;
static char qa_footer[81];
static void check_edges(void)
{
    unsigned row,col;char want[81];unsigned dirs=ui_scroll_directions(),n=10;
    if(overlay)return;
    strcpy(want,qa_footer);
    if(dirs&UI_SCROLL_UP)want[n++]=(char)glyph_byte(GLYPH_SCROLL_UP,ui_codepage());
    if(dirs&UI_SCROLL_DOWN)want[n++]=(char)glyph_byte(GLYPH_SCROLL_DOWN,ui_codepage());
    for(col=0;col<80;++col)if((cells[24*80+col]&255)!=(unsigned char)want[col])++errors;
    for(row=3;row<=20;++row)for(col=0;col<2;++col)
        if(cells[row*80+col]!=before[row*80+col]||cells[row*80+78+col]!=before[row*80+78+col])++errors;
}
int ui_init(unsigned cp)
{
    unsigned i;int rc=qa_init(cp);if(!rc)return rc;
    cells=(unsigned short __far *)MK_FP(video_get_mode()==7?0xb000:0xb800,0);
    for(i=0;i<2000;++i)before[i]=cells[i];strcpy(qa_footer,painted_footer);return rc;
}
void ui_shutdown(void)
{
    FILE *f;check_edges();f=fopen("QA.TXT","wb");if(f){transcript_save(f);fclose(f);}else ++errors;
    f=fopen("QA.LOG","w");if(f){fprintf(f,"%s errors=%u offline=%u online=%u status=%s\n",errors?"FAIL":"PASS",errors,offline_seen,online_seen,ui_status_label(1));fclose(f);}
    qa_shutdown();
}
static unsigned qa_key(unsigned service)
{
    static const unsigned short keys[]={0x3b00,27,0x3e00,27,0x3f00,27,0x4900,0x5100,0x4800,0x5000,0x3c00,
      '/', 'r','e','c','o','n','n','e','c','t',13,0x4400,27,0x4400,0x4400};
    static unsigned step,at,phase;
    unsigned key,i;const char *mode=getenv("QA_MODE");const char *text;
    if(busy)return 0;
    if(ui_get_status()==UI_ERROR)++offline_seen;
    if(ui_get_status()==UI_ONLINE)++online_seen;
    if(mode&&strcmp(mode,"offline")!=0&&strcmp(mode,"once")!=0){
        if(phase==0){
            if(strcmp(mode,"chat")==0||strcmp(mode,"idlequit")==0)phase=3;
            else if(strcmp(mode,"idle")==0){if(ui_get_status()!=UI_ERROR)return 0;phase=2;}
            else phase=1;
        }
        if(phase==1)text="drop\r";
        else if(phase==2){if(ui_get_status()!=UI_ERROR)return 0;text="/reconnect\r";}
        else if(phase==3){if(ui_get_status()!=UI_ONLINE)return 0;text="after\r";}
        else {
            if(strcmp(mode,"idlequit")==0){if(ui_get_status()!=UI_ERROR)return 0;phase=5;}
            text="/quit\r";
        }
        if(phase>4)key=0x4400;else key=(unsigned char)text[at];
        if(service==_KEYBRD_READ){if(phase>4)++phase;else if(!text[++at]){at=0;++phase;}}
        return key;
    }
    if(step>=sizeof(keys)/sizeof(keys[0]))return 0;
    key=keys[step];
    if(service==_KEYBRD_READ){
        check_edges();
        if(modal_saved&&key==27){
            /* Close and check all 2000 cells on the next read. */
            modal_saved=2;
        }else if(modal_saved==2){
            for(i=0;i<2000;++i)if(cells[i]!=before[i])++errors;
            modal_saved=0;
        }
        if(key==0x3b00||key==0x3e00){for(i=0;i<2000;++i)before[i]=cells[i];modal_saved=1;}
        ++step;
        if(mode&&strcmp(mode,"once")==0&&step==10)step=22;
    }
    return key;
}
