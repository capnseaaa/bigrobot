// Interrupt handler (ARM code in IWRAM). VBlank counts frames; HBlank paints the sky gradient
// by changing the backdrop color every scanline.
#include "game.h"

u16 grad[160];
volatile u32 vblanks;
volatile int grad_on;

__attribute__((section(".iwram"), target("arm"), noinline)) void irq_handler(void) {
    u16 f = REG_IF;
    if (f & 2) {
        u32 v = REG_VCOUNT;
        if (grad_on) {
            if (v < 159) BG_PAL[0] = grad[v + 1];
            else if (v == 227) BG_PAL[0] = grad[0];
        }
    }
    if (f & 1) vblanks++;
    REG_IF = f;
    BIOS_IF |= f;
}
