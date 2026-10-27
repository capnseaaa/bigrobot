# The Big Giant Robot

A heavy-metal robot smash-'em-up for the Game Boy Advance, played in emulators (built for the R36 Ultra handheld).

You are a huge, cool gray, slightly angry robot in black sunglasses. March through 21 levels, squish the little armored guys, and beat a boss at the end of every level. On level 21 there are no little guys: six of the toughest bosses come back one after another, and then the Mega Robot.

## Story
Every new save starts with an intro (after 3 seconds, hold B to skip it). The world is burning and the people call for the Big Giant Robot. Asteroids hit the Earth, and the bad guys and the Mega Robot came with them. Then the robot, hooked up to the power lines, switches on: its eyes light up red, it nods its sunglasses down, and they sparkle. Beat the Mega Robot and the ending plays: the Mega Robot goes down behind the city, the robot walks in, the crowd cheers, and there are fireworks. Then the stats.

## Controls
| Button | What it does |
|---|---|
| D-pad | The robot marches right on its own. RIGHT = faster, LEFT = stop, UP/DOWN = move on the street |
| A | Stomp (squishes the little guys in front of you) |
| B | Blue hand lasers: short range, aim at the nearest enemy in front, only scratch bosses |
| R | Red eye lasers: he lifts his sunglasses and fires from his eyes |
| L | Slam: jump up and smash the ground |
| L + R | Thunderclap: stuns every enemy (no damage). Only 2 per level (more with upgrades) |
| START | Pause (SELECT in the pause menu turns the music on or off) |

**Eye lasers are for bosses** (they do the real damage to them). If they hit one of the little guys, the whole world explodes and turns into a lava field. Then pick KEEP MY UPGRADES (back to level 1 with your upgrades) or START OVER.

## Game
- The little guys look like War Machine suits in six colors (gunmetal, red, gold, blue, green, purple). All colors have the same stats. They walk or fly toward you from the right, but never higher than half the robot's height.
- Some little guys need a certain move. SHIELD guys (from level 2): lasers bounce off, so stomp or slam them (a thunderclap drops their shields). SPIKE guys (from level 4): stomping them hurts you, so laser them. HEAVIES (from level 7): only a slam takes them down. The little guys get tougher and come in bigger groups as the levels go on.
- Every level ends with a boss about 80% of the robot's size. Each has four attacks, from shots, spreads, lobs, rain from the sky, charges and jumps to shockwaves down your lane (change lanes), triple charges, warping behind you and calling in backup. Below half health a boss goes into RAGE MODE: red, faster, harder. The bosses: Iron Mauler, Sawblade, Blaze Horn, Spike Guy (he shoots spikes), Volt Skull, Rocket Raven, Chrome Crusher, Magma Maw, Frost Fang, Venom Vat, Doom Drill, Grim Reaper, Heavy Metal, Steel Titan, Blizzard Beast, Neon Ninja, Scrap King, Cyclops, Dragon-X, Inferno King.
- The Mega Robot has three phases: at 2/3 health it calls in backup and gets angry, at 1/3 its armor goes up and only eye lasers hurt it.
- Health hearts drop from the sky as you march and from beaten enemies. Bosses drop a big health cell. You start every level at full health.
- After every boss, pick one of three upgrades: Hand Lasers, Eye Lasers, Stomp, Slam, Armor, Thunderclap, Speed, Power (+25% boss damage).
- Every enemy you beat gives XP. A full XP bar pauses the game: LEVEL UP! and you pick another upgrade.
- Seven areas with three levels each: Burning City, Night Storm, Wasteland, Steel Factory, Ice Age, Neon Nights, Hellfire. Each has its own weather (embers, rain and lightning, dust, snow).
- NEW GAME asks NORMAL or HARD. Hard: bosses have 50% more health and attack more often, more little guys come at you, every hit hurts 50% more, and health hearts drop less often.
- The game saves at the start of every level and when you win. CONTINUE on the title screen picks up there.
- STATS (on the title screen, and after the ending): mode, level, play time, little guys squished, bosses beaten, player level, robot downs and worlds ended.
- Secret level select: on the title screen hold L + R and press SELECT. There, L maxes every upgrade and R turns the normal enemies off (bosses only).
- Dev mode, for testing: in a level press L + R + B together. UP/DOWN pick, A sets, B closes. Switches: ENEMIES, GOD MODE, ONE-HIT BOSSES, NO COOLDOWNS, SAFE EYES (the eye beam pops little guys instead of ending the world), FAST WALK. Actions: SKIP TO BOSS, CLEAR LEVEL, LEVEL UP, MAX UPGRADES, GO TO LEVEL (LEFT/RIGHT picks the number). The switches stay on until a new game. Once dev mode or the level select is used, that run never saves.

## Build
Needs `arm-none-eabi-gcc` and Python 3 with Pillow.

```sh
sh bigrobot/build.sh          # -> bigrobot/bigrobot.gba
```

Tests need `libmgba`: `sh bigrobot/test/run.sh test/play.txt` plays a scripted run and saves screenshots (also `boss.txt`, `boom.txt`, `clear.txt`, `final.txt`, `dead.txt`, `spike.txt`, `new.txt`, `walk.txt`, `bossonly.txt`, `devmenu.txt`, `devmenu2.txt`, `hard.txt`, `stats.txt`, `variants.txt`, `ninja.txt`, `titan.txt`, `mega.txt`, `intro.txt`, `skip.txt`; `migrate.txt` loads an old save given in `HARNESS_SAV`).

No external GBA libraries. All art (robot, enemies, bosses, backgrounds, the metal font, the title, lava, intro and ending pictures) is drawn in code by `tools/make_art.py`; previews land in `art/`.
