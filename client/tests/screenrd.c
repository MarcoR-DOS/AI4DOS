/* Test-only BIOS readback after a pre-UI startup failure. */
#include <dos.h>
#include <stdio.h>
int main(void)
{
    union REGS r;unsigned page,row,col,cursor,cell;FILE *f;
    r.h.ah=0x0f;int86(0x10,&r,&r);page=r.h.bh;
    r.h.ah=3;r.h.bh=(unsigned char)page;int86(0x10,&r,&r);cursor=r.x.dx;
    f=fopen("QASCR.BIN","wb");if(!f)return 1;
    for(row=0;row<25;++row)for(col=0;col<80;++col){
        r.h.ah=2;r.h.bh=(unsigned char)page;r.h.dh=(unsigned char)row;r.h.dl=(unsigned char)col;int86(0x10,&r,&r);
        r.h.ah=8;r.h.bh=(unsigned char)page;int86(0x10,&r,&r);cell=r.x.ax;
        if(fwrite(&cell,2,1,f)!=1){fclose(f);return 1;}
    }
    r.h.ah=2;r.h.bh=(unsigned char)page;r.x.dx=cursor;int86(0x10,&r,&r);
    return fclose(f)!=0;
}
