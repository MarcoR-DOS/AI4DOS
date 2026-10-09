#ifndef AI4DOS_CHARSET_H
#define AI4DOS_CHARSET_H
/* DOS byte strings at UI/editor/transcript; UTF-8 only at the wire boundary. */
int dos_to_utf8(const char *src,char *dst,unsigned capacity,unsigned codepage);
unsigned utf8_to_dos(const char *src,char *dst,unsigned capacity,unsigned codepage);
#endif
