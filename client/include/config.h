#ifndef AI4DOS_CONFIG_H
#define AI4DOS_CONFIG_H
#include "l10n.h"
typedef struct { char server[64],device[65],secret[129];unsigned port,codepage;Language language; } Config;
int config_load(const char *path,Config *cfg);
#endif
