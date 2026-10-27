// The intro (the world is ending, they came from the sky, the bad guys, the robot powers up)
// and the ending (the Mega Robot falls, the crowd cheers, fireworks).
#include "game.h"

#define SQ 0
#define WIDE 1
// sprite VRAM for cutscenes (same places as in a level where they overlap)
enum { T_ROBOT = 0, T_GLASS = 96, T_BOSS = 100, T_ENEMY = 356, T_FX = 404, T_CS = 754 };
enum { PAL_ROBOT, PAL_BOSS, PAL_ENEMY, PAL_FX = 8, PAL_WHITE = 10, PAL_VAR = 12, PAL_CS = 15 };

#define F8X(v) ((v) << 8)
static int imin32(int a, int b) { return a < b ? a : b; }
static int imax32(int a, int b) { return a > b ? a : b; }

static int cs_t, shot, shot_t;
static int skip_hold;   // frames B has been held during the intro

// ---- small effects list: booms and sparks
#define MAX_CFX 16
static struct { u8 on, kind, pal; int x, y, t; } cfx[MAX_CFX];
enum { CK_BOOM, CK_BURST };

static void cfx_add(int kind, int x, int y, int pal) {
    for (int i = 0; i < MAX_CFX; i++)
        if (!cfx[i].on) {
            cfx[i].on = 1;
            cfx[i].kind = kind;
            cfx[i].x = x;
            cfx[i].y = y;
            cfx[i].t = 0;
            cfx[i].pal = pal;
            return;
        }
}

static void cfx_draw(void) {
    for (int i = 0; i < MAX_CFX; i++) {
        if (!cfx[i].on) continue;
        int t = cfx[i].t++;
        if (cfx[i].kind == CK_BOOM) {
            if (t >= 20) { cfx[i].on = 0; continue; }
            spr(cfx[i].x, cfx[i].y, SQ, 2, T_FX + FX_BOOM + (t / 5) * 16, PAL_FX, 0, 0);
        } else {
            if (t >= 28) { cfx[i].on = 0; continue; }
            spr_ex(cfx[i].x - 16, cfx[i].y - 16, SQ, 2, T_CS + CS_BURST + (t / 7) * 16, cfx[i].pal, 0, 1, 0);   // 2x
        }
    }
}

static int shk;
static void cs_shake(void) {
    if (shk > 0) {
        shk--;
        shake_x = rndr(5) - 2;
        shake_y = rndr(5) - 2;
    } else {
        shake_x = shake_y = 0;
    }
}

// typed text: shows the first n letters (n grows with time)
static void typed(int y, const char* s, int t0, int style) {
    int n = (cs_t - t0) / 2;
    if (n < 0) return;
    char b[32];
    int len = 0;
    while (s[len]) len++;
    if (n > len) n = len;
    if (n == 0) return;
    for (int i = 0; i < len; i++) b[i] = i < n ? s[i] : ' ';
    b[len] = 0;
    txt((30 - len) / 2, y, b, style);
    if ((cs_t - t0) % 4 == 0 && n < len && s[n - 1] != ' ') sfx(SFX_SELECT);
}

// ---- the robot: frame tiles, glasses, palette lights (eyes and chest go dark when powered off)
static int robot_shown = -1;
static void robot_frame(int f) {
    if (f == robot_shown) return;
    robot_shown = f;
    upload((void*)(OBJ_TILES + T_ROBOT * 16), &robot_tiles[f * 96 * 8], 96 * 8);
}

static void robot_lights(int on) {
    OBJ_PAL[9] = on ? robot_pal[9] : RGB(7, 2, 2);
    OBJ_PAL[10] = on ? robot_pal[10] : RGB(9, 3, 3);
}

// the robot at 1x: (x, y) = its feet, facing right
static void draw_robot(int x, int y, int f, int glass) {
    int ox = x - 31, oy = y - 95;
    spr(ox + robot_glass_x[f], oy + robot_glass_y[f] - glass, WIDE, 1, T_GLASS, PAL_ROBOT, 0, 0);
    for (int r = 0; r < 3; r++)
        for (int c = 0; c < 2; c++) spr(ox + c * 32, oy + r * 32, SQ, 2, T_ROBOT + (r * 2 + c) * 16, PAL_ROBOT, 0, 0);
}

// the robot at 2x (affine matrix 0): (ox, oy) = top-left of the 128x192 picture
static void draw_robot2(int ox, int oy, int f, int glass) {
    spr_ex(ox + robot_glass_x[f] * 2, oy + (robot_glass_y[f] - glass) * 2, WIDE, 1, T_GLASS, PAL_ROBOT, 0, 1, 0);
    for (int r = 0; r < 3; r++)
        for (int c = 0; c < 2; c++)
            spr_ex(ox + c * 64, oy + r * 64, SQ, 2, T_ROBOT + (r * 2 + c) * 16, PAL_ROBOT, 0, 1, 0);
}

// ---- crowd of little heads
#define HEADS 12
static struct { int x, y; } hd[HEADS];

static void heads_place(int y0) {
    for (int i = 0; i < HEADS; i++) {
        hd[i].x = 6 + i * 19 + rndr(6);
        hd[i].y = y0 + (i & 1) * 12 + rndr(4);
    }
}

// scared: vibrate in place. happy: hop.
static void heads_draw(int happy, int dy) {
    for (int i = 0; i < HEADS; i++) {
        int x = hd[i].x, y = hd[i].y + dy;
        if (happy) {
            int ph = (cs_t * 3 + i * 23) & 63;
            y -= ph < 32 ? ph / 3 : (63 - ph) / 3;
        } else {
            x += rndr(3) - 1;
            y += rndr(3) - 1;
        }
        spr(x, y, SQ, 1, T_CS + CS_HEAD + ((i % 6) * 2 + happy) * 4, PAL_CS, i & 1, 0);
    }
}

static void load_cs_sprites(void) {
    for (int i = 0; i < 16; i++) OBJ_PAL[PAL_CS * 16 + i] = intro_pal[i];
    upload((void*)(OBJ_TILES + T_CS * 16), cs_tiles, sizeof(cs_tiles) / 4);
    upload((void*)(OBJ_TILES + T_FX * 16), fx_tiles, sizeof(fx_tiles) / 4);
}

// ================================================================ intro

enum { SH_CITY, SH_SKY, SH_BAD, SH_POWER, SH_DONE };
static const int shot_len[SH_DONE] = { 300, 270, 380, 420 };

#define MAX_ROCK 6
static struct { u8 on; int x, y; } rock[MAX_ROCK];

#define MAX_MARCH 8
static struct { int x, kind, suit; } march[MAX_MARCH];
static int mega_x;

#define MAX_SPARK 8
static struct { u8 on, side; int t; } spark[MAX_SPARK];

static void shot_enter(int s) {
    shot = s;
    shot_t = 0;
    for (int i = 0; i < MAX_CFX; i++) cfx[i].on = 0;
    txt_clear();
    if (s == SH_CITY) {
        video_screen(SCR_ICITY);
        load_cs_sprites();
        heads_place(118);
        music(SONG_BOSS);
    } else if (s == SH_SKY) {
        video_screen(SCR_EARTH);
        load_cs_sprites();
        for (int i = 0; i < MAX_ROCK; i++) rock[i].on = 0;
    } else if (s == SH_BAD) {
        video_play(6);
        set_theme_pal(6, 0);
        upload((void*)(OBJ_TILES + T_ENEMY * 16), enemy_tiles, sizeof(enemy_tiles) / 4);
        upload((void*)(OBJ_TILES + T_CS * 16), variant_tiles, sizeof(variant_tiles) / 4);
        upload((void*)(OBJ_TILES + T_BOSS * 16), mega_tiles, 256 * 8);
        for (int i = 0; i < 16; i++) OBJ_PAL[16 + i] = mega_pal[i];
        for (int i = 0; i < MAX_MARCH; i++) {
            march[i].x = 250 + i * 34;
            march[i].kind = i % 4;
            march[i].suit = rndr(6);
        }
        mega_x = 300;
    } else if (s == SH_POWER) {
        video_screen(SCR_POWER);
        load_cs_sprites();
        robot_shown = -1;
        robot_frame(RF_STAND);
        upload((void*)(OBJ_TILES + T_GLASS * 16), glasses_tiles, 32);
        robot_lights(0);
        aff_mat(0, 0x80, 0, 0, 0x80);
        for (int i = 0; i < MAX_SPARK; i++) spark[i].on = 0;
        music(SONG_NONE);
    }
}

void intro_enter(void) {
    cs_t = 0;
    skip_hold = 0;
    shk = 0;
    shot_enter(SH_CITY);
}

// pylon arms and cable ends in the power picture (see PYLONS / CABLE_ENDS in make_art.py)
static void cable_point(int side, int t, int* x, int* y) {
    int x0 = side ? 206 : 18, y0 = 28;
    int x1 = side ? 156 : 84, y1 = 90;
    *x = x0 + (x1 - x0) * t / 64;
    *y = y0 + (y1 - y0) * t / 64 + 14 * 4 * t * (64 - t) / (64 * 64);
}

static void intro_shot(void) {
    int t = shot_t;
    switch (shot) {
    case SH_CITY:
        typed(2, "BIG GIANT ROBOT...", 20, 0);
        if (t == 120) txt_big_center(5, "WE NEED YOU!");
        if (t > 120 && t < 124) shk = 6;
        if ((t % 70) == 35) { shk = 8; sfx(SFX_BOOM); }
        heads_draw(0, 0);
        break;
    case SH_SKY:
        typed(2, "THEY CAME FROM THE SKY...", 10, 0);
        if (t % 22 == 0 && t < 220) {
            for (int i = 0; i < MAX_ROCK; i++)
                if (!rock[i].on) {
                    rock[i].on = 1;
                    rock[i].x = F8X(150 + rndr(110));
                    rock[i].y = F8X(-16 - rndr(20));
                    break;
                }
        }
        for (int i = 0; i < MAX_ROCK; i++) {
            if (!rock[i].on) continue;
            rock[i].x -= 400;
            rock[i].y += 380;
            int x = rock[i].x >> 8, y = rock[i].y >> 8;
            int dx = x + 6 - 120, dy = y + 10 - 150;
            if (dx * dx + dy * dy < 76 * 76) {
                rock[i].on = 0;
                cfx_add(CK_BOOM, x - 10, y - 8, 0);
                shk = 8;
                sfx(SFX_BIGBOOM);
                fade(1, 6);
            } else {
                spr(x, y, SQ, 1, T_CS + CS_ROCK + ((cs_t >> 2) & 1) * 4, PAL_FX, 0, 0);
            }
        }
        if ((t & 3) == 2) fade(0, 0);
        break;
    case SH_BAD: {
        typed(2, "DEFEAT THE BAD GUYS...", 10, 0);
        if (t >= 150) typed(4, "AND DESTROY THE MEGA ROBOT!", 150, 0);
        bg_x[1] = t / 2;
        bg_x[2] = t / 4;
        bg_x[3] = t / 8;
        for (int i = 0; i < MAX_MARCH; i++) {
            march[i].x -= (t & 1) ? 1 : 2;
            if (march[i].x < -30) march[i].x += MAX_MARCH * 34;
            int x = march[i].x, y = 152;
            int f = (cs_t >> 3) & 1;
            if (march[i].kind == 0)
                spr(x - 8, y - 32, 2, 2, T_ENEMY + (f ? EF_WALK1 : EF_WALK2) * 8, PAL_ENEMY + march[i].suit, 1, 0);
            else
                spr(x - 16, y - 32, SQ, 2, T_CS + ((march[i].kind - 1) * 3 + f) * 16, PAL_VAR + march[i].kind - 1, 1, 0);
        }
        if (t >= 150) {
            if (mega_x > 170 && (t % 16) == 0) {
                mega_x -= 14;
                shk = 6;
                sfx(SFX_STOMP);
            }
            int pal = (t > 300 && (t & 8)) ? PAL_WHITE : PAL_BOSS;
            for (int r = 0; r < 4; r++)
                for (int c = 0; c < 4; c++)
                    spr(mega_x - 64 + (3 - c) * 32, 150 - 127 + r * 32, SQ, 2, T_BOSS + (r * 4 + c) * 16, pal, 1, 0);
        }
        break;
    }
    case SH_POWER: {
        int ox = 56, oy = 6;
        int glass = 9;
        // power flows down the cables
        if (t < 200 && (t % 7) == 0) {
            for (int i = 0; i < MAX_SPARK; i++)
                if (!spark[i].on) { spark[i].on = 1; spark[i].side = rndr(2); spark[i].t = 0; break; }
        }
        for (int i = 0; i < MAX_SPARK; i++) {
            if (!spark[i].on) continue;
            int x, y;
            cable_point(spark[i].side, spark[i].t, &x, &y);
            spr(x - 8, y - 8, SQ, 1, T_FX + FX_SPARK + ((cs_t >> 1) & 1) * 4, PAL_FX, 0, 0);
            spark[i].t += 2;
            if (spark[i].t > 64) spark[i].on = 0;
        }
        if (t < 200 && (t % 30) == 0) sfx(SFX_LASER);
        // flickers, then the eyes come on
        if (t == 110 || t == 130) robot_lights(1);
        if (t == 114 || t == 134) robot_lights(0);
        if (t == 160) {
            robot_lights(1);
            sfx(SFX_EYE);
            fade(1, 10);
            shk = 10;
        }
        if (t == 163) fade(0, 0);
        if (t == 166) music(SONG_TITLE);
        // head bob: down (glasses drop onto the eyes), then back up
        int bob = 0;
        if (t >= 200 && t < 212) bob = (t - 200);
        else if (t >= 212 && t < 224) bob = 12 - (t - 212);
        if (t >= 200) glass = t < 212 ? 9 - (t - 200) * 9 / 12 : 0;
        draw_robot2(ox, oy + bob, RF_STAND, glass);
        if (t >= 224 && t < 254) {
            int k = (t - 224) / 5;
            int gx = ox + (robot_glass_x[RF_STAND] + 30) * 2 - 16;
            int gy = oy + robot_glass_y[RF_STAND] * 2 - 14;
            spr_ex(gx, gy, SQ, 1, T_CS + CS_KIRA + ((k == 1 || k == 3) ? 4 : 0), PAL_FX, 0, 0, 0);   // 2x, in front
            if (t == 224) sfx(SFX_PICKUP);
        }
        if (t == 270) txt_big_center(17, "LET'S GO!");
        break;
    }
    }
}

// after 3 seconds: "HOLD B TO SKIP" on a dark strip in the bottom right corner
static void skip_prompt(void) {
    for (int x = 14; x <= 29; x++) put_tile(x, 19, HUD_PANEL);
    txt(15, 19, "HOLD B TO SKIP", skip_hold ? 2 : 3);
}

// returns 1 when the intro is over (played through, or B held for a second)
int intro_update(void) {
    cs_t++;
    if (cs_t >= 180) {
        skip_hold = (keys & KEY_B) ? skip_hold + 1 : 0;
        if (skip_hold >= 60) {
            fade(0, 0);
            shake_x = shake_y = 0;
            robot_lights(1);
            return 1;
        }
    }
    shot_t++;
    intro_shot();
    if (cs_t >= 180) skip_prompt();
    cfx_draw();
    cs_shake();
    if (shot_t >= shot_len[shot]) {
        if (shot + 1 >= SH_DONE) {
            robot_lights(1);
            return 1;
        }
        shot_enter(shot + 1);
    }
    return 0;
}

// ================================================================ ending

static int walk_x;

void ending_enter(void) {
    cs_t = 0;
    shk = 0;
    for (int i = 0; i < MAX_CFX; i++) cfx[i].on = 0;
    video_screen(SCR_DAWN);
    // the sky behind the city is the backdrop gradient: night blue to sunrise orange
    static const u16 sk[3] = { RGB(4, 6, 16), RGB(28, 14, 10), RGB(31, 26, 16) };
    for (int y = 0; y < 160; y++) {
        int i = y < 70 ? 0 : 1, f = y < 70 ? y * 32 / 70 : imin32((y - 70) * 32 / 60, 32);
        u16 a = sk[i], b = sk[i + 1];
        int r = ((a & 31) * (32 - f) + (b & 31) * f) >> 5;
        int g = (((a >> 5) & 31) * (32 - f) + ((b >> 5) & 31) * f) >> 5;
        int bl = (((a >> 10) & 31) * (32 - f) + ((b >> 10) & 31) * f) >> 5;
        grad[y] = r | (g << 5) | (bl << 10);
    }
    gradient(1);
    load_cs_sprites();
    upload((void*)(OBJ_TILES + T_BOSS * 16), &mega_tiles[2 * 256 * 8], 256 * 8);
    for (int i = 0; i < 16; i++) OBJ_PAL[16 + i] = mega_pal[i];
    upload((void*)(OBJ_TILES + T_GLASS * 16), glasses_tiles, 32);
    robot_shown = -1;
    robot_lights(1);
    heads_place(132);
    walk_x = -40;
    aff_mat(0, 0x80, 0, 0, 0x80);
    music(SONG_WIN);
}

int ending_update(void) {
    int t = ++cs_t;
    // the Mega Robot goes down behind the city
    if (t < 200) {
        int sink = t < 100 ? 0 : (t - 100) * 3 / 2;
        int pal = (t < 100 && (t & 4)) ? PAL_WHITE : PAL_BOSS;
        for (int r = 0; r < 4; r++)
            for (int c = 0; c < 4; c++)
                spr_ex(110 + (3 - c) * 32, 8 + sink + r * 32, SQ, 2, T_BOSS + (r * 4 + c) * 16, pal, 1, 2, -1);
        if ((t % 9) == 0 && t < 150) {
            cfx_add(CK_BOOM, 110 + rndr(110), 10 + rndr(90) + sink / 2, 0);
            sfx(SFX_BOOM);
            shk = 4;
        }
    }
    if (t == 200) { fade(1, 12); shk = 24; sfx(SFX_BIGBOOM); }
    if (t == 204) fade(0, 0);
    // the Big Giant Robot walks in
    int f = RF_STAND, glass = 0;
    if (t > 210 && walk_x < 120) {
        walk_x++;
        f = RF_WALK1 + ((walk_x >> 3) & 3);
        if ((walk_x & 15) == 0) { shk = 2; sfx(SFX_STOMP); }
    }
    if (t > 340 && t < 360) glass = (t - 340) * 9 / 20;
    else if (t >= 360 && t < 400) glass = 9;
    else if (t >= 400 && t < 410) glass = 9 - (t - 400) * 9 / 10;
    if (t > 210) {
        robot_frame(f);
        draw_robot(walk_x, 144, f, glass);
    }
    if (t >= 410 && t < 440) {
        int k = (t - 410) / 5;
        spr_ex(walk_x - 31 + robot_glass_x[RF_STAND] + 36 - 16, 144 - 95 + robot_glass_y[RF_STAND] - 18, SQ, 1,
               T_CS + CS_KIRA + ((k == 1 || k == 3) ? 4 : 0), PAL_FX, 0, 0, 0);
        if (t == 410) sfx(SFX_PICKUP);
    }
    // the crowd pops up and cheers
    if (t > 300) heads_draw(1, imax32(0, 40 - (t - 300)));
    // fireworks
    if (t > 320 && (t % 12) == 0) {
        cfx_add(CK_BURST, 4 + rndr(204), 10 + rndr(60), PAL_ENEMY + 1 + rndr(5));
        if (rndr(2)) sfx(SFX_BOOM);
    }
    if (t == 330) txt_big_center(1, "YOU SAVED");
    if (t == 350) txt_big_center(4, "THE WORLD!");
    if (t >= 470) typed(7, "THANKS FOR PLAYING!", 470, 1);
    if (t > 560) {
        txt_clear_rows(18, 18);
        if ((t >> 5) & 1) txt_center(18, "PRESS START", 0);
    }
    cfx_draw();
    cs_shake();
    if (t > 560 && (pressed & (KEY_START | KEY_A))) {
        gradient(0);
        return 1;
    }
    return 0;
}
