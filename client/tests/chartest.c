#include <stdio.h>
#include <string.h>
#include "charset.h"
#define CHECK(x) do{if(!(x)){printf("ENCODING FAIL %u\n",(unsigned)__LINE__);return 1;}}while(0)
int main(void)
{
    char wire[1001],dos[1001],input[3];unsigned cp,i;
    const char umlauts[]={ (char)0x84,(char)0x94,(char)0x81,(char)0x8e,(char)0x99,(char)0x9a,(char)0xe1,0 };
    const char *utf8="\303\244\303\266\303\274\303\204\303\226\303\234\303\237";
    for(cp=437;cp<=850;cp+=413){
        CHECK(dos_to_utf8("ASCII",wire,sizeof(wire),cp)==5&&strcmp(wire,"ASCII")==0);
        CHECK(dos_to_utf8(umlauts,wire,sizeof(wire),cp)==14&&strcmp(wire,utf8)==0);
        CHECK(utf8_to_dos(wire,dos,sizeof(dos),cp)==7&&strcmp(dos,umlauts)==0);
        for(i=128;i<256;++i){input[0]=(char)i;input[1]=0;
            CHECK(dos_to_utf8(input,wire,sizeof(wire),cp)>0);
            CHECK(utf8_to_dos(wire,dos,sizeof(dos),cp)==1&&(unsigned char)dos[0]==i);}
        utf8_to_dos("\342\200\234a\342\200\235 \342\200\224 \342\200\242 \342\200\246 \360\237\230\200",dos,sizeof(dos),cp);
        CHECK(strcmp(dos,"\"a\" - * ... ?")==0);
        utf8_to_dos("\300\257X\xed\xa0\x80Y\xf4\x90\x80\x80Z",dos,sizeof(dos),cp);
        CHECK(strchr(dos,'X')&&strchr(dos,'Y')&&strchr(dos,'Z'));
        CHECK(dos_to_utf8(umlauts,wire,14,cp)==-1&&wire[0]==0);
        CHECK(dos_to_utf8("bad\n",wire,sizeof(wire),cp)==-1);
    }
    utf8_to_dos(utf8,dos,sizeof(dos),0);CHECK(strcmp(dos,"???????")==0);
    CHECK(dos_to_utf8(umlauts,wire,sizeof(wire),0)==7&&strcmp(wire,"???????")==0);
    utf8_to_dos("\303\270",dos,sizeof(dos),850);CHECK((unsigned char)dos[0]==0x9b);
    utf8_to_dos("\303\270",dos,sizeof(dos),437);CHECK(strcmp(dos,"?")==0);
    CHECK(utf8_to_dos("\342\200\246",dos,3,437)==0&&dos[0]==0);
    puts("AI4DOS ENCODING PASS");return 0;
}
