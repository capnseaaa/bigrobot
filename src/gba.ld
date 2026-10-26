OUTPUT_ARCH(arm)
ENTRY(_start)

MEMORY {
    rom   : ORIGIN = 0x08000000, LENGTH = 32M
    iwram : ORIGIN = 0x03000000, LENGTH = 32K
    ewram : ORIGIN = 0x02000000, LENGTH = 256K
}

SECTIONS {
    .text : {
        KEEP(*(.crt0))
        *(.text*)
        *(.rodata*)
        . = ALIGN(4);
    } > rom

    .data : {
        __data_start = .;
        *(.iwram*)
        *(.data*)
        . = ALIGN(4);
        __data_end = .;
    } > iwram AT > rom
    __data_lma = LOADADDR(.data);

    /* Only the interrupt handler and its scanline gradient live in fast IWRAM. */
    .bss (NOLOAD) : {
        __bss_start = .;
        *irq.o(.bss* COMMON)
        . = ALIGN(4);
        __bss_end = .;
    } > iwram

    /* Everything else lives in the 256 KB of EWRAM, leaving IWRAM room for the stack. */
    .ewram (NOLOAD) : {
        __ewram_start = .;
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        __ewram_end = .;
    } > ewram

    /DISCARD/ : { *(.ARM.exidx*) *(.ARM.attributes) *(.comment) }
}
