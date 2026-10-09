/* Selective Georgi modal-save/overwrite/notice flow, neutral file and role APIs. */
#include <string.h>
#include "controls.h"
#include "ui.h"
#include "l10n.h"
#include "chatfile.h"
#define DIALOG_SAVE 1
#define DIALOG_OVERWRITE 2
#define DIALOG_INFO 3
#define DIALOG_EXIT 4
static unsigned dialog,name_len;
static int name_overflow;
static char name[40],filename[13];
void controls_init(void){dialog=name_len=0;name_overflow=0;name[0]=0;}
int controls_active(void){return dialog!=0;}
static void close_dialog(void){dialog=0;ui_overlay_end();}
static void save_file(int overwrite)
{
    ChatSaveResult result;char message[77];
    result=chat_save(filename,overwrite);
    if(result==CHAT_SAVE_EXISTS){dialog=DIALOG_OVERWRITE;ui_save_prompt(filename,tr(TXT_SAVE_OVERWRITE),0);}
    else if(result==CHAT_SAVE_OK){
        close_dialog();strcpy(message,tr(TXT_SAVED));strcat(message,"CHATS\\");strcat(message,filename);ui_notice(message);
    }else{
        dialog=DIALOG_SAVE;ui_save_prompt(name,tr(result==CHAT_SAVE_DIRECTORY?TXT_SAVE_DIRECTORY:TXT_SAVE_ERROR),1);
    }
}
int controls_handle(unsigned key,int busy)
{
    unsigned char ch=(unsigned char)key;unsigned scan=key>>8;
    if(!key)return CONTROL_NONE;
    if(dialog){
        if(ch==27){close_dialog();return CONTROL_HANDLED;}
        if(dialog==DIALOG_EXIT){if(ch==0&&scan==0x44)return CONTROL_EXIT;}
        else if(dialog==DIALOG_OVERWRITE){if(ch==0&&scan==0x3f)save_file(1);}
        else if(dialog==DIALOG_SAVE){
            if(ch==8){if(name_len)name[--name_len]=0;name_overflow=0;}
            else if(ch==13){
                if(!name_overflow&&chat_filename(name,filename))save_file(0);
                else ui_save_prompt(name,tr(TXT_SAVE_INVALID),1);
                return CONTROL_HANDLED;
            }else if(ch>=32){
                /* Keep invalid characters visible; never silently correct a name. */
                if(name_len==sizeof(name)-1){name_overflow=1;ui_save_prompt(name,tr(TXT_SAVE_INVALID),1);return CONTROL_HANDLED;}
                name[name_len++]=(char)ch;name[name_len]=0;
            }
            ui_save_prompt(name,tr(TXT_SAVE_HINT),1);
        }
        return CONTROL_HANDLED;
    }
    ui_clear_notice();
    if(ch==0&&(scan==0x3b||scan==0x3e||scan==0x3f||scan==0x44)){
        if(busy)return CONTROL_HANDLED;
        if(scan==0x3b){dialog=DIALOG_INFO;ui_info();}
        else if(scan==0x3e){dialog=DIALOG_INFO;ui_help();}
        else if(scan==0x3f){dialog=DIALOG_SAVE;name_len=0;name_overflow=0;name[0]=0;ui_save_prompt(name,tr(TXT_SAVE_HINT),1);}
        else{dialog=DIALOG_EXIT;ui_exit_prompt();}
        return CONTROL_HANDLED;
    }
    return CONTROL_NONE;
}
