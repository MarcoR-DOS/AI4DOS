#ifndef AI4DOS_TRANSPORT_H
#define AI4DOS_TRANSPORT_H
#ifdef __cplusplus
extern "C" {
#endif
int mtcp_adapter_start(const char *server,unsigned port);
int mtcp_adapter_pump(void);
int mtcp_adapter_recv(char *buffer,unsigned capacity);
int mtcp_adapter_send(const char *buffer,unsigned length);
unsigned long mtcp_adapter_ticks(void);
void mtcp_adapter_disconnect(void);
void mtcp_adapter_stop(void);
#ifdef __cplusplus
}
#endif
/* Local adapter validation; retain the existing invalid-address code. */
#define NET_START_INVALID_SERVER (-2)
#define NET_START_NO_IP (-8)
#define NET_START_NO_GATEWAY (-9)
/* These line operations pump mTCP while waiting. */
int net_open(const char *server,unsigned port);
int net_start_error(void); /* Last local startup error, or zero for socket failure. */
int net_write(const char *line);
int net_read(char *line,unsigned capacity);
void net_disconnect(void); /* Socket only; retain initialized packet-driver stack. */
void net_close(void);
#endif
