#ifndef AI4DOS_CHATFILE_H
#define AI4DOS_CHATFILE_H
typedef enum { CHAT_SAVE_OK,CHAT_SAVE_EXISTS,CHAT_SAVE_DIRECTORY,
               CHAT_SAVE_ERROR,CHAT_SAVE_INVALID } ChatSaveResult;
int chat_filename(const char *input,char *output);
ChatSaveResult chat_save(const char *name,int overwrite);
#endif
