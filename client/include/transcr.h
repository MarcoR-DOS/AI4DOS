#ifndef AI4DOS_TRANSCR_H
#define AI4DOS_TRANSCR_H
#include <stdio.h>
#include "roles.h"
#define TRANSCRIPT_CAPACITY 61440U
#define TRANSCRIPT_WARNING 51200U
void transcript_reset(void);
unsigned transcript_size(void);
unsigned transcript_messages(void);
Role transcript_role(unsigned index);
int transcript_full(void);
int transcript_warning(void);
int transcript_can_message(Role role,const char *label,const char *text);
int transcript_begin(Role role,const char *label);
unsigned transcript_append(const char *text);
void transcript_end(void);
int transcript_save(FILE *fp);
#endif
