/* Selective Georgi filename/device/directory/binary-save concepts.
   Append .TXT only without an extension; stage writes before replacing an existing file. */
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <sys/stat.h>
#ifdef __WATCOMC__
#include <direct.h>
#define CHAT_DIR "CHATS"
#define CHAT_PREFIX "CHATS\\"
#else
#define CHAT_DIR "CHATS"
#define CHAT_PREFIX "CHATS/"
#endif
#include "chatfile.h"
#include "transcr.h"
static int filename_char(char ch)
{return (ch>='A'&&ch<='Z')||(ch>='a'&&ch<='z')||(ch>='0'&&ch<='9')||ch=='_'||ch=='-';}
int chat_filename(const char *input,char *output)
{
    unsigned i,base=0,ext=0;int dot=0;char upper[9],ch;
    output[0]=0;
    for(i=0;input[i];++i){
        ch=input[i];if(ch=='.'){if(dot||!base)return 0;dot=1;continue;}
        if(!filename_char(ch))return 0;
        if(dot){if(++ext>3)return 0;}
        else{if(base==8)return 0;upper[base++]=ch>='a'&&ch<='z'?(char)(ch-'a'+'A'):ch;}
    }
    if(!base||(dot&&!ext))return 0;upper[base]=0;
    if(strcmp(upper,"CON")==0||strcmp(upper,"PRN")==0||strcmp(upper,"AUX")==0||strcmp(upper,"NUL")==0||
       (base==4&&(strncmp(upper,"COM",3)==0||strncmp(upper,"LPT",3)==0)&&upper[3]>='1'&&upper[3]<='9'))return 0;
    strcpy(output,input);if(!dot)strcat(output,".TXT");return 1;
}
ChatSaveResult chat_save(const char *name,int overwrite)
{
    char filename[13],path[20];FILE *fp;struct stat st;int exists,ok;
    const char *temp=CHAT_PREFIX "A4SAVE.$$$",*backup=CHAT_PREFIX "A4SAVE.$BK";
    if(!chat_filename(name,filename))return CHAT_SAVE_INVALID;
    if(stat(CHAT_DIR,&st)!=0){
        if(errno!=ENOENT)return CHAT_SAVE_DIRECTORY;
#ifdef __WATCOMC__
        if(mkdir(CHAT_DIR)!=0)return CHAT_SAVE_DIRECTORY;
#else
        if(mkdir(CHAT_DIR,0700)!=0)return CHAT_SAVE_DIRECTORY;
#endif
    }else if((st.st_mode&S_IFMT)!=S_IFDIR)return CHAT_SAVE_DIRECTORY;
    strcpy(path,CHAT_PREFIX);strcat(path,filename);
    exists=stat(path,&st)==0;
    if(!exists&&errno!=ENOENT)return CHAT_SAVE_ERROR;
    if(exists){
        if(!overwrite)return CHAT_SAVE_EXISTS;
        if((st.st_mode&S_IFMT)!=S_IFREG)return CHAT_SAVE_ERROR;
    }
    /* Single DOS process. Never reuse a recovery file left by an interrupted save. */
    if(stat(temp,&st)==0||errno!=ENOENT)return CHAT_SAVE_ERROR;
    if(exists&&(stat(backup,&st)==0||errno!=ENOENT))return CHAT_SAVE_ERROR;
    fp=fopen(temp,"wb");if(!fp)return CHAT_SAVE_ERROR;
    ok=transcript_save(fp);if(fclose(fp)!=0)ok=0;
    if(!ok){remove(temp);return CHAT_SAVE_ERROR;}
    if(exists&&rename(path,backup)!=0){remove(temp);return CHAT_SAVE_ERROR;}
    if(rename(temp,path)!=0){if(exists)rename(backup,path);remove(temp);return CHAT_SAVE_ERROR;}
    if(exists&&remove(backup)!=0)return CHAT_SAVE_ERROR;
    return CHAT_SAVE_OK;
}
