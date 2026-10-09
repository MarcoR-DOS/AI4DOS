#include <stdio.h>
#include <string.h>
#include "protocol.h"
#include "sha256.h"
#define CHECK(x) do{if(!(x)){printf("FAIL line %u\n",(unsigned)__LINE__);return 1;}}while(0)
int main(void)
{
    static const char *labels[]={"ChatGPT","Claude","Gemini","Mistral","NVIDIA","OpenRouter","AI","unknown"};
    unsigned char digest[32],key[20];char hex[65],frame[90];Protocol p;Event e;unsigned i;
    memset(key,0x0b,sizeof(key));
    hmac_sha256(key,sizeof(key),(const unsigned char *)"Hi There",8,digest);digest_to_hex(digest,hex);
    CHECK(strcmp(hex,"b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7")==0);
    sha256_digest((const unsigned char *)"abc",3,digest);digest_to_hex(digest,hex);
    CHECK(strcmp(hex,"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")==0);
    protocol_init(&p);CHECK(protocol_parse(&p,"BEGIN",&e)==EV_INVALID);
    CHECK(protocol_parse(&p,WIRE_GREETING,&e)==EV_GREETING);
    CHECK(protocol_parse(&p,"CHALLENGE 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",&e)==EV_CHALLENGE);
    CHECK(protocol_parse(&p,"OK AUTH",&e)==EV_AUTH);
    CHECK(protocol_expect_session(&p));CHECK(protocol_parse(&p,"SESSION 0123456789ab",&e)==EV_SESSION);
    CHECK(protocol_expect_reply(&p));CHECK(protocol_parse(&p,"BEGIN",&e)==EV_BEGIN);
    CHECK(protocol_parse(&p,"DATA hello\\nworld\\t\\\\",&e)==EV_DATA);CHECK(e.role==ROLE_AI);
    CHECK(strcmp(e.text,"hello\nworld\t\\")==0);
    CHECK(protocol_parse(&p,"DATA bad\\z",&e)==EV_INVALID);
    CHECK(protocol_parse(&p,"END",&e)==EV_END);CHECK(protocol_expect_close(&p));
    CHECK(protocol_parse(&p,"OK BYE",&e)==EV_BYE);
    p.state=READY;CHECK(!protocol_expect_resume(&p,"bad"));
    CHECK(protocol_expect_resume(&p,"0123456789ab"));
    CHECK(protocol_parse(&p,"SESSION 111111111111",&e)==EV_INVALID);
    CHECK(protocol_parse(&p,"OK RESUME",&e)==EV_RESUME);
    CHECK(strcmp(p.session,"0123456789ab")==0&&p.state==READY);
    CHECK(protocol_expect_resume(&p,p.session));
    CHECK(protocol_parse(&p,"ERROR SESSION session unavailable",&e)==EV_ERROR);
    CHECK(strcmp(p.session,"0123456789ab")==0);
    protocol_init(&p);CHECK(protocol_parse(&p,"ERROR AUTH_FAILED denied",&e)==EV_ERROR);CHECK(p.state==FAILED);
    protocol_init(&p);CHECK(protocol_parse(&p,"OK AI4DOS/0.2 UTF-8",&e)==EV_GREETING);
    for(i=0;i<sizeof(labels)/sizeof(labels[0]);++i){
        p.state=WAIT_BEGIN;sprintf(frame,"BEGIN %s",labels[i]);
        CHECK(protocol_parse(&p,frame,&e)==EV_BEGIN&&e.role==ROLE_AI);
        CHECK(strcmp(e.text,i<6?labels[i]:"")==0);
        CHECK(protocol_parse(&p,"END",&e)==EV_END);
    }
    p.state=WAIT_BEGIN;CHECK(protocol_parse(&p,"BEGIN ",&e)==EV_INVALID);
    CHECK(protocol_parse(&p,"BEGIN Claude\t",&e)==EV_INVALID);
    CHECK(protocol_parse(&p,"BEGIN",&e)==EV_BEGIN&&e.text[0]==0);
    /* Resume is role/session logic; each new BEGIN supplies its own presentation. */
    p.state=READY;CHECK(protocol_expect_resume(&p,"0123456789ab"));
    CHECK(protocol_parse(&p,"OK RESUME",&e)==EV_RESUME);
    CHECK(protocol_expect_reply(&p));CHECK(protocol_parse(&p,"BEGIN Claude",&e)==EV_BEGIN);
    CHECK(strcmp(e.text,"Claude")==0&&e.role==ROLE_AI);
    CHECK(protocol_parse(&p,"END",&e)==EV_END);
    CHECK(protocol_expect_reply(&p));CHECK(protocol_parse(&p,"BEGIN",&e)==EV_BEGIN&&e.text[0]==0);
    puts("AI4DOS CORE PASS");return 0;
}
