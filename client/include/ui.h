#ifndef AI4DOS_UI_H
#define AI4DOS_UI_H
#include "roles.h"
#define UI_CHAT_ROWS 18
#define UI_CHAT_WIDTH 76
int ui_init(unsigned codepage);
unsigned ui_codepage(void);
void ui_shutdown(void);
void ui_begin(Role role,const char *label);
void ui_append(const char *text);
void ui_end(void);
typedef enum { UI_CONNECTING, UI_ONLINE, UI_TX_RX, UI_ERROR } UiStatus;
void ui_status(UiStatus status);
UiStatus ui_get_status(void);
const char *ui_status_label(int header);
void ui_error_wait(void);
void ui_busy(int busy);
int ui_input(char *text,int (*poll_network)(void));
int ui_poll_wait(void);
#define UI_SCROLL_UP 1
#define UI_SCROLL_DOWN 2
void ui_clear_chat(void);
void ui_set_session(const char *session);
unsigned ui_scroll_directions(void);
void ui_scroll_lines(int delta);
void ui_scroll_page(int pages);
void ui_help(void);
void ui_info(void);
void ui_save_prompt(const char *name,const char *hint,int editing);
void ui_exit_prompt(void);
void ui_overlay_end(void);
void ui_notice(const char *text);
void ui_clear_notice(void);
const char *ui_label(Role role);
/* Bounded visible-window inspection for tests; not a transcript/export API. */
const char *ui_line(unsigned row);
Role ui_line_role(unsigned row);
#endif
