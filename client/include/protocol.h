#ifndef AI4DOS_PROTOCOL_H
#define AI4DOS_PROTOCOL_H
#include "roles.h"
#define WIRE_VERSION "0.3"
#define WIRE_GREETING "OK AI4DOS/" WIRE_VERSION " UTF-8"
#define LINE_CAP 1025
#define DATA_CAP 513

typedef enum { WAIT_GREETING, WAIT_CHALLENGE, WAIT_AUTH, READY, WAIT_SESSION,
               WAIT_RESUME, WAIT_BEGIN, IN_REPLY, WAIT_BYE, FAILED } ProtocolState;
typedef enum { EV_INVALID, EV_GREETING, EV_CHALLENGE, EV_AUTH, EV_SESSION,
               EV_RESUME, EV_BEGIN, EV_DATA, EV_END, EV_ERROR, EV_BYE } EventType;
typedef struct { ProtocolState state; char session[13]; } Protocol;
typedef struct { EventType type; Role role; char text[DATA_CAP]; } Event;
void protocol_init(Protocol *p);
int protocol_expect_session(Protocol *p);
int protocol_expect_resume(Protocol *p,const char *session);
int protocol_expect_reply(Protocol *p);
int protocol_expect_close(Protocol *p);
EventType protocol_parse(Protocol *p, const char *line, Event *e);
#endif
