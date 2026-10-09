#ifndef AI4DOS_EDITOR_H
#define AI4DOS_EDITOR_H
#define EDITOR_CAP 1000
typedef struct { char text[EDITOR_CAP+1];unsigned length,cursor; } LineEditor;
void editor_init(LineEditor *e);
int editor_key(LineEditor *e,unsigned char ascii,unsigned char scan);
#endif
