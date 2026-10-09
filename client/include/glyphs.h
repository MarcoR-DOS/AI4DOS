#ifndef AI4DOS_GLYPHS_H
#define AI4DOS_GLYPHS_H
typedef enum { GLYPH_HLINE, GLYPH_VLINE, GLYPH_TL, GLYPH_TR,
 GLYPH_BL, GLYPH_BR, GLYPH_LTEE, GLYPH_RTEE,
 GLYPH_DOUBLE_HLINE, GLYPH_DOUBLE_VLINE, GLYPH_DOUBLE_TL, GLYPH_DOUBLE_TR,
 GLYPH_DOUBLE_BL, GLYPH_DOUBLE_BR, GLYPH_SCROLL_UP, GLYPH_SCROLL_DOWN, GLYPH_COUNT } Glyph;
unsigned char glyph_byte(Glyph glyph,unsigned codepage);
unsigned glyph_codepage(unsigned requested,unsigned detected);
unsigned glyph_detect(void);
#endif
