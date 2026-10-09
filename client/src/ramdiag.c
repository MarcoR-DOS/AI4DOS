/* DOS/8088 measurement-only instrumentation. No allocations or heap resizing. */
#include <stdio.h>
#include <string.h>
#include <dos.h>
#include <malloc.h>
#include "ramdiag.h"
#ifndef AI4DOS_RAM_DIAG
#error Compile ramdiag.c only with AI4DOS_RAM_DIAG
#endif
#define POINTS 8
struct snapshot {
    unsigned seen, alloc_error, alloc_paras, arena_ok, own_blocks;
    unsigned near_status;
    unsigned long free_bytes, largest, owned;
    unsigned long near_used, near_free;
};
static struct snapshot samples[POINTS];
static unsigned base_kb;
static const char *labels[POINTS] = {
    "startup", "config", "mtcp_init", "connected",
    "session", "reply", "pre_cleanup", "post_cleanup"
};
static unsigned heap_sum( unsigned long *used, unsigned long *available)
{
    struct _heapinfo info;
    int status;
    unsigned count = 0;
    info._pentry = NULL;
    *used = *available = 0;
    for (;;) {
        status = _nheapwalk(&info);
        if (status != _HEAPOK) break;
        if (++count > 8192U) return 99;
        if (info._useflag == _USEDENTRY) *used += info._size;
        else *available += info._size;
    }
    return (unsigned)status;
}
static void arena_sum(struct snapshot *s, unsigned psp, unsigned ceiling)
{
    union REGS in, out;
    struct SREGS segs;
    unsigned segment, count = 0;
    unsigned char __far *mcb;
    unsigned owner, paragraphs, type;
    unsigned long next, bytes;
    segread(&segs);
    in.x.ax = 0x5200;
    int86x(0x21, &in, &out, &segs);
    if (out.x.bx < 2) return;
    segment = *(unsigned __far *)MK_FP(segs.es, out.x.bx - 2);
    while (segment < ceiling && ++count <= 4096U) {
        mcb = (unsigned char __far *)MK_FP(segment, 0);
        type = mcb[0];
        if (type != 'M' && type != 'Z') return;
        owner = *(unsigned __far *)(mcb + 1);
        paragraphs = *(unsigned __far *)(mcb + 3);
        next = (unsigned long)segment + paragraphs + 1UL;
        if (next > ceiling || next <= segment) return;
        bytes = (unsigned long)paragraphs * 16UL;
        if (owner == 0) {
            s->free_bytes += bytes;
            if (bytes > s->largest) s->largest = bytes;
        } else if (owner == psp) {
            s->owned += bytes;
            ++s->own_blocks;
        }
        if (type == 'Z' || next == ceiling) { s->arena_ok = 1; return; }
        segment = (unsigned)next;
    }
}
void ram_mark(unsigned point)
{
    struct snapshot *s;
    union REGS in, out;
    unsigned psp;
    if (point >= POINTS) return;
    s = &samples[point];
    memset(s,0,sizeof(*s));
    s->seen = 1;
    int86(0x12, &in, &out);
    base_kb = out.x.ax;
    in.x.ax = 0x5100;
    int86(0x21, &in, &out);
    psp = out.x.bx;
    /* 65535 paragraphs cannot fit in conventional memory. Failure BX is largest.
       DOS may coalesce its existing free blocks while answering this query. */
    in.x.ax = 0x4800;
    in.x.bx = 0xffff;
    int86(0x21, &in, &out);
    if (out.x.cflag) { s->alloc_error = out.x.ax; s->alloc_paras = out.x.bx; }
    else { s->alloc_error = 99; _dos_freemem(out.x.ax); }
    if (base_kb > 0 && base_kb <= 640) arena_sum(s, psp, base_kb * 64U);
    s->near_status = heap_sum(&s->near_used, &s->near_free);
}
void ram_report(void)
{
    unsigned i;
    struct snapshot *s;
    puts("RAM diagnostic v1; all sizes in bytes; no hardware claim");
    printf("RAM BIOS_KB=%u SNAPSHOT_BYTES=%u\n", base_kb, (unsigned)sizeof(samples));
    puts("RAM A: point,arena_ok,alloc_error,alloc_largest,free,largest,owned,blocks");
    puts("RAM H: point,near_status,near_used,near_free");
    for (i = 0; i < POINTS; ++i) {
        s = &samples[i];
        if (!s->seen) continue;
        printf("RAM A,%s,%u,%u,%lu,%lu,%lu,%lu,%u\n", labels[i],
               s->arena_ok, s->alloc_error, (unsigned long)s->alloc_paras * 16UL,
               s->free_bytes, s->largest, s->owned, s->own_blocks);
        printf("RAM H,%s,%u,%lu,%lu\n", labels[i],
               s->near_status, s->near_used, s->near_free);
    }
}
