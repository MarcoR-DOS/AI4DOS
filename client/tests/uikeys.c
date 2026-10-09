/* Emulator-only BIOS keyboard replacement for the actual interactive client. */
#include <bios.h>
static unsigned test_keybrd(unsigned service);
#define _bios_keybrd test_keybrd
#define ui_status recorded_status
#define ui_init recorded_init
#include "../src/ui.c"
#undef _bios_keybrd
#undef ui_status
#undef ui_init
int ui_init(unsigned cp)
{
    int ok;FILE *f;ok=recorded_init(cp);f=fopen("STATUS.LOG","w");
    if(f){fprintf(f,"%s\n",ui_status_label(1));fclose(f);}return ok;
}
void ui_status(UiStatus status)
{
    FILE *f;recorded_status(status);f=fopen("STATUS.LOG","a");
    if(f){fprintf(f,"%s\n",ui_status_label(1));fclose(f);}
}
static unsigned test_keybrd(unsigned service)
{
    static const unsigned short keys[]={
      'h','e','l','l','o','-',0x3e00,27,0x3b00,27,0x3f00,'T','E',13,27,
      'd','o','s',13,'/','s','a','v','e',13,'C','M','D','.','T','X','T',13,27,0x3c00,'h','e','l','l','o','-','a','g','a','i','n',13,
      0x4400,27,0x4400,0x4400};
    static unsigned next;
    unsigned value;
    if(busy || next>=sizeof(keys)/sizeof(keys[0]))return 0;
    value=keys[next];if(service==_KEYBRD_READ)++next;return value;
}
