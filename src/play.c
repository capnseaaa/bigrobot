// The level: the robot, the little War Machine guys, bosses, lasers, pickups, and the end of the world.
#include "game.h"

void video_play(int theme);

#define GY GROUND_Y
#define F8(v) ((v) << 8)
// the street is a depth band: everything stands on its own lane (feet y) between these
#define LANE_TOP 140
#define LANE_BOT 158

// sprite VRAM (4bpp tile numbers) and OBJ palette banks
enum { T_ROBOT = 0, T_GLASS = 96, T_BOSS = 100, T_ENEMY = 356, T_FX = 404 };
#define T_PROJ (T_FX + FX_TILE_COUNT)
enum { PAL_ROBOT, PAL_BOSS, PAL_ENEMY, PAL_FX = 8, PAL_PROJ, PAL_WHITE, PAL_STUN };

// sprite shapes/sizes
#define SQ 0
#define WIDE 1
#define TALL 2

// ---------------------------------------------------------------- state

enum { PH_WALK, PH_WARN, PH_BOSS, PH_CLEAR, PH_RUSHGAP, PH_DEAD, PH_BOOM };
static int phase, phase_t, cam, level_len, theme, spawn_t, next_heart, rush_i, paused, boom_t;
static int shake_t, shake_m;
static const char* banner;
static const char* banner2;
static int banner_t;
static int level_squish;
static int lvlup, lvl_sel;      // level-up popup showing, and its cursor
static int dev_open, dev_sel, dev_lv;  // dev menu (L+R+B)
static int lightning_t;
#define MAX_WX 12
static struct { s16 x, y; } wx[MAX_WX];   // weather particles (screen space)

enum { RS_FREE, RS_STOMP, RS_SLAM, RS_CLAP, RS_EYE, RS_DEAD };
static struct {
    int x, y, gy, vy, face, hp, maxhp, st, t, walk, moving, fire_cd, eye_cd, slam_cd, claps, inv, glass;
    int frame, shoot_t, hurt_t, pend_l, pend_r;
} R;
static int shown_frame;

#define MAX_EN 12
enum { ES_OFF, ES_LIVE, ES_SQUISH, ES_FLEE };
typedef struct {
    u8 st, fly, suit, hit;
    int x, y, gy, spd, keep, t, stun, cd, anim, hover, shoot;
} Enemy;
static Enemy en[MAX_EN];

#define MAX_SHOT 32
enum { OWN_BOLT, OWN_BULLET, OWN_BOSS, OWN_MARK, OWN_WAVE };
typedef struct {
    u8 on, own, kind, grav;
    int x, y, gy, vx, vy, life, dmg, t;
} Shot;
static Shot sh[MAX_SHOT];

#define MAX_FX 18
enum { K_BOOM, K_POP, K_SPARK, K_DUST, K_PUFF, K_FLASH };
typedef struct {
    u8 on, kind;
    int x, y, vx, t;
} Fx;
static Fx fx[MAX_FX];

#define MAX_PK 4
enum { PK_HEART, PK_CELL };
typedef struct {
    u8 on, kind;
    int x, y, gy, vy, t;
} Pickup;
static Pickup pk[MAX_PK];

enum { A_SHOT, A_FAN, A_LOB, A_RAIN, A_CHARGE, A_JUMP, A_BEAM };
typedef struct {
    u8 atk[3];
    u8 proj, beam, speed;
} BossDef;
static const BossDef bdef[BOSS_COUNT + 1] = {
    { { A_CHARGE, A_SHOT, A_CHARGE }, PJ_RIVET, PJ_RIVET, 2 },   // IRON MAULER
    { { A_SHOT, A_CHARGE, A_FAN }, PJ_SAW, PJ_SAW, 3 },          // SAWBLADE
    { { A_BEAM, A_LOB, A_SHOT }, PJ_FIRE, PJ_FIRE, 2 },          // BLAZE HORN
    { { A_FAN, A_RAIN, A_SHOT }, PJ_SPIKE, PJ_SPIKE, 2 },        // SPIKE GUY
    { { A_SHOT, A_RAIN, A_FAN }, PJ_ELEC, PJ_ELEC, 3 },          // VOLT SKULL
    { { A_LOB, A_SHOT, A_JUMP }, PJ_MISSILE, PJ_FIRE, 3 },       // ROCKET RAVEN
    { { A_JUMP, A_CHARGE, A_SHOT }, PJ_ROCK, PJ_ROCK, 2 },       // CHROME CRUSHER
    { { A_LOB, A_BEAM, A_RAIN }, PJ_FIRE, PJ_FIRE, 2 },          // MAGMA MAW
    { { A_FAN, A_SHOT, A_CHARGE }, PJ_ICE, PJ_ICE, 3 },          // FROST FANG
    { { A_LOB, A_RAIN, A_SHOT }, PJ_ACID, PJ_ACID, 2 },          // VENOM VAT
    { { A_CHARGE, A_JUMP, A_FAN }, PJ_ROCK, PJ_ROCK, 3 },        // DOOM DRILL
    { { A_SHOT, A_CHARGE, A_RAIN }, PJ_SCYTHE, PJ_SCYTHE, 3 },   // GRIM REAPER
    { { A_FAN, A_BEAM, A_SHOT }, PJ_NOTE, PJ_SOUND, 3 },         // HEAVY METAL
    { { A_CHARGE, A_JUMP, A_FAN }, PJ_RIVET, PJ_RIVET, 3 },      // STEEL TITAN
    { { A_FAN, A_RAIN, A_CHARGE }, PJ_ICE, PJ_ICE, 1 },          // BLIZZARD BEAST
    { { A_SHOT, A_CHARGE, A_JUMP }, PJ_SHURIKEN, PJ_SHURIKEN, 3 }, // NEON NINJA
    { { A_LOB, A_RAIN, A_SHOT }, PJ_ROCK, PJ_ROCK, 1 },          // SCRAP KING
    { { A_SHOT, A_BEAM, A_FAN }, PJ_LASER, PJ_LASER, 2 },        // CYCLOPS
    { { A_BEAM, A_LOB, A_JUMP }, PJ_FIRE, PJ_FIRE, 2 },          // DRAGON-X
    { { A_JUMP, A_CHARGE, A_RAIN }, PJ_FIRE, PJ_FIRE, 2 },       // INFERNO KING
    { { A_FAN, A_RAIN, A_JUMP }, PJ_MISSILE, PJ_FIRE, 3 },       // MEGA ROBOT
};

enum { BS_ENTER, BS_MOVE, BS_TELE, BS_ATK, BS_DIE };
static struct {
    int on, id, mega, st, t, x, y, gy, vx, vy, face, hp, maxhp, cd, stun, flash, atk, atk_i, frame, shown;
    int air;
} B;

// upgrade tables (index = upgrade level)
static const u8 hand_cd[4] = { 14, 14, 9, 9 };
static const u8 hand_n[4] = { 1, 2, 2, 3 };
static const u8 eye_dmg[4] = { 2, 3, 3, 4 };
static const u8 eye_cool[4] = { 110, 100, 60, 60 };
static const u8 eye_len[4] = { 48, 48, 48, 64 };
static const u8 stomp_w[4] = { 32, 44, 56, 70 };
static const u8 stomp_dmg[4] = { 5, 7, 9, 12 };
static const u8 slam_r[4] = { 80, 100, 120, 150 };
static const u8 slam_dmg[4] = { 10, 13, 16, 20 };
static const u8 slam_cool[4] = { 150, 150, 100, 80 };
static const u16 walk_spd[3] = { 320, 384, 448 };

// ---------------------------------------------------------------- helpers

static int sgn(int v) { return v > 0 ? 1 : v < 0 ? -1 : 0; }
static int imin(int a, int b) { return a < b ? a : b; }
static int imax(int a, int b) { return a > b ? a : b; }
static int near_lane(int a, int b, int tol) { return iabs(a - b) <= tol; }

static void shake(int t, int m) {
    if (t > shake_t) shake_t = t;
    if (m > shake_m) shake_m = m;
}

// velocity (8.8 fixed) from (x0,y0) toward (x1,y1) in pixels, speed in 1/256 px per frame
static void aim(int x0, int y0, int x1, int y1, int speed, int* vx, int* vy) {
    int dx = x1 - x0, dy = y1 - y0;
    int ax = iabs(dx), ay = iabs(dy);
    int len = ax > ay ? ax + ay * 3 / 8 : ay + ax * 3 / 8;
    if (len < 1) len = 1;
    *vx = idiv(dx * speed, len);
    *vy = idiv(dy * speed, len);
}

static int boxes(int ax0, int ay0, int ax1, int ay1, int bx0, int by0, int bx1, int by1) {
    return ax0 <= bx1 && bx0 <= ax1 && ay0 <= by1 && by0 <= ay1;
}

static void fx_add(int kind, int x, int y, int vx) {
    for (int i = 0; i < MAX_FX; i++)
        if (!fx[i].on) {
            fx[i].on = 1;
            fx[i].kind = kind;
            fx[i].x = x;
            fx[i].y = y;
            fx[i].vx = vx;
            fx[i].t = 0;
            return;
        }
}

static Shot* shot_new(int own) {
    for (int i = 0; i < MAX_SHOT; i++)
        if (!sh[i].on) {
            Shot* s = &sh[i];
            s->on = 1;
            s->own = own;
            s->kind = 0;
            s->grav = 0;
            s->vx = s->vy = 0;
            s->life = 600;
            s->dmg = 1;
            s->t = 0;
            s->gy = LANE_BOT + 4;
            return s;
        }
    return 0;
}

static void pickup_add(int kind, int x, int y, int gy) {
    for (int i = 0; i < MAX_PK; i++)
        if (!pk[i].on) {
            pk[i].on = 1;
            pk[i].kind = kind;
            pk[i].x = x;
            pk[i].y = F8(y);
            pk[i].gy = gy;
            pk[i].vy = 0;
            pk[i].t = 0;
            return;
        }
}

static void set_banner(const char* a, const char* b, int t) {
    banner = a;
    banner2 = b;
    banner_t = t;
    txt_clear_rows(7, 12);
}

// robot box in world pixels
static void robot_box(int* x0, int* y0, int* x1, int* y1) {
    int x = R.x >> 8, y = R.y >> 8;
    *x0 = x - 15;
    *x1 = x + 15;
    *y0 = y - (R.st == RS_SLAM && R.frame == RF_CROUCH ? 72 : 82);
    *y1 = y;
}

static void boss_box(int* x0, int* y0, int* x1, int* y1) {
    int hw = B.mega ? 34 : 20, h = B.mega ? 112 : 66;
    int x = B.x >> 8, y = B.y >> 8;
    *x0 = x - hw;
    *x1 = x + hw;
    *y0 = y - h;
    *y1 = y;
}

static void enemy_box(Enemy* e, int* x0, int* y0, int* x1, int* y1) {
    int x = e->x >> 8, y = e->y >> 8;
    *x0 = x - 7;
    *x1 = x + 7;
    *y0 = y - (e->fly ? 21 : 23);
    *y1 = y;
}

static void hurt(int n) {
    if (R.inv || R.st == RS_DEAD || phase == PH_BOOM || phase == PH_CLEAR || dev_sw[DV_GOD]) return;
    if (hard) n += (n + 1) / 2;
    R.hp -= n;
    R.inv = 60;
    R.hurt_t = 12;
    sfx(SFX_HURT);
    shake(8, 2);
    if (R.hp <= 0) {
        R.hp = 0;
        R.st = RS_DEAD;
        R.t = 0;
        deaths++;
        phase = PH_DEAD;
        phase_t = 0;
    }
}

// ---------------------------------------------------------------- boss

static void boss_frame_upload(void) {
    if (B.frame == B.shown) return;
    B.shown = B.frame;
    if (B.mega) upload((void*)(OBJ_TILES + T_BOSS * 16), &mega_tiles[B.frame * 256 * 8], 256 * 8);
    else upload((void*)(OBJ_TILES + T_BOSS * 16), &boss_tiles[(B.id * 3 + B.frame) * 96 * 8], 96 * 8);
}

static void boss_start(int id) {
    B.on = 1;
    B.id = id;
    B.mega = id == MEGA_ID;
    B.st = BS_ENTER;
    B.t = 0;
    B.x = F8(cam + 290);
    B.gy = R.gy;
    B.y = F8(B.gy);
    B.vx = B.vy = 0;
    B.face = -1;
    if (B.mega) B.maxhp = 700;
    else if (level == LAST_LEVEL) B.maxhp = (60 + 13 * (id + 1)) / 2;
    else B.maxhp = 60 + 13 * level;
    if (hard) B.maxhp += B.maxhp / 2;
    B.hp = B.maxhp;
    B.cd = 60;
    B.stun = 0;
    B.flash = 0;
    B.atk_i = 0;
    B.air = 0;
    B.frame = 0;
    B.shown = -1;
    const u16* p = B.mega ? mega_pal : &boss_pals[id * 16];
    for (int i = 0; i < 16; i++) OBJ_PAL[16 + i] = p[i];
    boss_frame_upload();
}

static void gain_xp(int n) {
    if (level == LAST_LEVEL && plv > 40) return;
    xp += n;
}

static void boss_damage(int n) {
    if (!B.on || B.st == BS_DIE || B.st == BS_ENTER) return;
    n = dev_sw[DV_ONEHIT] ? B.hp : n * (4 + up_lv[U_POWER]) / 4;
    B.hp -= n;
    B.flash = 4;
    if (B.hp <= 0) {
        B.hp = 0;
        B.st = BS_DIE;
        B.t = 0;
        B.vx = B.vy = 0;
        sfx(SFX_BIGBOOM);
        gain_xp(B.mega ? 20 : 10);
        bosses_beaten++;
    }
}

static void boss_proj(int x, int y, int vx, int vy, int kind, int grav, int life, int dmg) {
    Shot* s = shot_new(OWN_BOSS);
    if (!s) return;
    s->x = F8(x);
    s->y = F8(y);
    s->vx = vx;
    s->vy = vy;
    s->kind = kind;
    s->grav = grav;
    s->life = life;
    s->dmg = dmg;
}

static const s16 fan_c[7] = { 197, 222, 247, 256, 247, 222, 197 };
static const s16 fan_s[7] = { -165, -128, -66, 0, 66, 128, 165 };

static void boss_attack_start(void) {
    const BossDef* d = &bdef[B.mega ? MEGA_ID : B.id];
    if (B.mega) {
        static const u8 cyc[7] = { A_FAN, A_SHOT, A_RAIN, A_CHARGE, A_LOB, A_JUMP, A_BEAM };
        B.atk = cyc[B.atk_i % 7];
    } else {
        B.atk = d->atk[B.atk_i % 3];
    }
    B.atk_i++;
    B.st = BS_TELE;
    B.t = (B.atk == A_CHARGE) ? 34 : (B.atk == A_JUMP) ? 18 : 26;
    if (level >= 10 && B.t > 18) B.t -= 6;
    sfx(SFX_WARN);
}

static void boss_update(void) {
    if (!B.on) return;
    const BossDef* d = &bdef[B.mega ? MEGA_ID : B.id];
    int bx = B.x >> 8, by = B.y >> 8;
    int rx = R.x >> 8;
    int hand_x = bx + B.face * (B.mega ? 40 : 22), hand_y = by - (B.mega ? 64 : 40);
    if (B.flash) B.flash--;
    if (B.st == BS_DIE) {
        B.t++;
        B.frame = 2;
        if ((B.t % 6) == 0) {
            int x0, y0, x1, y1;
            boss_box(&x0, &y0, &x1, &y1);
            fx_add(K_BOOM, x0 + rndr(x1 - x0) - 16, y0 + rndr(y1 - y0) - 16, 0);
            sfx(SFX_BOOM);
            shake(6, 3);
        }
        if (B.t >= 100) {
            B.on = 0;
            for (int i = 0; i < 6; i++) fx_add(K_BOOM, bx - 30 + rndr(44), by - 60 + rndr(44), 0);
            pickup_add(PK_CELL, bx, B.gy - 60, B.gy);
            shake(20, 4);
        }
        boss_frame_upload();
        return;
    }
    if (B.stun) {
        B.stun--;
        if (B.air) B.stun = imax(B.stun, 1);
    }
    if (B.st == BS_ENTER) {
        B.x -= 256;
        B.frame = (B.t >> 4) & 1;
        B.t++;
        if (bx <= cam + (B.mega ? 175 : 185)) {
            B.st = BS_MOVE;
            B.cd = 50;
        }
        boss_frame_upload();
        return;
    }
    // gravity / airborne (jumps)
    if (B.air) {
        B.vy += B.mega ? 60 : 72;
        B.x += B.vx;
        B.y += B.vy;
        if (B.y >= F8(B.gy)) {
            B.y = F8(B.gy);
            B.air = 0;
            B.vx = 0;
            shake(14, 4);
            sfx(SFX_SLAM);
            for (int dir = -1; dir <= 1; dir += 2) {
                Shot* s = shot_new(OWN_WAVE);
                if (s) {
                    s->x = B.x + dir * F8(B.mega ? 30 : 16);
                    s->y = F8(B.gy);
                    s->gy = B.gy;
                    s->vx = dir * 3 * 256;
                    s->life = 45;
                    s->dmg = 2;
                }
            }
            if (B.st == BS_ATK) {
                B.st = BS_MOVE;
                B.cd = 40 + rndr(30);
            }
        }
    }
    int lo = cam + (B.mega ? 40 : 26), hi = cam + (B.mega ? 200 : 214);
    if (B.stun && !B.air) {
        boss_frame_upload();
        return;
    }
    int dx = rx - bx;
    if (B.st != BS_ATK || B.atk != A_CHARGE) B.face = dx >= 0 ? 1 : -1;
    int speed = 72 + d->speed * 26;   // side to side: about 0.4 to 0.6 px per frame
    switch (B.st) {
    case BS_MOVE: {
        int dist = iabs(dx);
        int moving = 0;
        if (dist > 115) { B.x += sgn(dx) * speed; moving = 1; }
        else if (dist < 60) { B.x -= sgn(dx) * speed; moving = 1; }
        // drift toward the robot's lane
        if (B.gy < R.gy && (B.t % 3) == 0) { B.gy++; B.y += 256; moving = 1; }
        if (B.gy > R.gy && (B.t % 3) == 0) { B.gy--; B.y -= 256; moving = 1; }
        B.t++;
        B.frame = moving ? ((B.t >> 4) & 1) : 0;
        if (--B.cd <= 0) boss_attack_start();
        break;
    }
    case BS_TELE:
        B.frame = 2;
        if (--B.t <= 0) {
            B.st = BS_ATK;
            B.t = 0;
            if (B.atk == A_CHARGE) {
                B.vx = B.face * (B.mega ? 4 : 3) * 256;
                sfx(SFX_SLAM);
            } else if (B.atk == A_JUMP) {
                B.air = 1;
                B.vy = -(B.mega ? 6 : 7) * 256;
                B.vx = idiv((rx - bx) * 256, 64);
            }
        }
        break;
    case BS_ATK: {
        int t = B.t++;
        int done = 0;
        B.frame = 2;
        switch (B.atk) {
        case A_SHOT: {
            int n = 1 + (level >= 6) + (level >= 11) + B.mega;
            if (t % 12 == 0 && t / 12 < n) {
                int vx, vy;
                aim(hand_x, hand_y, rx, (R.y >> 8) - 45, B.mega ? 900 : 760, &vx, &vy);
                boss_proj(hand_x, hand_y, vx, vy, B.mega ? PJ_MISSILE : d->proj, 0, 200, 2);
                sfx(SFX_HIT);
            }
            done = t >= n * 12 + 8;
            break;
        }
        case A_FAN:
            if (t == 0 || (B.mega && t == 20)) {
                int vx, vy;
                aim(hand_x, hand_y, rx, (R.y >> 8) - 40, 620, &vx, &vy);
                int lo2 = (level >= 10 || B.mega) ? 0 : 1, hi2 = (level >= 10 || B.mega) ? 7 : 6;
                for (int k = lo2; k < hi2; k++) {
                    int c = fan_c[k], s = fan_s[k];
                    boss_proj(hand_x, hand_y, (vx * c - vy * s) >> 8, (vx * s + vy * c) >> 8,
                              B.mega ? PJ_SPIKE : d->proj, 0, 200, 2);
                }
                sfx(SFX_HIT);
            }
            done = t >= (B.mega ? 40 : 22);
            break;
        case A_LOB:
            if (t == 0 || t == 15 || t == 30) {
                int tx = rx + (t == 0 ? 0 : t == 15 ? -30 : 30);
                int vx = idiv((tx - hand_x) * 256, 50);
                boss_proj(hand_x, hand_y - 6, vx, -1000, B.mega ? PJ_MISSILE : d->proj, 40, 200, 2);
                for (int q = 0; q < MAX_SHOT; q++)
                    if (sh[q].on && sh[q].own == OWN_BOSS && sh[q].t == 0 && sh[q].grav) sh[q].gy = R.gy;
                sfx(SFX_HIT);
            }
            done = t >= 40;
            break;
        case A_RAIN:
            if (t == 0) {
                static const s8 off[5] = { -60, -30, 0, 30, 60 };
                int n = B.mega || level >= 8 ? 5 : 4;
                for (int k = 0; k < n; k++) {
                    Shot* s = shot_new(OWN_MARK);
                    if (s) {
                        s->x = F8(rx + off[k + (n == 4 && k >= 2)] + rndr(10) - 5);
                        s->y = F8(R.gy - 4);
                        s->gy = R.gy;
                        s->life = 45 + k * 4;
                        s->kind = B.mega ? PJ_ELEC : d->proj;
                    }
                }
            }
            done = t >= 50;
            break;
        case A_CHARGE: {
            B.x += B.vx;
            B.frame = (t >> 2) & 1 ? 2 : 1;
            if ((t & 7) == 0) fx_add(K_DUST, bx - 16 - B.face * 20, B.gy - 16, 0);
            int passed = (B.vx > 0 && bx > rx + 70) || (B.vx < 0 && bx < rx - 70);
            if (passed || bx <= lo || bx >= hi || t > 120) {
                B.vx = 0;
                done = 1;
            }
            break;
        }
        case A_JUMP:
            done = 0;   // ends when it lands (see above)
            if (t > 200) done = 1;
            break;
        case A_BEAM:
            if (t < 48 && (t & 3) == 0) {
                int vy = (rndr(5) - 2) * 40;
                boss_proj(hand_x, hand_y + 4, B.face * 900, vy, d->beam, 0, 30, 1);
                if ((t & 7) == 0) sfx(SFX_HIT);
            }
            done = t >= 52;
            break;
        }
        if (done) {
            B.st = BS_MOVE;
            B.cd = B.mega ? 30 + rndr(30) : imax(40, 90 - level * 3) + rndr(40);
            if (hard) B.cd = B.cd * 2 / 3;
        }
        break;
    }
    }
    if (B.x < F8(lo)) B.x = F8(lo);
    if (B.x > F8(hi)) B.x = F8(hi);
    // touching the robot hurts
    int x0, y0, x1, y1, a0, b0, a1, b1;
    boss_box(&x0, &y0, &x1, &y1);
    robot_box(&a0, &b0, &a1, &b1);
    if (near_lane(B.gy, R.gy, 12) && boxes(x0 + 6, y0 + 6, x1 - 6, y1, a0, b0, a1, b1)) hurt(B.st == BS_ATK && B.atk == A_CHARGE ? 3 : 2);
    boss_frame_upload();
}

// ---------------------------------------------------------------- enemies

static void enemy_spawn(int x, int fly) {
    for (int i = 0; i < MAX_EN; i++)
        if (en[i].st == ES_OFF) {
            Enemy* e = &en[i];
            e->st = ES_LIVE;
            e->fly = fly;
            e->suit = rndr(ENEMY_SUITS);
            e->x = F8(x);
            e->gy = LANE_TOP + rndr(LANE_BOT - LANE_TOP + 1);
            e->y = F8(fly ? e->gy - 12 : e->gy);
            e->spd = (fly ? 140 : 100) + rndr(60);
            e->keep = 46 + rndr(70);
            e->cd = 70 + rndr(90);
            e->hover = rndr(64);
            e->stun = 0;
            e->anim = 0;
            e->shoot = 0;
            e->hit = 0;
            e->t = 0;
            return;
        }
}

static void enemy_kill(Enemy* e, int squish) {
    if (squish) {
        e->st = ES_SQUISH;
        e->t = 40;
        e->y = F8(e->gy);
        sfx(SFX_SQUISH);
    } else {
        e->st = ES_OFF;
        fx_add(K_POP, (e->x >> 8) - 8, (e->y >> 8) - 20, 0);
        sfx(SFX_HIT);
    }
    squished++;
    level_squish++;
    gain_xp(1);
    if (rndr(100) < 12) pickup_add(PK_HEART, e->x >> 8, (e->y >> 8) - 20, e->gy);
}

static int live_enemies(void) {
    int n = 0;
    for (int i = 0; i < MAX_EN; i++) n += en[i].st == ES_LIVE;
    return n;
}

static void enemies_update(void) {
    int rx = R.x >> 8;
    int a0, b0, a1, b1;
    robot_box(&a0, &b0, &a1, &b1);
    for (int i = 0; i < MAX_EN; i++) {
        Enemy* e = &en[i];
        if (e->st == ES_OFF) continue;
        int ex = e->x >> 8;
        if (e->st == ES_SQUISH) {
            if (--e->t <= 0) e->st = ES_OFF;
            continue;
        }
        if (e->st == ES_FLEE) {
            int dir = ex >= rx ? 1 : -1;
            e->x += dir * 640;
            e->anim++;
            if (ex < cam - 40 || ex > cam + 280) e->st = ES_OFF;
            continue;
        }
        if (e->shoot) e->shoot--;
        if (e->stun) {
            e->stun--;
            continue;
        }
        // they march left, toward (and past) the robot
        int dx = rx - ex;
        e->x -= e->spd;
        e->anim++;
        // close in on the robot's lane while ahead of it
        if (dx < 0 && dx > -150 && (e->anim & 3) == 0 && e->gy != R.gy) {
            int d = e->gy < R.gy ? 1 : -1;
            e->gy += d;
            if (!e->fly) e->y += d * 256;
        }
        if (e->fly) {
            // hover between 8 and 19 px above the street (their heads stay below the robot's waist)
            int ph = (frame + e->hover * 4) & 127;
            int bob = ph < 64 ? ph : 127 - ph;
            int ty = e->gy - 8 - bob * 11 / 63;
            e->y += (F8(ty) - e->y) >> 3;
        }
        if (ex < cam - 80 || ex > cam + 340) {
            e->st = ES_OFF;
            continue;
        }
        if (--e->cd <= 0) {
            e->cd = imax(50, 110 + rndr(80) - level * 4);
            if (ex > rx + 20 && ex < cam + 244) {
                Shot* s = shot_new(OWN_BULLET);
                if (s) {
                    int sx = ex + (dx > 0 ? 7 : -7), sy = (e->y >> 8) - 18;
                    s->x = F8(sx);
                    s->y = F8(sy);
                    aim(sx, sy, rx, (R.y >> 8) - 46, 600, &s->vx, &s->vy);
                    s->life = 160;
                    e->shoot = 12;
                }
            }
        }
        int x0, y0, x1, y1;
        enemy_box(e, &x0, &y0, &x1, &y1);
        if (near_lane(e->gy, R.gy, 8) && boxes(x0, y0, x1, y1, a0 + 4, b0, a1 - 4, b1)) hurt(1);
    }
}

// ---------------------------------------------------------------- robot

// eye position (world px) for the current frame
static void robot_eye(int* x, int* y) {
    int f = R.frame;
    int ex = robot_eye_x[f];
    *x = (R.x >> 8) + (R.face > 0 ? ex - 31 : 32 - ex);
    *y = (R.y >> 8) - 95 + robot_eye_y[f];
}

static void robot_hand(int* x, int* y) {
    int f = R.frame;
    int hx = robot_hand_x[f];
    *x = (R.x >> 8) + (R.face > 0 ? hx - 31 : 32 - hx) + R.face * 4;
    *y = (R.y >> 8) - 95 + robot_hand_y[f];
}

static void fire_bolts(void) {
    int hx, hy;
    robot_hand(&hx, &hy);
    // aim at the nearest target in front
    int best = 9999, tx = 0, ty = 0;
    for (int i = 0; i < MAX_EN; i++) {
        Enemy* e = &en[i];
        if (e->st != ES_LIVE) continue;
        int dx = (e->x >> 8) - hx;
        if (dx * R.face <= 4 || iabs(dx) > 220) continue;
        if (iabs(dx) < best) {
            best = iabs(dx);
            tx = e->x >> 8;
            ty = (e->y >> 8) - 11;
        }
    }
    if (B.on && B.st != BS_DIE && B.st != BS_ENTER) {
        int dx = (B.x >> 8) - hx;
        if (dx * R.face > 0 && iabs(dx) < best) {
            best = iabs(dx);
            tx = B.x >> 8;
            ty = (B.y >> 8) - (B.mega ? 60 : 36);
        }
    }
    int vx, vy;
    if (best < 9999) aim(hx, hy, tx, ty, 1700, &vx, &vy);
    else { vx = R.face * 1700; vy = 200; }
    int n = hand_n[up_lv[U_HAND]];
    static const s16 spread[3][3] = { { 0, 0, 0 }, { -110, 110, 0 }, { -220, 0, 220 } };
    for (int k = 0; k < n; k++) {
        Shot* s = shot_new(OWN_BOLT);
        if (!s) break;
        s->x = F8(hx);
        s->y = F8(hy - 2 + (n == 2 ? (k ? 3 : -3) : 0));
        s->vx = vx;
        s->vy = vy + spread[n - 1][k];
        s->life = 80;
        s->dmg = up_lv[U_HAND] >= 3 ? 3 : 2;
    }
    fx_add(K_FLASH, hx - 8, hy - 8, 0);
    sfx(SFX_LASER);
}

static void do_stomp(void) {
    int rx = R.x >> 8;
    int w = stomp_w[up_lv[U_STOMP]];
    int z0 = R.face > 0 ? rx + 2 : rx - w;
    int z1 = R.face > 0 ? rx + w : rx - 2;
    if (up_lv[U_STOMP] >= 2) { z0 -= 14; z1 += 14; }
    for (int i = 0; i < MAX_EN; i++) {
        Enemy* e = &en[i];
        if (e->st != ES_LIVE) continue;
        int ex = e->x >> 8;
        int low = (e->y >> 8) >= e->gy - (up_lv[U_STOMP] >= 2 ? 20 : 10);
        int lane = near_lane(e->gy, R.gy, up_lv[U_STOMP] >= 2 ? 14 : 10);
        if (ex >= z0 && ex <= z1 && low && lane) enemy_kill(e, !e->fly);
    }
    if (B.on && !B.air && near_lane(B.gy, R.gy, 14)) {
        int x0, y0, x1, y1;
        boss_box(&x0, &y0, &x1, &y1);
        if (z1 >= x0 && z0 <= x1) boss_damage(stomp_dmg[up_lv[U_STOMP]]);
    }
    fx_add(K_DUST, (R.face > 0 ? rx + 16 : rx - 16) - 16, R.gy - 16, 0);
    if (up_lv[U_STOMP] >= 2) {
        fx_add(K_DUST, rx + 20, R.gy - 16, 2);
        fx_add(K_DUST, rx - 52, R.gy - 16, -2);
    }
    shake(6, 2);
    sfx(SFX_STOMP);
}

static void do_slam(void) {
    int rx = R.x >> 8;
    int r = slam_r[up_lv[U_SLAM]];
    for (int i = 0; i < MAX_EN; i++) {
        Enemy* e = &en[i];
        if (e->st != ES_LIVE) continue;
        int ex = e->x >> 8;
        if (iabs(ex - rx) <= r && (e->y >> 8) >= e->gy - 22 && near_lane(e->gy, R.gy, 18)) enemy_kill(e, !e->fly);
    }
    if (B.on && !B.air && near_lane(B.gy, R.gy, 20)) {
        int x0, y0, x1, y1;
        boss_box(&x0, &y0, &x1, &y1);
        if (rx + r >= x0 && rx - r <= x1) boss_damage(slam_dmg[up_lv[U_SLAM]]);
    }
    for (int k = 0; k < 3; k++) {
        fx_add(K_DUST, rx + 4 + k * 10, R.gy - 16, 3 + k);
        fx_add(K_DUST, rx - 36 - k * 10, R.gy - 16, -3 - k);
    }
    shake(16, 4);
    sfx(SFX_SLAM);
}

static void do_clap(void) {
    for (int i = 0; i < MAX_EN; i++)
        if (en[i].st == ES_LIVE) en[i].stun = 180;
    if (B.on && B.st != BS_DIE && B.st != BS_ENTER) B.stun = 90;
    for (int i = 0; i < MAX_SHOT; i++)
        if (sh[i].on && sh[i].own != OWN_BOLT) sh[i].on = 0;
    int hx, hy;
    robot_hand(&hx, &hy);
    for (int k = 0; k < 6; k++) fx_add(K_SPARK, hx - 8 + (k - 3) * 14, hy - 20 + rndr(40), 0);
    fade(1, 14);
    shake(10, 3);
    sfx(SFX_CLAP);
}

static void world_boom(Enemy* e) {
    phase = PH_BOOM;
    boom_t = 0;
    worlds++;
    e->hit = 1;
    music(SONG_NONE);
    sfx(SFX_BIGBOOM);
}

// The eye beam: from the eyes, down and forward at a slope of 1 down for every 2 across.
// Returns how far it reaches (pixels along x).
static int beam_len;

static int beam_hits(int ex, int ey, int x0, int y0, int x1, int y1, int dmax) {
    int d0, d1;
    if (R.face > 0) { d0 = x0 - ex; d1 = x1 - ex; }
    else { d0 = ex - x1; d1 = ex - x0; }
    int e0 = 2 * (y0 - 2 - ey), e1 = 2 * (y1 + 2 - ey);
    int lo = imax(imax(d0, e0), 0), hi = imin(imin(d1, e1), dmax);
    return lo <= hi ? lo : -1;
}

static void beam_update(void) {
    int ex, ey;
    robot_eye(&ex, &ey);
    int dmax = (R.gy - ey) * 2;
    int edge = R.face > 0 ? cam + 240 - ex : ex - cam;
    if (edge < dmax) dmax = edge;
    int dboss = -1;
    if (B.on && B.st != BS_DIE && B.st != BS_ENTER) {
        int x0, y0, x1, y1;
        boss_box(&x0, &y0, &x1, &y1);
        dboss = beam_hits(ex, ey, x0 + 4, y0 + 4, x1 - 4, y1, dmax);
        if (dboss >= 0) dmax = dboss;
    }
    beam_len = dmax;
    // a normal enemy in the beam: that is the end of the world
    for (int i = 0; i < MAX_EN; i++) {
        Enemy* e = &en[i];
        if (e->st != ES_LIVE && e->st != ES_FLEE) continue;
        int x0, y0, x1, y1;
        enemy_box(e, &x0, &y0, &x1, &y1);
        if (x1 < cam || x0 > cam + 240) continue;
        int d = beam_hits(ex, ey, x0, y0, x1, y1, dmax);
        if (d >= 0 && dev_sw[DV_SAFEEYE]) {
            if (e->st == ES_LIVE) enemy_kill(e, 0);
            continue;
        }
        if (d >= 0) {
            beam_len = d;
            world_boom(e);
            return;
        }
    }
    if (dboss >= 0 && (R.t & 2) == 0 && (R.t & 1)) {
        boss_damage(eye_dmg[up_lv[U_EYE]]);
        if ((R.t & 7) == 1) fx_add(K_POP, ex + R.face * dboss - 8, ey + dboss / 2 - 8, 0);
    }
}

static void robot_update(void) {
    int sp = walk_spd[up_lv[U_SPEED]];
    if (dev_sw[DV_FAST]) sp *= 3;
    if (dev_sw[DV_NOCOOL]) {
        R.fire_cd = R.eye_cd = R.slam_cd = 0;
        R.claps = 2 + up_lv[U_THUNDER];
    }
    if (R.inv) R.inv--;
    if (R.hurt_t) R.hurt_t--;
    if (R.fire_cd) R.fire_cd--;
    if (R.eye_cd) R.eye_cd--;
    if (R.slam_cd) R.slam_cd--;
    if (R.shoot_t) R.shoot_t--;
    R.moving = 0;
    int boss_phase = phase != PH_WALK;
    if (R.st == RS_DEAD) {
        R.t++;
        R.frame = RF_DEAD;
        R.glass = 0;
        if ((R.t % 12) == 0 && R.t < 90) {
            fx_add(K_POP, (R.x >> 8) - 20 + rndr(32), (R.y >> 8) - 70 + rndr(50), 0);
            sfx(SFX_BOOM);
        }
        return;
    }
    // L and R: wait a few frames for the other button so L+R makes a thunderclap
    if (R.st == RS_FREE) {
        int both = (keys & (KEY_L | KEY_R)) == (KEY_L | KEY_R) && (pressed & (KEY_L | KEY_R));
        if (both || ((pressed & KEY_L) && R.pend_r) || ((pressed & KEY_R) && R.pend_l)) {
            R.pend_l = R.pend_r = 0;
            if (R.claps > 0) {
                R.claps--;
                R.st = RS_CLAP;
                R.t = 0;
            } else {
                sfx(SFX_SELECT);
            }
        } else {
            if (pressed & KEY_L) R.pend_l = 6;
            if (pressed & KEY_R) R.pend_r = 6;
        }
        if (R.pend_l && --R.pend_l == 0) {
            if (R.slam_cd == 0) {
                R.st = RS_SLAM;
                R.t = 0;
                R.vy = 0;
            }
        }
        if (R.pend_r && --R.pend_r == 0) {
            if (R.eye_cd == 0) {
                R.st = RS_EYE;
                R.t = 0;
            }
        }
        if (R.st == RS_FREE && (pressed & KEY_A)) {
            R.st = RS_STOMP;
            R.t = 0;
        }
    }
    switch (R.st) {
    case RS_FREE: {
        if ((keys & KEY_UP) && R.gy > LANE_TOP) R.gy--;
        if ((keys & KEY_DOWN) && R.gy < LANE_BOT) R.gy++;
        if (keys & (KEY_UP | KEY_DOWN)) R.moving = 1;
        R.y = F8(R.gy);
        if (!boss_phase) {
            // the level scrolls: the robot marches right on its own (RIGHT = faster, LEFT = hold still)
            int v = (keys & KEY_LEFT) ? 0 : (keys & KEY_RIGHT) ? sp * 3 / 2 : sp;
            R.face = 1;
            if (v) {
                R.x += v;
                R.walk += v;
                R.moving = 1;
            }
        } else {
            int dir = (keys & KEY_RIGHT) ? 1 : (keys & KEY_LEFT) ? -1 : 0;
            if (dir) {
                R.face = dir;
                R.x += dir * sp;
                R.walk += sp;
                R.moving = 1;
            }
        }
        if ((keys & KEY_B) && R.fire_cd == 0) {
            fire_bolts();
            R.fire_cd = hand_cd[up_lv[U_HAND]];
            R.shoot_t = 16;
        }
        int wf = (R.walk >> 11) & 3;
        // heavy footfalls: a little shake each time a foot lands
        static int last_wf;
        if (R.moving && wf != last_wf && (wf & 1) == 0) {
            shake(3, 1);
            // dust puff under the foot that just landed
            int foot = wf == 0 ? 18 : -14;
            fx_add(K_PUFF, (R.x >> 8) + R.face * foot - 8, R.gy - 14, 0);
        }
        last_wf = wf;
        if (R.hurt_t > 6) R.frame = RF_HURT;
        else if (R.shoot_t) R.frame = R.moving ? RF_SHOOT1 + wf : RF_SHOOT;
        else R.frame = R.moving ? RF_WALK1 + wf : RF_STAND;
        break;
    }
    case RS_STOMP:
        R.frame = R.t < 10 ? RF_STOMP_UP : RF_STOMP_DN;
        if (R.t == 10) do_stomp();
        if (++R.t >= 22) R.st = RS_FREE;
        break;
    case RS_SLAM:
        if (R.t < 8) {
            R.frame = RF_CROUCH;
            if (R.t == 7) R.vy = -6 * 256;
        } else if (R.vy != 0 || R.y < F8(R.gy)) {
            R.frame = RF_JUMP;
            R.vy += 80;
            R.y += R.vy;
            int dir = (keys & KEY_RIGHT) ? 1 : (keys & KEY_LEFT) ? -1 : 0;
            if (!boss_phase) dir = (keys & KEY_LEFT) ? 0 : 1;
            if (dir) { R.face = dir; R.x += dir * sp; }
            if (R.y >= F8(R.gy)) {
                R.y = F8(R.gy);
                R.vy = 0;
                R.t = 100;
                do_slam();
            }
        }
        if (R.t >= 100) {
            R.frame = RF_LAND;
            if (R.t >= 116) {
                R.st = RS_FREE;
                R.slam_cd = slam_cool[up_lv[U_SLAM]];
            }
        }
        R.t++;
        break;
    case RS_CLAP:
        R.frame = R.t < 10 ? RF_CLAP_OPEN : RF_CLAP_SHUT;
        if (R.t == 10) do_clap();
        if (R.t == 12) fade(0, 0);
        if (++R.t >= 30) R.st = RS_FREE;
        break;
    case RS_EYE: {
        int len = eye_len[up_lv[U_EYE]];
        R.frame = RF_STAND;
        if (R.t < 10) R.glass = R.t;
        else if (R.t < 10 + len) R.glass = 9;
        else R.glass = 9 - (R.t - 10 - len);
        if (R.t == 10) sfx(SFX_EYE);
        if (R.t >= 10 && R.t < 10 + len) beam_update();
        if (phase == PH_BOOM) return;
        if (++R.t >= 20 + len) {
            R.st = RS_FREE;
            R.glass = 0;
            R.eye_cd = eye_cool[up_lv[U_EYE]];
        }
        break;
    }
    }
    // eyes glow while the glasses are up
    int beam = R.st == RS_EYE && R.t >= 10 && R.t < 10 + eye_len[up_lv[U_EYE]];
    OBJ_PAL[9] = beam ? RGB(31, 8, 4) : robot_pal[9];
    OBJ_PAL[10] = beam ? RGB(31, 30, 26) : robot_pal[10];
    // stay on screen; the camera only moves forward
    int lo = cam + 18, hi = boss_phase ? cam + 222 : cam + 200;
    if (R.x < F8(lo)) R.x = F8(lo);
    if (R.x > F8(hi)) R.x = F8(hi);
}

// ---------------------------------------------------------------- shots, pickups, effects

static void shots_update(void) {
    int a0, b0, a1, b1;
    robot_box(&a0, &b0, &a1, &b1);
    for (int i = 0; i < MAX_SHOT; i++) {
        Shot* s = &sh[i];
        if (!s->on) continue;
        s->t++;
        if (s->own == OWN_MARK) {
            if (--s->life <= 0) {
                s->own = OWN_BOSS;
                s->y = F8(-12);
                s->vy = 4 * 256;
                s->vx = 0;
                s->life = 80;
                s->dmg = 2;
            }
            continue;
        }
        s->vy += s->grav;
        s->x += s->vx;
        s->y += s->vy;
        int x = s->x >> 8, y = s->y >> 8;
        if (--s->life <= 0 || x < cam - 24 || x > cam + 264 || y > s->gy || y < -40) {
            if (s->own == OWN_BOSS && y > s->gy && s->grav) fx_add(K_POP, x - 8, s->gy - 14, 0);
            s->on = 0;
            continue;
        }
        if (s->own == OWN_BOLT) {
            for (int k = 0; k < MAX_EN; k++) {
                Enemy* e = &en[k];
                if (e->st != ES_LIVE) continue;
                int x0, y0, x1, y1;
                enemy_box(e, &x0, &y0, &x1, &y1);
                if (x >= x0 - 3 && x <= x1 + 3 && y >= y0 - 3 && y <= y1 + 3) {
                    enemy_kill(e, 0);
                    s->on = 0;
                    break;
                }
            }
            if (s->on && B.on && B.st != BS_DIE && B.st != BS_ENTER) {
                int x0, y0, x1, y1;
                boss_box(&x0, &y0, &x1, &y1);
                if (x >= x0 && x <= x1 && y >= y0 && y <= y1) {
                    boss_damage(s->dmg);
                    fx_add(K_POP, x - 8, y - 8, 0);
                    s->on = 0;
                }
            }
        } else if (s->own == OWN_WAVE) {
            if (R.y >= F8(R.gy - 2) && near_lane(s->gy, R.gy, 10) && x >= a0 && x <= a1) {
                hurt(s->dmg);
                s->on = 0;
            }
            if ((s->t & 3) == 0) fx_add(K_DUST, x - 16, s->gy - 16, 0);
        } else {
            if (x >= a0 - 2 && x <= a1 + 2 && y >= b0 && y <= b1) {
                hurt(s->dmg);
                s->on = 0;
            }
        }
    }
}

static void pickups_update(void) {
    int rx = R.x >> 8;
    for (int i = 0; i < MAX_PK; i++) {
        Pickup* p = &pk[i];
        if (!p->on) continue;
        p->t++;
        if (p->y < F8(p->gy)) {
            p->vy += 30;
            p->y += p->vy;
            if (p->y > F8(p->gy)) {
                p->y = F8(p->gy);
                p->vy = 0;
            }
        }
        if (iabs(p->x - rx) < 20 && p->vy == 0 && near_lane(p->gy, R.gy, 12)) {
            R.hp += p->kind == PK_CELL ? 12 : 5;
            if (R.hp > R.maxhp) R.hp = R.maxhp;
            sfx(SFX_PICKUP);
            p->on = 0;
            continue;
        }
        if (p->t > 900 || p->x < cam - 30) p->on = 0;
    }
}

static void fx_update(void) {
    for (int i = 0; i < MAX_FX; i++) {
        Fx* f = &fx[i];
        if (!f->on) continue;
        f->t++;
        f->x += f->vx;
        int life = f->kind == K_BOOM ? 25 : f->kind == K_POP ? 16 : f->kind == K_SPARK ? 14 :
                   f->kind == K_PUFF ? 15 : f->kind == K_FLASH ? 4 : 18;
        if (f->t >= life) f->on = 0;
    }
}

// ---------------------------------------------------------------- drawing

static void draw_weather(void);
static void draw_shadows(int sx0, int sy0);

static void draw_proj(Shot* s, int sx, int sy) {
    int k = s->kind;
    int base = T_PROJ + proj_start[k];
    if (proj_frames[k] == 5) {
        // five angle variants (0..90 degrees), flipped for the other quadrants
        int ax = iabs(s->vx), ay = iabs(s->vy);
        int v;
        if (ay * 5 < ax) v = 0;
        else if (ay * 3 < ax * 2) v = 1;
        else if (ay * 2 < ax * 3) v = 2;
        else if (ay < ax * 5) v = 3;
        else v = 4;
        spr(sx - 8, sy - 8, SQ, 1, base + v * 4, PAL_PROJ, s->vx < 0, s->vy < 0);
    } else {
        int f = proj_frames[k] > 1 ? (s->t >> 2) & 1 : 0;
        spr(sx - 8, sy - 8, SQ, 1, base + f * 4, PAL_PROJ, s->vx < 0, 0);
    }
}

static void draw_bolt(Shot* s, int sx, int sy) {
    int ax = iabs(s->vx), ay = iabs(s->vy);
    int v;
    if (ay * 5 < ax) v = 0;
    else if (ay * 3 < ax * 2) v = 1;
    else if (ay * 2 < ax * 3) v = 2;
    else if (ay < ax * 5) v = 3;
    else v = 4;
    spr(sx - 8, sy - 8, SQ, 1, T_FX + FX_BOLT + v * 4, PAL_FX, s->vx < 0, s->vy < 0);
}

static void draw_boss(int sx0, int sy0) {
    {
        int cols = B.mega ? 4 : 2, rows = B.mega ? 4 : 3;
        int w = cols * 32, cx = B.mega ? 64 : 32;
        int sx = (B.x >> 8) + sx0, sy = (B.y >> 8) + sy0;
        int hf = B.face < 0;
        int ox = hf ? sx - (w - cx) : sx - cx, oy = sy - (B.mega ? 127 : 95);
        int pal = B.flash ? PAL_WHITE : PAL_BOSS;
        if (B.st == BS_TELE && (B.t & 4)) pal = PAL_WHITE;
        if (B.stun) {
            int st = ((frame >> 3) & 1);
            for (int k = 0; k < 3; k++)
                spr(sx - 12 + k * 10, oy + (B.mega ? 14 : 22) - ((k + frame / 8) & 1) * 3, SQ, 0,
                    T_FX + FX_STAR + st, PAL_FX, 0, 0);
        }
        for (int r = 0; r < rows; r++)
            for (int c = 0; c < cols; c++)
                spr(ox + (hf ? cols - 1 - c : c) * 32, oy + r * 32, SQ, 2, T_BOSS + (r * cols + c) * 16, pal, hf, 0);
    }
}

static void draw_enemies(int sx0, int sy0, int front) {
    int rx = R.x >> 8;
    for (int i = 0; i < MAX_EN; i++) {
        Enemy* e = &en[i];
        if (e->st == ES_OFF || (e->gy > R.gy) != front) continue;
        int x = (e->x >> 8) + sx0, y = (e->y >> 8) + sy0;
        int f;
        if (e->st == ES_SQUISH) f = EF_SQUISH;
        else if (e->shoot && e->st == ES_LIVE) f = EF_SHOOT;
        else if (e->fly) f = (frame >> 2) & 1 ? EF_FLY1 : EF_FLY2;
        else f = (e->anim >> 3) & 1 ? EF_WALK1 : EF_WALK2;
        int hf = e->st == ES_FLEE ? (e->x >> 8) < rx : 1;
        int pal = PAL_ENEMY + e->suit;
        if (e->stun) {
            pal = PAL_STUN;
            spr(x - 4, y - 32 + ((frame >> 3) & 1), SQ, 0, T_FX + FX_STAR + ((frame >> 3) & 1), PAL_FX, 0, 0);
        }
        if (e->hit && (frame & 2)) pal = PAL_WHITE;
        spr(x - 8, y - 32, TALL, 2, T_ENEMY + f * 8, pal, hf, 0);
    }
}

static void draw_world(void) {
    int sx0 = -cam + shake_x, sy0 = shake_y;
    // effects in front
    for (int i = 0; i < MAX_FX; i++) {
        Fx* f = &fx[i];
        if (!f->on) continue;
        int x = f->x + sx0, y = f->y + sy0;
        if (f->kind == K_BOOM) spr(x, y, SQ, 2, T_FX + FX_BOOM + (f->t / 5) * 16, PAL_FX, 0, 0);
        else if (f->kind == K_POP) spr(x, y, SQ, 1, T_FX + FX_POP + (f->t / 4) * 4, PAL_FX, 0, 0);
        else if (f->kind == K_SPARK) spr(x, y - f->t, SQ, 1, T_FX + FX_SPARK + ((f->t >> 2) & 1) * 4, PAL_FX, 0, 0);
        else if (f->kind == K_PUFF) spr(x, y, SQ, 1, T_FX + FX_PUFF + (f->t / 5) * 4, PAL_FX, f->vx < 0, 0);
        else if (f->kind == K_FLASH) spr(x, y, SQ, 1, T_FX + FX_MFLASH + (f->t >> 1) * 4, PAL_FX, 0, 0);
        else spr(x, y, WIDE, 2, T_FX + FX_DUST + ((f->t >> 3) & 1) * 8, PAL_FX, f->vx < 0, 0);
    }
    draw_weather();
    // shots
    for (int i = 0; i < MAX_SHOT; i++) {
        Shot* s = &sh[i];
        if (!s->on) continue;
        int x = (s->x >> 8) + sx0, y = (s->y >> 8) + sy0;
        if (s->own == OWN_BOLT) draw_bolt(s, x, y);
        else if (s->own == OWN_BULLET) spr(x - 4, y - 4, SQ, 0, T_FX + FX_BULLET, PAL_FX, 0, 0);
        else if (s->own == OWN_BOSS) draw_proj(s, x, y);
        else if (s->own == OWN_MARK) {
            if ((s->life >> 2) & 1) spr(x - 4, y - 6, SQ, 0, T_FX + FX_WARN, PAL_FX, 0, 0);
        }
    }
    // the eye beam
    int beaming = R.st == RS_EYE && R.t >= 10 && R.t < 10 + eye_len[up_lv[U_EYE]];
    if (beaming || (phase == PH_BOOM && boom_t < 40)) {
        int ex, ey;
        robot_eye(&ex, &ey);
        int segs = (beam_len + 15) / 16;
        if (segs > 14) segs = 14;
        int v = (frame >> 1) & 1;
        for (int k = 0; k < segs; k++) {
            int bx = ex + R.face * k * 16;
            int x = R.face > 0 ? bx : bx - 16;
            spr(x + sx0, ey + k * 8 - 6 + sy0, SQ, 1, T_FX + FX_BEAM + v * 4, PAL_FX, R.face < 0, 0);
        }
        spr(ex - 8 + sx0, ey - 8 + sy0, SQ, 1, T_FX + FX_FLARE + v * 4, PAL_FX, 0, 0);
        spr(ex - 8 - R.face * 12 + sx0, ey - 8 + sy0, SQ, 1, T_FX + FX_FLARE + v * 4, PAL_FX, 0, 0);
    }
    // depth: things lower on the street are in front
    draw_enemies(sx0, sy0, 1);
    if (B.on && B.gy > R.gy) draw_boss(sx0, sy0);
    // the robot (its frame is streamed into VRAM when it changes)
    if (R.frame != shown_frame) {
        shown_frame = R.frame;
        upload((void*)(OBJ_TILES + T_ROBOT * 16), &robot_tiles[R.frame * 96 * 8], 96 * 8);
    }
    {
        int sx = (R.x >> 8) + sx0, sy = (R.y >> 8) + sy0;
        int ox = R.face > 0 ? sx - 31 : sx - 32, oy = sy - 95;
        int pal = ((R.inv & 4) && phase != PH_BOOM) ? PAL_WHITE : PAL_ROBOT;
        int gx = robot_glass_x[R.frame], gy = robot_glass_y[R.frame];
        spr(R.face > 0 ? ox + gx : ox + 32 - gx, oy + gy - R.glass, WIDE, 1, T_GLASS, pal, R.face < 0, 0);
        for (int r = 0; r < 3; r++)
            for (int c = 0; c < 2; c++)
                spr(ox + (R.face > 0 ? c : 1 - c) * 32, oy + r * 32, SQ, 2, T_ROBOT + (r * 2 + c) * 16, pal,
                    R.face < 0, 0);
    }
    if (B.on && B.gy <= R.gy) draw_boss(sx0, sy0);
    // pickups
    for (int i = 0; i < MAX_PK; i++) {
        Pickup* p = &pk[i];
        if (!p->on || (p->t > 780 && (p->t & 4))) continue;
        int x = p->x + sx0 - 8, y = (p->y >> 8) + sy0 - 16 - ((p->vy == 0) ? ((frame >> 3) & 1) : 0);
        spr(x, y, SQ, 1, T_FX + (p->kind == PK_CELL ? FX_CELL : FX_HEART), PAL_FX, 0, 0);
    }
    draw_enemies(sx0, sy0, 0);
    draw_shadows(sx0, sy0);
}

static void draw_bar(int x, int y, int n, int val, int max, int base) {
    int units = max > 0 ? val * n * 8 / max : 0;
    if (val > 0 && units == 0) units = 1;
    for (int i = 0; i < n; i++) {
        int f = units - i * 8;
        if (f < 0) f = 0;
        if (f > 8) f = 8;
        put_tile(x + i, y, base + f);
    }
}

static void hud(void) {
    put_tile(0, 0, HUD_HEART);
    draw_bar(1, 0, 8, R.hp, R.maxhp, HUD_BAR_HP);
    int maxc = 2 + up_lv[U_THUNDER];
    for (int i = 0; i < 5; i++) put_tile(10 + i, 0, i < maxc ? (i < R.claps ? HUD_BOLT : HUD_BOLT_EMPTY) : 0);
    put_tile(16, 0, HUD_EYE);
    int cool = eye_cool[up_lv[U_EYE]];
    int ready = R.st == RS_EYE ? 0 : cool - R.eye_cd;
    draw_bar(17, 0, 4, ready, cool, HUD_BAR_EYE);
    char b[8] = "LV ";
    num_str(b + 3, level);
    txt(24, 0, "      ", 0);
    txt(24, 0, b, 0);
    // experience: kills fill the bar; a full bar means a level up
    txt(0, 1, "XP", 0);
    draw_bar(2, 1, 6, xp, xp_need(), HUD_BAR_XP);
    char pb[8] = "PL ";
    num_str(pb + 3, plv + 1);
    txt(9, 1, "     ", 0);
    txt(9, 1, pb, 1);
    if (B.on && B.st != BS_ENTER) {
        put_tile(0, 2, HUD_SKULL);
        txt(1, 2, boss_names[B.mega ? MEGA_ID : B.id], 1);
        draw_bar(1, 3, 16, B.hp, B.maxhp, HUD_BAR_BOSS);
    } else {
        txt_clear_rows(2, 3);
    }
    if (banner_t > 0) {
        banner_t--;
        if (banner_t == 0) txt_clear_rows(7, 12);
        else {
            if (banner && (banner[0] != 'W' || ((banner_t >> 3) & 1))) txt_big_center(7, banner);
            else txt_clear_rows(7, 8);
            if (banner2) txt_center(11, banner2, 0);
        }
    }
}

static void panel_rows(int y0, int y1) {
    for (int y = y0; y <= y1; y++)
        for (int x = 1; x <= 28; x++) put_tile(x, y, y == y0 ? HUD_PANEL_TOP : y == y1 ? HUD_PANEL_BOT : HUD_PANEL);
}

static void pause_screen(int on) {
    txt_clear_rows(4, 19);
    if (!on) return;
    panel_rows(4, 18);
    txt_big_center(5, "PAUSED");
    txt(3, 8, "A STOMP    B HAND LASERS", 3);
    txt(3, 10, "R EYE LASERS (BOSSES!)", 3);
    txt(3, 12, "L SLAM     L+R THUNDER", 3);
    txt(3, 14, "SELECT  MUSIC", 2);
    txt(17, 14, music_on ? "ON " : "OFF", 3);
    txt(3, 16, "START   KEEP PLAYING", 2);
}

static void levelup_screen(void) {
    txt_clear_rows(4, 19);
    panel_rows(4, 19);
    txt_big_center(5, "LEVEL UP!");
    draw_upgrade_choices(8, lvl_sel, 1);
}

// ---- dev menu: L+R+B in a level. Six switches, then one-shot actions.
enum { DM_SKIP = DV_COUNT, DM_CLEAR, DM_LVLUP, DM_MAX, DM_GOTO, DM_COUNT };
static const char* const dev_names[DM_COUNT] = {
    "ENEMIES", "GOD MODE", "ONE-HIT BOSSES", "NO COOLDOWNS", "SAFE EYES", "FAST WALK",
    "SKIP TO BOSS", "CLEAR LEVEL", "LEVEL UP", "MAX UPGRADES", "GO TO LEVEL",
};

static void dev_screen(void) {
    txt_clear_rows(3, 19);
    panel_rows(3, 19);
    txt_big_center(4, "DEV MODE");
    for (int i = 0; i < DM_COUNT; i++) {
        int y = 7 + i;
        txt(3, y, i == dev_sel ? ">" : " ", 3);
        txt(4, y, dev_names[i], i == dev_sel ? 3 : 2);
        if (i < DV_COUNT) {
            int on = i == DV_NOENEMY ? !dev_sw[i] : dev_sw[i];
            txt(21, y, on ? "ON " : "OFF", 3);
        } else if (i == DM_GOTO) {
            char b[8] = "- ";
            num_str(b + 2, dev_lv);
            int n = 2;
            while (b[n]) n++;
            b[n++] = ' ';
            b[n++] = '+';
            b[n] = 0;
            txt(21, y, b, 3);
        }
    }
    txt(3, 18, "A SET  B CLOSE  NO SAVING", 2);
}

static void dev_close(void) {
    dev_open = 0;
    txt_clear_rows(3, 19);
    banner_t = 0;
    R.pend_l = R.pend_r = 0;
}

// returns an event when an action leaves the level
static int dev_update(void) {
    if (pressed & KEY_UP) { dev_sel = (dev_sel + DM_COUNT - 1) % DM_COUNT; sfx(SFX_SELECT); dev_screen(); }
    if (pressed & KEY_DOWN) { dev_sel = (dev_sel + 1) % DM_COUNT; sfx(SFX_SELECT); dev_screen(); }
    if (dev_sel == DM_GOTO && (pressed & (KEY_LEFT | KEY_RIGHT))) {
        dev_lv = (pressed & KEY_RIGHT) ? dev_lv % LAST_LEVEL + 1 : (dev_lv + LAST_LEVEL - 2) % LAST_LEVEL + 1;
        sfx(SFX_SELECT);
        dev_screen();
    }
    if (pressed & KEY_B) { dev_close(); return EV_NONE; }
    if (!(pressed & KEY_A)) return EV_NONE;
    sfx(SFX_PICKUP);
    if (dev_sel < DV_COUNT) {
        dev_sw[dev_sel] ^= 1;
        dev_screen();
        return EV_NONE;
    }
    int live = phase == PH_WALK || phase == PH_WARN || phase == PH_BOSS || phase == PH_RUSHGAP;
    switch (dev_sel) {
    case DM_SKIP:
        if (phase == PH_WALK) {
            cam = level_len;
            R.x = F8(cam + 60);
        }
        break;
    case DM_CLEAR:
        if (live) {
            B.on = 0;
            rush_i = MEGA_ID;
            phase = PH_BOSS;
            for (int i = 0; i < MAX_EN; i++)
                if (en[i].st == ES_LIVE) en[i].st = ES_FLEE;
        }
        break;
    case DM_LVLUP:
        if (xp < xp_need()) xp = xp_need();
        break;
    case DM_MAX:
        max_upgrades();
        R.maxhp = 20 + 5 * up_lv[U_ARMOR];
        R.hp = R.maxhp;
        R.claps = 2 + up_lv[U_THUNDER];
        break;
    case DM_GOTO:
        level = dev_lv;
        dev_open = 0;
        return EV_GOTO;
    }
    dev_close();
    return EV_NONE;
}

// weather for each area: embers, rain, dust, sparks, snow, none, embers
static void weather_update(int dcam) {
    static const s8 vx[THEME_COUNT] = { -1, -2, -3, -1, -1, 0, 0 };
    static const s8 vy[THEME_COUNT] = { -1, 5, 0, -1, 1, 0, -2 };
    if (theme == 5) return;
    for (int i = 0; i < MAX_WX; i++) {
        wx[i].x += vx[theme] - dcam + ((theme == 4 || theme == 0) && ((frame + i * 7) & 31) < 16 ? 1 : 0);
        wx[i].y += vy[theme] + (theme == 4 && (frame & 1));
        if (wx[i].y > 160) { wx[i].y = -8; wx[i].x = rndr(260); }
        if (wx[i].y < -8) { wx[i].y = 160; wx[i].x = rndr(260); }
        if (wx[i].x < -8) wx[i].x += 256;
        if (wx[i].x > 248) wx[i].x -= 256;
    }
    if (theme == 1) {
        if (lightning_t > 0) {
            lightning_t--;
            if (lightning_t == 3) fade(1, 9);
            if (lightning_t == 1) fade(0, 0);
        } else if (rndr(300) == 0) {
            lightning_t = 5;
            sfx(SFX_BOOM);
        }
    }
}

static void draw_weather(void) {
    static const u8 kind[THEME_COUNT] = { 2, 0, 3, 3, 1, 0, 2 };
    if (theme == 5) return;
    for (int i = 0; i < MAX_WX; i++)
        spr(wx[i].x, wx[i].y, SQ, 0, T_FX + FX_WEATHER + kind[theme], PAL_FX, 0, 0);
}

// dithered shadows on the street, behind everything (shows lanes and how high fliers are)
static void draw_shadows(int sx0, int sy0) {
    int x = (R.x >> 8) + sx0;
    spr(x - 16, R.gy - 4 + sy0, WIDE, 1, T_FX + FX_SHADOW32, PAL_FX, 0, 0);
    if (B.on) {
        int bx = (B.x >> 8) + sx0, n = B.mega ? 3 : 2;
        for (int k = 0; k < n; k++) spr(bx - n * 16 + k * 32, B.gy - 4 + sy0, WIDE, 1, T_FX + FX_SHADOW32, PAL_FX, 0, 0);
    }
    for (int i = 0; i < MAX_EN; i++) {
        Enemy* e = &en[i];
        if (e->st == ES_OFF) continue;
        spr((e->x >> 8) + sx0 - 8, e->gy - 4 + sy0, WIDE, 0, T_FX + FX_SHADOW16, PAL_FX, 0, 0);
    }
}

// ---------------------------------------------------------------- level flow

void play_enter(void) {
    theme = (level - 1) / 3;
    if (theme > THEME_COUNT - 1) theme = THEME_COUNT - 1;
    video_play(theme);
    for (int i = 0; i < MAX_EN; i++) en[i].st = ES_OFF;
    for (int i = 0; i < MAX_SHOT; i++) sh[i].on = 0;
    for (int i = 0; i < MAX_FX; i++) fx[i].on = 0;
    for (int i = 0; i < MAX_PK; i++) pk[i].on = 0;
    B.on = 0;
    cam = 0;
    level_len = dev_sw[DV_NOENEMY] ? 40 : 1700 + level * 120;
    R.x = F8(60);
    R.gy = GROUND_Y;
    R.y = F8(R.gy);
    R.vy = 0;
    R.face = 1;
    R.maxhp = 20 + 5 * up_lv[U_ARMOR];
    R.hp = R.maxhp;
    R.st = RS_FREE;
    R.t = 0;
    R.walk = 0;
    R.fire_cd = R.eye_cd = R.slam_cd = 0;
    R.claps = 2 + up_lv[U_THUNDER];
    R.inv = 0;
    R.glass = 0;
    R.frame = RF_STAND;
    R.shoot_t = R.hurt_t = R.pend_l = R.pend_r = 0;
    shown_frame = -1;
    spawn_t = 90;
    next_heart = 450;
    rush_i = 0;
    paused = 0;
    shake_t = shake_m = 0;
    banner_t = 0;
    level_squish = 0;
    lvlup = 0;
    dev_open = 0;
    lightning_t = 0;
    for (int i = 0; i < MAX_WX; i++) {
        wx[i].x = rndr(240);
        wx[i].y = rndr(160);
    }
    upload((void*)(OBJ_TILES + T_GLASS * 16), glasses_tiles, 32);
    upload((void*)(OBJ_TILES + T_ENEMY * 16), enemy_tiles, sizeof(enemy_tiles) / 4);
    upload((void*)(OBJ_TILES + T_FX * 16), fx_tiles, sizeof(fx_tiles) / 4);
    upload((void*)(OBJ_TILES + T_PROJ * 16), proj_tiles, sizeof(proj_tiles) / 4);
    OBJ_PAL[9] = robot_pal[9];
    OBJ_PAL[10] = robot_pal[10];
    if (level == LAST_LEVEL) {
        phase = PH_RUSHGAP;
        phase_t = 60;
        music(SONG_BOSS);
        set_banner("BOSS RUSH!", 0, 90);
    } else {
        phase = PH_WALK;
        phase_t = 0;
        music(SONG_LEVEL);
        set_banner("GO!", dev_sw[DV_NOENEMY] ? "BOSSES ONLY" : theme_names[theme], 90);
    }
}

int play_update(void) {
    if (dev_open) {
        int ev = dev_update();
        draw_world();
        return ev;
    }
    // L+R+B together: open the dev menu (a thunderclap that just started from L+R is refunded)
    if ((keys & (KEY_L | KEY_R | KEY_B)) == (KEY_L | KEY_R | KEY_B) && (pressed & (KEY_L | KEY_R | KEY_B)) &&
        !lvlup && !paused && phase != PH_BOOM && phase != PH_DEAD && phase != PH_CLEAR) {
        if (R.st == RS_CLAP && R.t < 10) { R.st = RS_FREE; R.claps++; }
        dev_open = 1;
        dev_run = 1;
        dev_lv = level;
        dev_sel = 0;
        dev_screen();
        sfx(SFX_SELECT);
        draw_world();
        return EV_NONE;
    }
    if (phase != PH_BOOM && phase != PH_DEAD && (pressed & KEY_START)) {
        paused ^= 1;
        pause_screen(paused);
        if (!paused) banner_t = banner_t ? banner_t : 0;
        sfx(SFX_SELECT);
    }
    if (lvlup) {
        if (pressed & KEY_UP) { lvl_sel = (lvl_sel + up_count - 1) % up_count; sfx(SFX_SELECT); levelup_screen(); }
        if (pressed & KEY_DOWN) { lvl_sel = (lvl_sel + 1) % up_count; sfx(SFX_SELECT); levelup_screen(); }
        if (++lvlup > 30 && (pressed & KEY_A)) {
            int u = take_upgrade(lvl_sel);
            if (u == U_ARMOR) { R.maxhp += 5; R.hp += 5; }
            else if (u == U_THUNDER) R.claps++;
            else if (u == U_REPAIR) R.hp = R.maxhp;
            sfx(SFX_PICKUP);
            lvlup = 0;
            txt_clear_rows(4, 19);
            banner_t = 0;
        }
        draw_world();
        return EV_NONE;
    }
    if (paused) {
        if (pressed & KEY_SELECT) {
            music_on ^= 1;
            pause_screen(1);
        }
        draw_world();
        return EV_NONE;
    }

    if (phase == PH_BOOM) {
        // the whole world explodes
        boom_t++;
        int t = boom_t;
        if (t > 24 && t < 175) {
            for (int k = 0; k < (t > 70 ? 2 : 1); k++)
                fx_add(K_BOOM, cam + rndr(250) - 20, rndr(170) - 20, 0);
            shake(4, 1 + t / 35);
            if ((t % 18) == 0) sfx(SFX_BIGBOOM);
            if ((t % 10) < 2) fade(1, 12);
            else fade(0, 0);
            if ((t & 7) == 0) set_theme_pal(theme, imin(16, (t - 24) / 6));
        }
        if (t >= 160) fade(1, (t - 160) * 16 / 40);
        fx_update();
        if (shake_t) { shake_t--; shake_x = rndr(shake_m * 2 + 1) - shake_m; shake_y = rndr(shake_m * 2 + 1) - shake_m; }
        draw_world();
        if (t >= 205) return EV_BOOM;
        return EV_NONE;
    }

    robot_update();
    if (phase == PH_BOOM) {
        draw_world();
        return EV_NONE;
    }
    enemies_update();
    boss_update();
    shots_update();
    pickups_update();
    fx_update();

    switch (phase) {
    case PH_WALK: {
        int target = (R.x >> 8) - 100;
        if (target > cam) cam = imin(target, level_len);
        if (!dev_sw[DV_NOENEMY] && --spawn_t <= 0) {
            int maxn = imin(hard ? 12 : 10, 3 + level / 2 + (hard ? 3 : 0));
            if (live_enemies() < maxn && cam < level_len - 120) {
                enemy_spawn(cam + 252, rndr(100) < 35);
            }
            spawn_t = imax(28, 75 - level * 3) + rndr(40);
            if (hard) spawn_t = spawn_t * 2 / 3;
        }
        if (cam >= next_heart) {
            pickup_add(PK_HEART, cam + 190 + rndr(30), -16, LANE_TOP + rndr(LANE_BOT - LANE_TOP));
            next_heart += hard ? 650 : 450;
        }
        if (cam >= level_len) {
            phase = PH_WARN;
            phase_t = 150;
            for (int i = 0; i < MAX_EN; i++)
                if (en[i].st == ES_LIVE) en[i].st = ES_FLEE;
            for (int i = 0; i < MAX_SHOT; i++)
                if (sh[i].own == OWN_BULLET) sh[i].on = 0;
            boss_start(level - 1);
            set_banner("WARNING!", boss_names[level - 1], 150);
            music(SONG_BOSS);
            sfx(SFX_WARN);
        }
        break;
    }
    case PH_WARN:
        if (--phase_t <= 0) phase = PH_BOSS;
        // fall through: the boss can already be beaten during the warning
    case PH_BOSS:
        if (!B.on) {
            if (level == LAST_LEVEL && rush_i < MEGA_ID) {
                rush_i++;
                phase = PH_RUSHGAP;
                phase_t = 110;
                pickup_add(PK_HEART, cam + 120, -16, R.gy);
            } else {
                phase = PH_CLEAR;
                phase_t = 0;
                music(SONG_WIN);
                if (level == LAST_LEVEL) set_banner("YOU WIN!", "THE MEGA ROBOT IS SCRAP!", 400);
                else {
                    static char line[24];
                    char n[8];
                    num_str(n, level_squish);
                    int p = 0;
                    for (const char* s = "SQUISHED: "; *s; s++) line[p++] = *s;
                    for (char* s = n; *s; s++) line[p++] = *s;
                    line[p] = 0;
                    set_banner("LEVEL CLEAR!", line, 400);
                }
            }
        }
        break;
    case PH_RUSHGAP:
        if (--phase_t <= 0) {
            boss_start(rush_i);
            phase = PH_WARN;
            phase_t = 90;
            set_banner(rush_i == MEGA_ID ? "WARNING!" : "NEXT BOSS", boss_names[rush_i], 110);
            sfx(SFX_WARN);
        }
        break;
    case PH_CLEAR:
        if (++phase_t > 200) return level == LAST_LEVEL ? EV_WIN : EV_CLEAR;
        break;
    case PH_DEAD:
        if (++phase_t > 150) return EV_DEAD;
        break;
    }

    if (shake_t) {
        shake_t--;
        shake_x = rndr(shake_m * 2 + 1) - shake_m;
        shake_y = rndr(shake_m * 2 + 1) - shake_m;
        if (!shake_t) shake_m = 0;
    } else {
        shake_x = shake_y = 0;
    }
    weather_update(cam - bg_x[1]);
    // a full XP bar: pause for a level-up pick
    if (xp >= xp_need() && R.st == RS_FREE && (phase == PH_WALK || phase == PH_BOSS || phase == PH_WARN) &&
        !(B.on && B.st == BS_DIE) && (B.on || phase == PH_WALK) && banner_t == 0) {
        xp -= xp_need();
        plv++;
        pick_upgrades();
        lvl_sel = 0;
        lvlup = 1;
        levelup_screen();
        sfx(SFX_PICKUP);
    }
    bg_x[1] = cam;
    bg_x[2] = cam >> 1;
    bg_x[3] = cam >> 2;
    hud();
    draw_world();
    return EV_NONE;
}
