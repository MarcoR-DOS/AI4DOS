/* Test-only BIOS keys drive the actual main/network/protocol/file path. */
#include <bios.h>
static unsigned stress_keybrd(unsigned service);
#define _bios_keybrd stress_keybrd
#include "../src/ui.c"
#undef _bios_keybrd
static unsigned script[80],length,next,round,exchange,post,saves;
static int pending_save,finished;
static void add(unsigned key){script[length++]=key;}
static void add_text(const char *text){while(*text)add((unsigned char)*text++);}
static void queue_save(const char *name,int slash)
{
    char path[30];strcpy(path,"CHATS\\");strcat(path,name);remove(path);
    if(slash){add_text("/save");add(13);}else add(0x3f00);
    add_text(name);add(13);add(27);++saves;
}
static unsigned stress_keybrd(unsigned service)
{
    unsigned value;char text[20];FILE *f;
    if(busy&&ui_get_status()==UI_ERROR)return 27;
    if(busy||finished)return 0;
    if(next==length){
        next=length=0;
        if(round<3){
            /* Functional fixture: create a full transcript through the public UI
               API; the following save/F2/NEW/message use the actual main/mTCP. */
            if(exchange==6&&!transcript_full()){
                char fill[513];memset(fill,'Z',512);fill[512]=0;
                ui_busy(1);ui_begin(ROLE_SYSTEM,0);
                while(!transcript_full())ui_append(fill);
                ui_end();ui_busy(0);
            }
            if(transcript_full()){
                sprintf(text,"FULL%u.TXT",round);queue_save(text,round%2);add(0x3c00);
                ++round;exchange=0;pending_save=0;
            }else if(pending_save){
                sprintf(text,"S%u%03u.TXT",round,exchange);queue_save(text,exchange%4==0);pending_save=0;
            }else{
                sprintf(text,"m%03u",exchange++);add_text(text);add(13);
                if(exchange%2==0)pending_save=1;
            }
        }else if(post<3){
            sprintf(text,"after%u",post++);add_text(text);add(13);
        }else{
            queue_save("AFTER.TXT",1);add(0x4400);add(0x4400);
            f=fopen("STRESS.LOG","w");if(f){fprintf(f,"rounds=%u post=%u saves=%u\n",round,post,saves);fclose(f);}
        }
    }
    value=script[next];
    if(service==_KEYBRD_READ){++next;if(next==length&&post==3&&round==3&&value==0x4400)finished=1;}
    return value;
}
