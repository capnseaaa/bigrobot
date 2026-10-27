// Shared declarations for The Big Giant Robot.
#pragma once
#include "types.h"
#include "gba.h"
#include "art.h"

#define SCREEN_W 240
#define SCREEN_H 160

// ---- main.c: system, video, text, save, scenes
extern u32 frame;
extern u16 keys, pressed;
u32 rnd(void);
int rndr(int n);
int iabs(int v);
int idiv(int a, int b);

void spr(int x, int y, int shape, int size, int tile, int pal, int hf, int vf);
void upload(void* dst, const void* src, int words);
extern int shake_x, shake_y;
extern int bg_x[4];

void txt_clear(void);
void txt_clear_rows(int y0, int y1);
void txt(int x, int y, const char* s, int style);
void txt_center(int y, const char* s, int style);
void txt_big(int x, int y, const char* s);
void txt_big_center(int y, const char* s);
void put_tile(int x, int y, u16 t);
void num_str(char* out, int v);
void fade(int mode, int v);           // mode 0 off, 1 to white, 2 to black; v 0..16
void set_theme_pal(int theme, int redshift);

extern u16 grad[160];
extern volatile int grad_on;
extern volatile u32 vblanks;

#define LAST_LEVEL 21       // the final level: every boss again, then the Mega Robot
#define MEGA_ID BOSS_COUNT  // boss index of the Mega Robot

enum { U_HAND, U_EYE, U_STOMP, U_SLAM, U_ARMOR, U_THUNDER, U_SPEED, U_POWER, U_COUNT };
#define U_REPAIR U_COUNT    // offered when fewer than three upgrades are left
extern u8 up_lv[U_COUNT];
extern int level;          // 1..LAST_LEVEL
extern u32 squished;
// dev menu (L+R+B in a level): test switches, cleared by a new game
enum { DV_NOENEMY, DV_GOD, DV_ONEHIT, DV_NOCOOL, DV_SAFEEYE, DV_FAST, DV_COUNT };
extern u8 dev_sw[DV_COUNT];
extern int dev_run;        // no saving for this run
void max_upgrades(void);
extern int plv, xp;        // player level and experience toward the next one
int xp_need(void);
void save_game(void);

// upgrade picker (shared by the between-levels screen and the level-up popup)
extern int up_choice[3], up_count;
void pick_upgrades(void);
void draw_upgrade_choices(int y0, int sel, int panel);
int take_upgrade(int sel);

enum { SC_TITLE, SC_HOWTO, SC_CARD, SC_PLAY, SC_UPGRADE, SC_LAVA, SC_GAMEOVER, SC_WIN, SC_DEV };
void goto_scene(int s);

// ---- play.c: the level itself
void play_enter(void);
int play_update(void);
enum { EV_NONE, EV_CLEAR, EV_DEAD, EV_BOOM, EV_WIN, EV_GOTO };

// ---- sound.c
void snd_init(void);
void snd_tick(void);
void sfx(int id);
void music(int song);
extern int music_on;
enum { SFX_LASER, SFX_EYE, SFX_STOMP, SFX_SLAM, SFX_BOOM, SFX_CLAP, SFX_HIT, SFX_SQUISH, SFX_PICKUP,
       SFX_HURT, SFX_SELECT, SFX_BIGBOOM, SFX_WARN };
enum { SONG_NONE, SONG_TITLE, SONG_LEVEL, SONG_BOSS, SONG_WIN, SONG_LAVA };
