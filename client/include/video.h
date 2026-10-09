#ifndef AI4DOS_VIDEO_H
#define AI4DOS_VIDEO_H
#define VIDEO_COLS 80
#define VIDEO_ROWS 25
typedef enum { VIDEO_LEGACY, VIDEO_EGA, VIDEO_VGA } VideoAdapter;
typedef struct { unsigned mode,segment,bios_cells; } VideoPlan;
VideoPlan video_plan(unsigned old_mode,VideoAdapter adapter);
int video_init(void);
void video_shutdown(void);
void video_put_cell(unsigned row,unsigned col,unsigned char ch,unsigned char attr);
void video_clear(void);
void video_set_cursor(unsigned row,unsigned col,int visible);
void video_hide_cursor(void);
unsigned video_get_mode(void);
unsigned long video_write_count(void);
#endif
