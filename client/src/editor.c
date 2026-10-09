/* Selective generic insert/delete/cursor concepts; no product-dependent editor. */
#include <string.h>
#include "editor.h"
void editor_init(LineEditor *e){e->text[0]=0;e->length=e->cursor=0;}
int editor_key(LineEditor *e,unsigned char ascii,unsigned char scan)
{
    if(ascii==8){if(e->cursor){memmove(e->text+e->cursor-1,e->text+e->cursor,e->length-e->cursor+1);--e->cursor;--e->length;}return 1;}
    if(ascii>=32&&ascii!=127){if(e->length==EDITOR_CAP)return 0;
        memmove(e->text+e->cursor+1,e->text+e->cursor,e->length-e->cursor+1);e->text[e->cursor++]=(char)ascii;++e->length;return 1;}
    if(ascii==0){switch(scan){
        case 0x4b:if(e->cursor)--e->cursor;break;
        case 0x4d:if(e->cursor<e->length)++e->cursor;break;
        case 0x47:e->cursor=0;break;
        case 0x4f:e->cursor=e->length;break;
        case 0x53:if(e->cursor<e->length){memmove(e->text+e->cursor,e->text+e->cursor+1,e->length-e->cursor);--e->length;}break;
        default:return 0;
    }return 1;}return 0;
}
