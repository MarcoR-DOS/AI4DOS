#include "glyphs.h"
#ifdef __WATCOMC__
#include <dos.h>
#endif
unsigned glyph_codepage(unsigned requested,unsigned detected)
{ unsigned cp=requested?requested:detected;return cp==437||cp==850?cp:0; }
unsigned char glyph_byte(Glyph glyph,unsigned codepage)
{
    /* Single and pure-double box glyphs are shared by CP437 and CP850. No mixed-line bytes. */
    static const unsigned char boxes[GLYPH_COUNT]={0xc4,0xb3,0xda,0xbf,0xc0,0xd9,0xc3,0xb4,0xcd,0xba,0xc9,0xbb,0xc8,0xbc,0x18,0x19};
    static const unsigned char ascii[GLYPH_COUNT]={'-','|','+','+','+','+','+','+','=','|','+','+','+','+','^','v'};
    if((unsigned)glyph>=GLYPH_COUNT)return '?';
    return codepage==437||codepage==850?boxes[glyph]:ascii[glyph];
}
unsigned glyph_detect(void)
{
#ifdef __WATCOMC__
    union REGS in,out;in.x.ax=0x6601;int86(0x21,&in,&out);
    if(!out.x.cflag&&(out.x.bx==437||out.x.bx==850))return out.x.bx;
#endif
    return 0;
}
