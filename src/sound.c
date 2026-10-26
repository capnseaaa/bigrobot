// Sound: effects on channels 1 (square + sweep) and 4 (noise); music on 2 (lead), 3 (bass) and 4 (drums,
// only while no noise effect plays).
#include "game.h"

int music_on = 1;

static int song, step, step_t, noise_t, sq_t, eye_t;

// 16 steps per bar; 0 = rest, 1 = hold. Notes are MIDI numbers.
#define E2 40
#define F2 41
#define G2 43
#define A2 45
#define AS2 46
#define B2 47
#define C3 48
#define D3 50
#define E3 52
#define G3 55
#define B3 59
#define D4 62
#define E4 64
#define FS4 66
#define G4 67
#define A4 69
#define B4 71

typedef struct {
    const u8* bass;
    const u8* lead;
    const u8* drum;   // 1 kick, 2 snare, 3 hat
    int len, speed;
} Song;

// title: a galloping E minor riff
static const u8 t_bass[32] = { E2, 0, E2, E2, E2, 0, E2, E2, G2, 0, G2, G2, A2, 0, A2, A2,
                               E2, 0, E2, E2, E2, 0, E2, E2, D3, 0, D3, D3, C3, 0, B2, 0 };
static const u8 t_lead[32] = { E4, 1, 1, 1, B3, 1, 1, 1, D4, 1, 1, 1, E4, 1, G4, 1,
                               FS4, 1, 1, 1, E4, 1, D4, 1, B3, 1, 1, 1, 1, 1, 0, 0 };
static const u8 t_drum[32] = { 1, 0, 1, 1, 2, 0, 1, 1, 1, 0, 1, 1, 2, 0, 1, 1,
                               1, 0, 1, 1, 2, 0, 1, 1, 1, 0, 1, 1, 2, 0, 2, 2 };
// level: chugging sixteenths
static const u8 l_bass[32] = { E2, E2, E2, E2, E2, E2, G2, E2, E2, E2, E2, E2, AS2, 0, A2, 0,
                               E2, E2, E2, E2, E2, E2, G2, E2, E2, E2, D3, 0, C3, 0, B2, 0 };
static const u8 l_lead[32] = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                               E4, 1, 0, E4, G4, 1, E4, 1, A4, 1, G4, 1, FS4, 1, D4, 1 };
static const u8 l_drum[32] = { 1, 3, 3, 3, 2, 3, 1, 3, 1, 3, 1, 3, 2, 3, 3, 3,
                               1, 3, 3, 3, 2, 3, 1, 3, 1, 3, 1, 3, 2, 3, 2, 2 };
// boss: menacing half steps, double kick
static const u8 b_bass[32] = { E2, E2, F2, E2, E2, E2, F2, E2, G2, G2, F2, 0, E2, 0, E3, 0,
                               E2, E2, F2, E2, E2, E2, F2, E2, AS2, AS2, A2, 0, G2, 0, F2, 0 };
static const u8 b_lead[32] = { E4, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0,
                               B4, 1, 1, 1, AS2 + 24, 1, 1, 1, A4, 1, G4, 1, FS4, 1, 1, 1 };
static const u8 b_drum[32] = { 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1,
                               1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2 };
// win: a major-key fanfare
static const u8 w_bass[32] = { E2, 0, E2, 0, E2, 0, E2, 0, C3, 0, C3, 0, D3, 0, D3, 0,
                               E2, 0, E2, 0, E2, 0, E2, 0, A2, 0, B2, 0, E3, 0, 0, 0 };
static const u8 w_lead[32] = { B3, 1, E4, 1, G4 + 1, 1, B4, 1, 1, 1, A4, 1, B4, 1, 1, 1,
                               B4, 1, A4, 1, G4 + 1, 1, E4, 1, FS4, 1, G4 + 1, 1, E4 + 12, 1, 1, 1 };
static const u8 w_drum[32] = { 1, 0, 3, 0, 2, 0, 3, 0, 1, 0, 3, 0, 2, 0, 3, 3,
                               1, 0, 3, 0, 2, 0, 3, 0, 1, 0, 1, 0, 2, 2, 2, 2 };
// lava: slow doom
static const u8 v_bass[32] = { E2, 1, 1, 1, 1, 1, 1, 1, F2, 1, 1, 1, E2, 1, 1, 1,
                               E2, 1, 1, 1, 1, 1, 1, 1, AS2, 1, 1, 1, A2, 1, 1, 1 };
static const u8 v_lead[32] = { 0 };
static const u8 v_drum[32] = { 1, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0,
                               1, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0 };

static const Song songs[] = {
    { 0, 0, 0, 0, 0 },
    { t_bass, t_lead, t_drum, 32, 7 },
    { l_bass, l_lead, l_drum, 32, 6 },
    { b_bass, b_lead, b_drum, 32, 5 },
    { w_bass, w_lead, w_drum, 32, 7 },
    { v_bass, v_lead, v_drum, 32, 9 },
};

void snd_init(void) {
    REG_SOUNDCNT_X = 0x80;
    REG_SOUNDCNT_L = 0xFF77;
    REG_SOUNDCNT_H = 0x0002;
    // a gritty sawtooth for the bass
    REG_SOUND3CNT_L = 0x40;
    static const u16 wave[8] = { 0x3210, 0x7654, 0xBA98, 0xFEDC, 0x3210, 0x7654, 0xBA98, 0xFEDC };
    for (int i = 0; i < 8; i++) WAVE_RAM[i] = wave[i];
    REG_SOUND3CNT_L = 0x80;
    REG_SOUND3CNT_H = 0;
}

static void noise(int vol, int step, int shift, int div) {
    REG_SOUND4CNT_L = (vol << 12) | (step << 8);
    REG_SOUND4CNT_H = div | (shift << 4) | 0x8000;
}

static void square1(int sweep, int duty, int vol, int step, int freq) {
    REG_SOUND1CNT_L = sweep;
    REG_SOUND1CNT_H = (vol << 12) | (step << 8) | (duty << 6);
    REG_SOUND1CNT_X = freq | 0x8000;
}

void sfx(int id) {
    switch (id) {
    case SFX_LASER: square1(0x2A, 2, 11, 1, 1850); sq_t = 8; break;
    case SFX_EYE: eye_t = 48; sq_t = 50; break;
    case SFX_STOMP: noise(15, 3, 7, 6); noise_t = 20; break;
    case SFX_SLAM: noise(15, 5, 7, 7); noise_t = 34; break;
    case SFX_BOOM: noise(13, 3, 5, 5); noise_t = 18; break;
    case SFX_BIGBOOM: noise(15, 7, 6, 7); noise_t = 44; break;
    case SFX_CLAP: noise(15, 4, 2, 1); noise_t = 26; square1(0x1F, 0, 12, 3, 1950); sq_t = 20; break;
    case SFX_HIT: noise(9, 1, 3, 2); noise_t = 6; break;
    case SFX_SQUISH: noise(12, 2, 5, 3); noise_t = 12; square1(0x0F, 2, 9, 1, 1200); sq_t = 8; break;
    case SFX_PICKUP: square1(0x16, 2, 10, 2, 1700); sq_t = 16; break;
    case SFX_HURT: square1(0x1E, 1, 12, 2, 1500); sq_t = 14; noise(8, 1, 4, 3); noise_t = 6; break;
    case SFX_SELECT: square1(0, 2, 8, 1, 1880); sq_t = 5; break;
    case SFX_WARN: square1(0, 1, 12, 4, 1750); sq_t = 24; break;
    }
}

void music(int s) {
    song = s;
    step = 0;
    step_t = 0;
    if (!s) {
        REG_SOUND2CNT_L = 0;
        REG_SOUND2CNT_H = 0x8000;
        REG_SOUND3CNT_H = 0;
    }
}

void snd_tick(void) {
    if (noise_t) noise_t--;
    if (sq_t) sq_t--;
    if (eye_t) {
        // the eye beam: a buzzing, wobbling low tone
        eye_t--;
        if ((eye_t & 3) == 0) square1(0, 3, 10, 0, (eye_t & 4) ? 1520 : 1560);
        if (eye_t == 0) REG_SOUND1CNT_H = 0;
    }
    if (!song) return;
    const Song* so = &songs[song];
    if (!music_on) {
        REG_SOUND3CNT_H = 0;
        REG_SOUND2CNT_L = 0;
        return;
    }
    if (step_t-- > 0) return;
    step_t = so->speed - 1;
    int b = so->bass[step], l = so->lead[step], d = so->drum[step];
    if (b > 1) {
        REG_SOUND3CNT_H = 0x2000;
        REG_SOUND3CNT_X = note_wv[b] | 0x8000;
    } else if (b == 0) {
        REG_SOUND3CNT_H = 0;
    }
    if (l > 1) {
        REG_SOUND2CNT_L = (8 << 12) | (4 << 8) | (2 << 6);
        REG_SOUND2CNT_H = note_sq[l] | 0x8000;
    } else if (l == 0) {
        REG_SOUND2CNT_L = 0;
        REG_SOUND2CNT_H = 0x8000;
    }
    if (d && !noise_t) {
        if (d == 1) noise(10, 1, 6, 5);
        else if (d == 2) noise(11, 2, 3, 2);
        else noise(4, 1, 1, 0);
    }
    step = (step + 1) % so->len;
}
