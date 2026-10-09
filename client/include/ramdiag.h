#ifndef AI4DOS_RAMDIAG_H
#define AI4DOS_RAMDIAG_H
/* Measurement-only build. No code/data/calls in the ordinary release. */
#ifdef AI4DOS_RAM_DIAG
#ifdef __cplusplus
extern "C" {
#endif
void ram_mark(unsigned point);
void ram_report(void);
#ifdef __cplusplus
}
#endif
#else
#define ram_mark(point) ((void)0)
#define ram_report() ((void)0)
#endif
#endif
