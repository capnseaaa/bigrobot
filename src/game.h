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

enum { U_HAND, U_EYE, U_STOMP, U_SLAM, U_ARMOR, U_THUNDER, U_SPEED, U_COUNT };
extern u8 up_lv[U_COUNT];
extern int level;          // 1..15
extern u32 squished;
void save_game(void);

enum { SC_TITLE, SC_HOWTO, SC_CARD, SC_PLAY, SC_UPGRADE, SC_LAVA, SC_GAMEOVER, SC_WIN, SC_DEV };
void goto_scene(int s);

// ---- play.c: the level itself
void play_enter(void);
int play_update(void);
enum { EV_NONE, EV_CLEAR, EV_DEAD, EV_BOOM, EV_WIN };

// ---- sound.c
void snd_init(void);
void snd_tick(void);
void sfx(int id);
void music(int song);
extern int music_on;
enum { SFX_LASER, SFX_EYE, SFX_STOMP, SFX_SLAM, SFX_BOOM, SFX_CLAP, SFX_HIT, SFX_SQUISH, SFX_PICKUP,
       SFX_HURT, SFX_SELECT, SFX_BIGBOOM, SFX_WARN };
enum { SONG_NONE, SONG_TITLE, SONG_LEVEL, SONG_BOSS, SONG_WIN, SONG_LAVA };
