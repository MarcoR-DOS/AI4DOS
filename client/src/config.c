#include <stdio.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include "config.h"
static int set(char *dst,unsigned cap,const char *src)
{unsigned n=(unsigned)strlen(src);if(n>=cap)return 0;memcpy(dst,src,n+1);return 1;}
int config_load(const char *path,Config *cfg)
{
    FILE *fp;char line[260],*eq,*end;unsigned i,n;unsigned long port;int ok=1,io_error=0;
    memset(cfg,0,sizeof(*cfg));fp=fopen(path,"rt");if(!fp)return 0;
    while(fgets(line,sizeof(line),fp)){
        if(!strchr(line,'\n')&&!feof(fp)){ok=0;break;}
        end=line+strlen(line);while(end>line&&(end[-1]=='\r'||end[-1]=='\n'))--end;*end=0;
        if(!line[0]||line[0]=='#')continue;
        eq=strchr(line,'=');if(!eq){ok=0;break;}*eq++=0;
        if(strcmp(line,"SERVER")==0)ok=set(cfg->server,sizeof(cfg->server),eq);
        else if(strcmp(line,"DEVICE")==0)ok=set(cfg->device,sizeof(cfg->device),eq);
        else if(strcmp(line,"SECRET")==0)ok=set(cfg->secret,sizeof(cfg->secret),eq);
        else if(strcmp(line,"LANGUAGE")==0)cfg->language=language_parse(eq);
        else if(strcmp(line,"CODEPAGE")==0){
            if(strcmp(eq,"AUTO")==0)cfg->codepage=0;
            else if(strcmp(eq,"437")==0)cfg->codepage=437;
            else if(strcmp(eq,"850")==0)cfg->codepage=850;
            else if(strcmp(eq,"ASCII")==0)cfg->codepage=1;
            else ok=0;
        }
        else if(strcmp(line,"PORT")==0){port=strtoul(eq,&end,10);ok=(*eq&&!*end&&port>=1&&port<=65535UL);if(ok)cfg->port=(unsigned)port;}
        else ok=0;
        if(!ok)break;
    }
    if(ferror(fp)){ok=0;io_error=1;}fclose(fp);
    if(!cfg->server[0]||!cfg->device[0]||!cfg->port)ok=0;
    n=(unsigned)strlen(cfg->secret);if(n<8)ok=0;
    for(i=0;i<n;++i)if((unsigned char)cfg->secret[i]<33||(unsigned char)cfg->secret[i]>126)ok=0;
    for(i=0;cfg->device[i];++i){char c=cfg->device[i];if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='.'||c=='_'||c=='-'))ok=0;}
    if(!ok){memset(cfg,0,sizeof(*cfg));errno=io_error?EIO:EINVAL;}return ok;
}
