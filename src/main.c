// The Big Giant Robot: main loop, video helpers, text, saving, and the menu scenes.
#include "game.h"

void irq_handler(void);

u32 frame;
u16 keys, pressed;
int shake_x, shake_y;
int bg_x[4];
u8 up_lv[U_COUNT];
int level = 1;
u32 squished;
int plv, xp;
int dev_run;                      // level select or dev menu used: do not overwrite the save
u8 dev_sw[DV_COUNT];
int hard;
u32 play_frames;
int bosses_beaten, deaths, worlds;

static u16 oam_buf[512];
static int oam_n;
static int scene;
static int st_t, st_sel;          // per-scene timer and menu cursor
static u32 rng_state = 0x1234567;
static int save_level;            // level stored in the save (0 = no save)
static int dev_max, dev_boss;

const char save_tag[] = "SRAM_V113";

// gcc emits memset/memcpy for array initializers; there is no C library.
void* memset(void* d, int c, unsigned n) {
    u8* p = d;
    while (n--) *p++ = c;
    return d;
}

void* memcpy(void* d, const void* s, unsigned n) {
    u8* p = d;
    const u8* q = s;
    while (n--) *p++ = *q++;
    return d;
}

u32 rnd(void) {
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 17;
    rng_state ^= rng_state << 5;
    return rng_state;
}

int rndr(int n) { return n > 0 ? (int)((rnd() >> 8) % (u32)n) : 0; }
int iabs(int v) { return v < 0 ? -v : v; }
int idiv(int a, int b) { return b ? a / b : 0; }

// ---------------------------------------------------------------- sprites and uploads

void spr_ex(int x, int y, int shape, int size, int tile, int pal, int hf, int prio, int aff) {
    if (oam_n >= 128 || x <= -128 || x >= 240 || y <= -128 || y >= 160) return;
    u16* o = &oam_buf[oam_n * 4];
    o[0] = (y & 255) | (shape << 14) | (aff >= 0 ? 0x300 : 0);
    o[1] = (x & 511) | (size << 14) | (aff >= 0 ? (aff << 9) : (hf << 12));
    o[2] = tile | (prio << 10) | (pal << 12);
    oam_n++;
}

void aff_mat(int i, int pa, int pb, int pc, int pd) {
    oam_buf[i * 16 + 3] = pa;
    oam_buf[i * 16 + 7] = pb;
    oam_buf[i * 16 + 11] = pc;
    oam_buf[i * 16 + 15] = pd;
}

void spr(int x, int y, int shape, int size, int tile, int pal, int hf, int vf) {
    if (oam_n >= 128 || x <= -64 || x >= 240 || y <= -64 || y >= 160) return;
    u16* o = &oam_buf[oam_n * 4];
    o[0] = (y & 255) | (shape << 14);
    o[1] = (x & 511) | (hf << 12) | (vf << 13) | (size << 14);
    o[2] = tile | (1 << 10) | (pal << 12);
    oam_n++;
}

static struct { void* dst; const void* src; int words; } upq[6];
static int upn;

void upload(void* dst, const void* src, int words) {
    if (upn < 6) {
        upq[upn].dst = dst;
        upq[upn].src = src;
        upq[upn].words = words;
        upn++;
    }
}

static void dma32(void* dst, const void* src, int words) {
    REG_DMA3SAD = (u32)src;
    REG_DMA3DAD = (u32)dst;
    REG_DMA3CNT = words | (1u << 26) | (1u << 31);
}

static void fill32(void* dst, u32 v, int words) {
    vu32* d = (vu32*)dst;
    while (words--) *d++ = v;
}

static void vblank_work(void) {
    dma32((void*)OAM, oam_buf, 256);
    for (int i = 0; i < upn; i++) dma32(upq[i].dst, upq[i].src, upq[i].words);
    upn = 0;
    REG_BGHOFS(1) = (bg_x[1] + shake_x) & 511;
    REG_BGHOFS(2) = (bg_x[2] + shake_x / 2) & 511;
    REG_BGHOFS(3) = (bg_x[3]) & 511;
    REG_BGVOFS(1) = shake_y & 511;
    REG_BGVOFS(2) = (shake_y / 2) & 511;
    REG_BGVOFS(3) = 0;
}

static void oam_finish(void) {
    for (int i = oam_n; i < 128; i++) oam_buf[i * 4] = 0x0200;
}

static void vsync(void) { __asm__ volatile("swi 0x05" ::: "r0", "r1", "r2", "r3", "memory"); }

// ---------------------------------------------------------------- text (BG0, screenblock 31)

#define TXT ((vu16*)SCREENBLOCK(31))

void put_tile(int x, int y, u16 t) {
    if (x >= 0 && x < 32 && y >= 0 && y < 32) TXT[y * 32 + x] = t | (15 << 12);
}

void txt_clear(void) { fill32((void*)TXT, 0, 512); }

void txt_clear_rows(int y0, int y1) {
    for (int y = y0; y <= y1; y++)
        for (int x = 0; x < 32; x++) TXT[y * 32 + x] = 0;
}

static int up_char(int c) {
    if (c >= 'a' && c <= 'z') c -= 32;
    if (c < 32 || c > 95) c = 32;
    return c;
}

// styles: 0 chrome/fire, 1 white, 2 chrome/fire on a dark panel, 3 white on a dark panel
void txt(int x, int y, const char* s, int style) {
    for (; *s; s++, x++) {
        int c = up_char(*s) - 32;
        if (style >= 2) put_tile(x, y, FONT_PANEL_BASE + (style - 2) * FONT_PANEL_COUNT + panel_map[c]);
        else put_tile(x, y, style * 64 + c);
    }
}

static int slen(const char* s) {
    int n = 0;
    while (s[n]) n++;
    return n;
}

void txt_center(int y, const char* s, int style) { txt((30 - slen(s)) / 2, y, s, style); }

void txt_big(int x, int y, const char* s) {
    for (; *s; s++, x += 2) {
        int t = FONT_BIG_BASE + big_map[up_char(*s) - 32] * 4;
        put_tile(x, y, t);
        put_tile(x + 1, y, t + 1);
        put_tile(x, y + 1, t + 2);
        put_tile(x + 1, y + 1, t + 3);
    }
}

void txt_big_center(int y, const char* s) { txt_big((30 - slen(s) * 2) / 2, y, s); }

void num_str(char* out, int v) {
    char tmp[12];
    int n = 0;
    if (v < 0) { *out++ = '-'; v = -v; }
    do { tmp[n++] = '0' + v % 10; v /= 10; } while (v);
    while (n) *out++ = tmp[--n];
    *out = 0;
}

// ---------------------------------------------------------------- palettes, fades, video modes

void fade(int mode, int v) {
    if (!mode || v <= 0) {
        REG_BLDCNT = 0;
        return;
    }
    REG_BLDCNT = 0x3F | ((mode == 1 ? 2 : 3) << 6);
    REG_BLDY = v > 16 ? 16 : v;
}

static u16 tint(u16 c, int k) {
    int r = c & 31, g = (c >> 5) & 31, b = (c >> 10) & 31;
    r = r + (31 - r) * k / 20;
    g = g * (16 - k) / 16;
    b = b * (16 - k) / 16;
    return r | (g << 5) | (b << 10);
}

void set_theme_pal(int theme, int red) {
    const u16* p = &theme_pals[theme * 48];
    for (int i = 0; i < 48; i++) BG_PAL[16 + i] = red ? tint(p[i], red) : p[i];
    const u16* sk = &theme_sky[theme * 4];
    for (int y = 0; y < 160; y++) {
        int t = y * 3 * 64 / 159;
        int i = t >> 6, f = t & 63;
        if (i > 2) { i = 2; f = 64; }
        u16 a = sk[i], b = sk[i + 1];
        int r = ((a & 31) * (64 - f) + (b & 31) * f) >> 6;
        int g = (((a >> 5) & 31) * (64 - f) + ((b >> 5) & 31) * f) >> 6;
        int bl = (((a >> 10) & 31) * (64 - f) + ((b >> 10) & 31) * f) >> 6;
        u16 c = r | (g << 5) | (bl << 10);
        grad[y] = red ? tint(c, red) : c;
    }
}

void gradient(int on) {
    grad_on = on;
    REG_IE = on ? 3 : 1;
    if (!on) BG_PAL[0] = 0;
}

static void reset_layers(void) {
    for (int i = 0; i < 4; i++) bg_x[i] = 0;
    shake_x = shake_y = 0;
    fade(0, 0);
}

// Text over black (menus).
static void video_text(void) {
    REG_DISPCNT = 0x80;
    gradient(0);
    reset_layers();
    txt_clear();
    REG_BGCNT(0) = 0x1F0C;
    REG_DISPCNT = 0x0040 | 0x0100 | 0x1000;
}

// A full-screen 8bpp picture on BG2 with text on BG0.
void video_screen(int which) {
    REG_DISPCNT = 0x80;
    gradient(0);
    reset_layers();
    const u32* tiles;
    const u16* map;
    const u16* pal;
    int nt;
    if (which == SCR_TITLE) { tiles = title_tiles; map = title_map; pal = title_pal; nt = sizeof(title_tiles); }
    else if (which == SCR_LAVA) { tiles = lava_tiles; map = lava_map; pal = lava_pal; nt = sizeof(lava_tiles); }
    else if (which == SCR_ICITY) { tiles = icity_tiles; map = icity_map; pal = icity_pal; nt = sizeof(icity_tiles); }
    else if (which == SCR_EARTH) { tiles = earth_tiles; map = earth_map; pal = earth_pal; nt = sizeof(earth_tiles); }
    else if (which == SCR_POWER) { tiles = power_tiles; map = power_map; pal = power_pal; nt = sizeof(power_tiles); }
    else if (which == SCR_DAWN) { tiles = dawn_tiles; map = dawn_map; pal = dawn_pal; nt = sizeof(dawn_tiles); }
    else { tiles = win_tiles; map = win_map; pal = win_pal; nt = sizeof(win_tiles); }
    dma32((void*)CHARBLOCK(0), tiles, nt / 4);
    fill32((void*)SCREENBLOCK(18), 0, 512);
    dma32((void*)SCREENBLOCK(18), map, 32 * 20 / 2);
    for (int i = 0; i < 224; i++) BG_PAL[i] = pal[i];
    txt_clear();
    REG_BGCNT(0) = 0x1F0C;
    REG_BGCNT(2) = 0x1281;   // 8bpp, char block 0, screen block 18 (right after the tiles)
    REG_BGHOFS(2) = 0;
    REG_BGVOFS(2) = 0;
    REG_DISPCNT = 0x0040 | 0x0100 | 0x0400 | 0x1000;
}

// The level: far mountains, city, street, and the HUD text layer.
void video_play(int theme) {
    REG_DISPCNT = 0x80;
    reset_layers();
    dma32((void*)CHARBLOCK(0), level_tiles, sizeof(level_tiles) / 4);
    dma32((void*)SCREENBLOCK(16), map_near, 1024);
    dma32((void*)SCREENBLOCK(18), map_mid, 1024);
    dma32((void*)SCREENBLOCK(20), map_far, 1024);
    set_theme_pal(theme, 0);
    txt_clear();
    REG_BGCNT(0) = 0x1F0C;
    REG_BGCNT(1) = 0x5002;
    REG_BGCNT(2) = 0x5203;
    REG_BGCNT(3) = 0x5403;
    gradient(1);
    REG_DISPCNT = 0x0040 | 0x0F00 | 0x1000;
}

static void load_static(void) {
    dma32((void*)CHARBLOCK(3), font_tiles, sizeof(font_tiles) / 4);
    for (int i = 0; i < 16; i++) BG_PAL[240 + i] = font_pal[i];
    for (int i = 0; i < 16; i++) OBJ_PAL[i] = robot_pal[i];
    for (int i = 0; i < 6 * 16; i++) OBJ_PAL[32 + i] = enemy_pals[i];
    for (int i = 0; i < 16; i++) OBJ_PAL[8 * 16 + i] = fx_pal[i];
    for (int i = 0; i < 16; i++) OBJ_PAL[9 * 16 + i] = proj_pal[i];
    for (int i = 0; i < 3 * 16; i++) OBJ_PAL[12 * 16 + i] = variant_pals[i];
    for (int i = 1; i < 16; i++) OBJ_PAL[10 * 16 + i] = RGB(31, 31, 31);
    // stunned enemies: a cold blue-gray version of the gunmetal suit
    for (int i = 1; i < 16; i++) {
        u16 c = enemy_pals[i];
        int r = c & 31, g = (c >> 5) & 31, b = (c >> 10) & 31;
        int l = (r + g + b) / 3;
        OBJ_PAL[11 * 16 + i] = (l / 2) | ((l * 3 / 4) << 5) | ((l < 21 ? l + 10 : 31) << 10);
    }
}

// ---------------------------------------------------------------- saving (SRAM)

#define SAVE_MAGIC_V1 0x31524742u   // "BGR1" (v0.1.x: level, 7 upgrades, squished)
#define SAVE_MAGIC_V2 0x32524742u   // "BGR2" (adds the Power upgrade, player level and XP)
#define SAVE_MAGIC 0x33524742u      // "BGR3" (adds hard mode and the run stats)
#define SAVE_SIZE 32

static void sram_write(int off, const u8* src, int n) {
    for (int i = 0; i < n; i++) SRAM[off + i] = src[i];
}

static void sram_read(int off, u8* dst, int n) {
    for (int i = 0; i < n; i++) dst[i] = SRAM[off + i];
}

static void put32(u8* b, u32 v) { for (int i = 0; i < 4; i++) b[i] = v >> (8 * i); }
static u32 get32(const u8* b) { return b[0] | (b[1] << 8) | (b[2] << 16) | ((u32)b[3] << 24); }

// v3 layout: magic(4) level(1) upgrades(8) plv(1) xp(2) squished(4)
//            hard(1) frames(4) bosses(2) deaths(2) worlds(2)   (v2 stops after squished)
void save_game(void) {
    if (dev_run) return;
    u8 b[SAVE_SIZE];
    for (int i = 0; i < SAVE_SIZE; i++) b[i] = 0;
    u32 m = SAVE_MAGIC;
    for (int i = 0; i < 4; i++) b[i] = m >> (8 * i);
    b[4] = level;
    for (int i = 0; i < 8; i++) b[5 + i] = i < U_COUNT ? up_lv[i] : 0;
    b[13] = plv;
    b[14] = xp;
    b[15] = xp >> 8;
    put32(b + 16, squished);
    b[20] = hard;
    put32(b + 21, play_frames);
    b[25] = bosses_beaten; b[26] = bosses_beaten >> 8;
    b[27] = deaths; b[28] = deaths >> 8;
    b[29] = worlds; b[30] = worlds >> 8;
    sram_write(0, b, SAVE_SIZE);
    save_level = level;
}

static u32 save_magic(const u8* b) { return get32(b); }

static void load_save(void) {
    u8 b[20];
    sram_read(0, b, 20);
    u32 m = save_magic(b);
    save_level = ((m == SAVE_MAGIC || m == SAVE_MAGIC_V2 || m == SAVE_MAGIC_V1) && b[4] >= 1 && b[4] <= LAST_LEVEL) ? b[4] : 0;
}

static const u8 up_max[U_COUNT] = { 3, 3, 3, 3, 6, 3, 2, 5 };

static void continue_game(void) {
    u8 b[SAVE_SIZE];
    sram_read(0, b, SAVE_SIZE);
    level = b[4];
    hard = 0;
    play_frames = 0;
    bosses_beaten = deaths = worlds = 0;
    if (save_magic(b) == SAVE_MAGIC_V1) {
        // old save: 7 upgrades, then squished at byte 12; no Power, player level or XP yet
        for (int i = 0; i < U_COUNT; i++) up_lv[i] = i < 7 ? b[5 + i] : 0;
        squished = b[12] | (b[13] << 8) | (b[14] << 16) | ((u32)b[15] << 24);
        plv = xp = 0;
    } else {
        for (int i = 0; i < U_COUNT; i++) up_lv[i] = b[5 + i];
        plv = b[13];
        xp = b[14] | (b[15] << 8);
        squished = get32(b + 16);
        if (save_magic(b) == SAVE_MAGIC) {
            hard = b[20] & 1;
            play_frames = get32(b + 21);
            bosses_beaten = b[25] | (b[26] << 8);
            deaths = b[27] | (b[28] << 8);
            worlds = b[29] | (b[30] << 8);
        }
    }
    for (int i = 0; i < U_COUNT; i++)
        if (up_lv[i] > up_max[i]) up_lv[i] = up_max[i];
}

void max_upgrades(void) {
    for (int i = 0; i < U_COUNT; i++) up_lv[i] = up_max[i];
}

static void new_game(void) {
    level = 1;
    for (int i = 0; i < U_COUNT; i++) up_lv[i] = 0;
    squished = 0;
    plv = xp = 0;
    hard = 0;
    play_frames = 0;
    bosses_beaten = deaths = worlds = 0;
    dev_run = 0;
    for (int i = 0; i < DV_COUNT; i++) dev_sw[i] = 0;
}

int xp_need(void) { return 10 + plv * 5; }

// ---------------------------------------------------------------- upgrades

static const char* const up_name[U_COUNT + 1] = { "HAND LASERS", "EYE LASERS", "STOMP", "SLAM", "ARMOR",
                                                  "THUNDERCLAP", "SPEED", "POWER", "REPAIR" };
static const char* const up_desc3[4][3] = {
    { "TWO SHOTS AT ONCE", "FASTER SHOTS", "THREE SHOTS AT ONCE" },
    { "STRONGER BEAM", "COOLS DOWN FASTER", "MEGA BEAM" },
    { "WIDER STOMP", "STOMP SHOCKWAVE", "MEGA STOMP" },
    { "BIGGER SLAM", "FASTER SLAM", "MEGA SLAM" },
};
static const char* const roman[7] = { "", " I", " II", " III", " IV", " V", " VI" };
int up_choice[3], up_count;

static const char* up_desc(int u) {
    if (u < 4) return up_desc3[u][up_lv[u]];
    switch (u) {
    case U_ARMOR: return "+5 MAX HEALTH";
    case U_THUNDER: return "+1 CLAP EVERY LEVEL";
    case U_SPEED: return up_lv[u] ? "WALK EVEN FASTER" : "WALK FASTER";
    case U_POWER: return "+25% DAMAGE TO BOSSES";
    default: return "FULL HEALTH NOW";
    }
}

void pick_upgrades(void) {
    int avail[U_COUNT], n = 0;
    for (int i = 0; i < U_COUNT; i++)
        if (up_lv[i] < up_max[i]) avail[n++] = i;
    up_count = 0;
    while (up_count < 3 && n > 0) {
        int k = rndr(n);
        up_choice[up_count++] = avail[k];
        avail[k] = avail[--n];
    }
    if (up_count < 3) up_choice[up_count++] = U_REPAIR;
}

void draw_upgrade_choices(int y0, int sel, int panel) {
    int p2 = panel ? 2 : 0;
    for (int i = 0; i < up_count; i++) {
        int u = up_choice[i];
        int y = y0 + i * 4;
        char name[24];
        int p = 0;
        for (const char* s = up_name[u]; *s; s++) name[p++] = *s;
        if (u != U_REPAIR)
            for (const char* s = roman[up_lv[u] + 1]; *s; s++) name[p++] = *s;
        name[p] = 0;
        txt(3, y, i == sel ? ">" : " ", p2);
        txt(5, y, "                     ", 1 + p2);
        txt(5, y, name, (i == sel ? 0 : 1) + p2);
        txt(6, y + 2, "                    ", 1 + p2);
        txt(6, y + 2, up_desc(u), 1 + p2);
    }
}

// apply choice sel; returns which upgrade it was (U_REPAIR for a repair)
int take_upgrade(int sel) {
    int u = up_choice[sel];
    if (u != U_REPAIR) up_lv[u]++;
    return u;
}

static void draw_upgrades(void) {
    txt_clear_rows(5, 19);
    draw_upgrade_choices(5, st_sel, 0);
    txt_center(19, "UP/DOWN PICK   A TAKE IT", 1);
}

// ---------------------------------------------------------------- scenes

static void title_text(void) {
    txt_clear_rows(16, 19);
    if (st_sel < 0) return;
    txt(9, 17, st_sel == 0 ? ">" : " ", 0);
    txt(11, 17, "NEW GAME", st_sel == 0 ? 0 : 1);
    if (save_level) {
        char b[20] = "CONTINUE  LV ";
        num_str(b + 13, save_level);
        txt(9, 18, st_sel == 1 ? ">" : " ", 0);
        txt(11, 18, b, st_sel == 1 ? 0 : 1);
        txt(9, 19, st_sel == 2 ? ">" : " ", 0);
        txt(11, 19, "STATS", st_sel == 2 ? 0 : 1);
    }
}

// the stats block is centered: names left-aligned at column 4, values right-aligned to column 25
static void stat_line(int y, const char* name, const char* val) {
    int n = 0;
    while (val[n]) n++;
    txt(4, y, name, 1);
    txt(26 - n, y, val, 0);
}

static void stats_screen(void) {
    char b[16];
    video_text();
    txt_big_center(1, "STATS");
    txt_center(3, hard ? "HARD MODE" : "NORMAL MODE", 1);
    num_str(b, level);
    stat_line(5, "LEVEL", b);
    u32 s = play_frames / 60;
    int h = s / 3600, mi = (s / 60) % 60, se = s % 60;
    num_str(b, h);
    int n = 0;
    while (b[n]) n++;
    b[n++] = ':';
    b[n++] = '0' + mi / 10; b[n++] = '0' + mi % 10;
    b[n++] = ':';
    b[n++] = '0' + se / 10; b[n++] = '0' + se % 10;
    b[n] = 0;
    stat_line(7, "TIME", b);
    num_str(b, squished);
    stat_line(9, "SQUISHED", b);
    num_str(b, bosses_beaten);
    stat_line(11, "BOSSES BEATEN", b);
    num_str(b, plv + 1);
    stat_line(13, "PLAYER LEVEL", b);
    num_str(b, deaths);
    stat_line(15, "ROBOT DOWNS", b);
    num_str(b, worlds);
    stat_line(17, "WORLDS ENDED", b);
    txt_center(19, "PRESS START", 0);
}

void goto_scene(int s) {
    scene = s;
    st_t = 0;
    st_sel = 0;
    switch (s) {
    case SC_TITLE:
        video_screen(SCR_TITLE);
        st_sel = -1;
        music(SONG_TITLE);
        break;
    case SC_HOWTO:
        video_text();
        txt_big_center(1, "HOW TO PLAY");
        txt(3, 4, "D-PAD", 0);  txt(11, 4, "MOVE (YOU MARCH RIGHT)", 1);
        txt(3, 6, "A", 0);      txt(11, 6, "STOMP", 1);
        txt(3, 8, "B", 0);      txt(11, 8, "HAND LASERS", 1);
        txt(3, 10, "R", 0);     txt(11, 10, "EYE LASERS", 1);
        txt(3, 12, "L", 0);     txt(11, 12, "SLAM", 1);
        txt(3, 14, "L + R", 0); txt(11, 14, "THUNDERCLAP", 1);
        txt_center(16, "EYE LASERS ARE FOR BOSSES.", 0);
        txt_center(17, "DO NOT ZAP THE LITTLE GUYS...", 1);
        txt_center(19, "PRESS A", 0);
        break;
    case SC_CARD: {
        video_text();
        music(SONG_NONE);
        save_game();
        char b[16] = "LEVEL ";
        num_str(b + 6, level);
        if (level == LAST_LEVEL) {
            txt_big_center(6, "FINAL LEVEL");
            txt_center(10, "SIX OF THE TOUGHEST BOSSES", 1);
            txt_center(11, "ARE BACK", 1);
            txt_center(13, "THEN THE MEGA ROBOT!", 0);
        } else {
            txt_big_center(6, b);
            txt_center(10, theme_names[(level - 1) / 3 < THEME_COUNT ? (level - 1) / 3 : THEME_COUNT - 1], 0);
        }
        if (hard) txt_center(15, "HARD MODE", 1);
        break;
    }
    case SC_PLAY:
        play_enter();
        break;
    case SC_UPGRADE:
        video_text();
        music(SONG_NONE);
        txt_big_center(1, "UPGRADE!");
        pick_upgrades();
        draw_upgrades();
        break;
    case SC_LAVA:
        video_screen(SCR_LAVA);
        music(SONG_LAVA);
        fade(1, 16);
        break;
    case SC_GAMEOVER:
        video_text();
        music(SONG_NONE);
        txt_big_center(6, "ROBOT DOWN");
        txt_center(11, "A   TRY AGAIN", 0);
        txt_center(13, "B   TITLE   ", 1);
        break;
    case SC_WIN:
        save_game();   // keep the finished run's stats
        ending_enter();
        break;
    case SC_INTRO:
        intro_enter();
        break;
    case SC_MODE:
        video_text();
        txt_big_center(2, "PICK A MODE");
        break;
    case SC_STATS:
        stats_screen();
        break;
    case SC_DEV:
        video_text();
        txt_big_center(1, "LEVEL SELECT");
        st_sel = 1;
        dev_max = 0;
        dev_boss = 0;
        break;
    }
}

static void scene_update(void) {
    st_t++;
    switch (scene) {
    case SC_TITLE:
        if (st_sel < 0) {
            txt_clear_rows(17, 17);
            if ((st_t >> 5) & 1) txt_center(17, "PRESS START", 0);
            if (pressed & (KEY_START | KEY_A)) {
                st_sel = save_level ? 1 : 0;
                sfx(SFX_SELECT);
                title_text();
            }
        } else {
            if ((pressed & (KEY_UP | KEY_DOWN)) && save_level) {
                st_sel = (st_sel + ((pressed & KEY_UP) ? 2 : 1)) % 3;
                sfx(SFX_SELECT);
                title_text();
            }
            if (pressed & (KEY_START | KEY_A)) {
                sfx(SFX_SELECT);
                if (st_sel == 1) {
                    continue_game();
                    goto_scene(SC_CARD);
                } else if (st_sel == 2) {
                    continue_game();
                    goto_scene(SC_STATS);
                } else {
                    goto_scene(SC_MODE);
                }
                return;
            }
        }
        if ((keys & (KEY_L | KEY_R)) == (KEY_L | KEY_R) && (pressed & KEY_SELECT)) goto_scene(SC_DEV);
        break;
    case SC_HOWTO:
        if (st_t > 20 && (pressed & (KEY_A | KEY_START))) goto_scene(SC_CARD);
        break;
    case SC_CARD:
        if (st_t > 150 || (st_t > 20 && (pressed & (KEY_A | KEY_START)))) goto_scene(SC_PLAY);
        break;
    case SC_MODE:
        if (st_t == 1 || (pressed & (KEY_UP | KEY_DOWN))) {
            if (st_t > 1) { st_sel ^= 1; sfx(SFX_SELECT); }
            txt_clear_rows(6, 17);
            txt(5, 7, st_sel == 0 ? ">" : " ", 0);
            txt(7, 7, "NORMAL", st_sel == 0 ? 0 : 1);
            txt(9, 9, "THE GAME AS IT IS", 1);
            txt(5, 12, st_sel == 1 ? ">" : " ", 0);
            txt(7, 12, "HARD", st_sel == 1 ? 0 : 1);
            txt(9, 14, "TOUGHER BOSSES,", 1);
            txt(9, 15, "MORE ENEMIES,", 1);
            txt(9, 16, "HITS HURT MORE", 1);
            txt_center(18, "UP/DOWN PICK   A GO", 1);
        }
        if (st_t > 10 && (pressed & (KEY_A | KEY_START))) {
            new_game();
            hard = st_sel;
            sfx(SFX_SELECT);
            goto_scene(SC_HOWTO);
        }
        if (pressed & KEY_B) goto_scene(SC_TITLE);
        break;
    case SC_STATS:
        if (st_t > 30 && (pressed & (KEY_START | KEY_A | KEY_B))) goto_scene(SC_TITLE);
        break;
    case SC_PLAY: {
        play_frames++;
        int ev = play_update();
        if (ev == EV_CLEAR) goto_scene(SC_UPGRADE);
        else if (ev == EV_DEAD) goto_scene(SC_GAMEOVER);
        else if (ev == EV_BOOM) goto_scene(SC_LAVA);
        else if (ev == EV_WIN) goto_scene(SC_WIN);
        else if (ev == EV_GOTO) goto_scene(SC_CARD);
        break;
    }
    case SC_UPGRADE:
        if (pressed & KEY_UP) { st_sel = (st_sel + up_count - 1) % up_count; sfx(SFX_SELECT); draw_upgrades(); }
        if (pressed & KEY_DOWN) { st_sel = (st_sel + 1) % up_count; sfx(SFX_SELECT); draw_upgrades(); }
        if (st_t > 20 && (pressed & KEY_A)) {
            take_upgrade(st_sel);
            sfx(SFX_PICKUP);
            level++;
            goto_scene(SC_CARD);
        }
        break;
    case SC_LAVA: {
        if (st_t <= 32) fade(1, 16 - st_t / 2);
        // the lava flows: rotate its color band
        if ((st_t & 3) == 0) {
            int b = LAVA_LAVA_BASE;
            u16 first = BG_PAL[b];
            for (int i = 0; i < 11; i++) BG_PAL[b + i] = BG_PAL[b + i + 1];
            BG_PAL[b + 11] = first;
        }
        if (st_t == 61 || (st_t > 61 && (pressed & (KEY_UP | KEY_DOWN)))) {
            if (st_t > 61) { st_sel ^= 1; sfx(SFX_SELECT); }
            for (int y = 15; y <= 19; y++)
                for (int x = 3; x <= 26; x++) put_tile(x, y, y == 15 ? HUD_PANEL_TOP : y == 19 ? HUD_PANEL_BOT : HUD_PANEL);
            txt(5, 16, st_sel == 0 ? ">" : " ", 2);
            txt(7, 16, "KEEP UPGRADES, LEVEL 1", st_sel == 0 ? 2 : 3);
            txt(5, 18, st_sel == 1 ? ">" : " ", 2);
            txt(7, 18, "START OVER", st_sel == 1 ? 2 : 3);
        }
        if (st_t > 61 && (pressed & (KEY_A | KEY_START))) {
            if (st_sel == 1) {
                // start over keeps the mode and the count of worlds ended
                int h = hard, w = worlds;
                new_game();
                hard = h;
                worlds = w;
            } else level = 1;
            sfx(SFX_SELECT);
            goto_scene(SC_CARD);
        }
        break;
    }
    case SC_GAMEOVER:
        if (st_t > 30 && (pressed & KEY_A)) goto_scene(SC_CARD);
        if (st_t > 30 && (pressed & KEY_B)) goto_scene(SC_TITLE);
        break;
    case SC_WIN:
        if (ending_update()) goto_scene(SC_STATS);
        break;
    case SC_INTRO:
        if (intro_update()) goto_scene(SC_TITLE);
        break;
    case SC_DEV: {
        if (pressed & KEY_UP) st_sel = st_sel % LAST_LEVEL + 1;
        if (pressed & KEY_DOWN) st_sel = (st_sel + LAST_LEVEL - 2) % LAST_LEVEL + 1;
        if (pressed & KEY_L) dev_max ^= 1;
        if (pressed & KEY_R) dev_boss ^= 1;
        char b[16] = "LEVEL ";
        num_str(b + 6, st_sel);
        txt_clear_rows(6, 16);
        txt_big_center(7, b);
        txt_center(11, dev_max ? "L  UPGRADES: ALL MAXED" : "L  UPGRADES: NONE     ", 1);
        txt_center(12, dev_boss ? "R  ENEMIES: OFF, BOSSES ONLY" : "R  ENEMIES: ON              ", 1);
        txt_center(14, "UP/DOWN   A START   B BACK", 1);
        if (pressed & KEY_A) {
            new_game();
            level = st_sel;
            dev_run = 1;
            dev_sw[DV_NOENEMY] = dev_boss;
            if (dev_max) max_upgrades();
            goto_scene(SC_CARD);
        }
        if (pressed & KEY_B) goto_scene(SC_TITLE);
        break;
    }
    }
}

int main(void) {
    REG_WAITCNT = 0x4317;
    REG_DISPCNT = 0x80;
    IRQ_VECTOR = (u32)irq_handler;
    REG_DISPSTAT = (1 << 3) | (1 << 4);
    REG_IE = 1;
    REG_IME = 1;
    load_static();
    snd_init();
    load_save();
    (void)*(volatile const char*)save_tag;
    goto_scene(SC_INTRO);
    for (;;) {
        vsync();
        vblank_work();
        frame++;
        u16 k = ~REG_KEYINPUT & 0x3FF;
        pressed = k & ~keys;
        keys = k;
        rng_state += k;
        oam_n = 0;
        scene_update();
        oam_finish();
        snd_tick();
    }
}
