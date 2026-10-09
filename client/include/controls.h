#ifndef AI4DOS_CONTROLS_H
#define AI4DOS_CONTROLS_H
#define CONTROL_NONE 0
#define CONTROL_HANDLED 1
#define CONTROL_EXIT 2
void controls_init(void);
int controls_active(void);
int controls_handle(unsigned key,int busy);
#endif
