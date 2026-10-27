# The Big Giant Robot

A heavy-metal robot smash-'em-up for the Game Boy Advance, played in emulators (built for the R36 Ultra handheld).

You are a huge, cool gray, slightly angry robot in black sunglasses. March through 21 levels, squish the little armored guys, and beat a boss at the end of every level. On level 21 there are no little guys: all 20 bosses come back one after another, and then the Mega Robot.

## Controls
| Button | What it does |
|---|---|
| D-pad | The robot marches right on its own. RIGHT = faster, LEFT = stop, UP/DOWN = move on the street |
| A | Stomp (squishes the little guys in front of you) |
| B | Blue hand lasers (aim at the nearest enemy in front) |
| R | Red eye lasers: he lifts his sunglasses and fires from his eyes |
| L | Slam: jump up and smash the ground |
| L + R | Thunderclap: stuns every enemy (no damage). Only 2 per level (more with upgrades) |
| START | Pause (SELECT in the pause menu turns the music on or off) |

**Eye lasers are for bosses.** If they hit one of the little guys, the whole world explodes and turns into a lava field. Then pick KEEP UPGRADES (back to level 1 with your upgrades) or START OVER.

## Game
- The little guys look like War Machine suits in six colors (gunmetal, red, gold, blue, green, purple). All colors have the same stats. They walk or fly toward you from the right, but never higher than half the robot's height.
- Every level ends with a boss about 80% of the robot's size: Iron Mauler, Sawblade, Blaze Horn, Spike Guy (he shoots spikes), Volt Skull, Rocket Raven, Chrome Crusher, Magma Maw, Frost Fang, Venom Vat, Doom Drill, Grim Reaper, Heavy Metal, Steel Titan, Blizzard Beast, Neon Ninja, Scrap King, Cyclops, Dragon-X, Inferno King.
- Health hearts drop from the sky as you march and from beaten enemies. Bosses drop a big health cell. You start every level at full health.
- After every boss, pick one of three upgrades: Hand Lasers, Eye Lasers, Stomp, Slam, Armor, Thunderclap, Speed, Power (+25% boss damage).
- Every enemy you beat gives XP. A full XP bar pauses the game: LEVEL UP! and you pick another upgrade.
- Seven areas with three levels each: Burning City, Night Storm, Wasteland, Steel Factory, Ice Age, Neon Nights, Hellfire. Each has its own weather (embers, rain and lightning, dust, snow).
- The game saves at the start of every level. CONTINUE on the title screen picks up there.
- Secret level select: on the title screen hold L + R and press SELECT. There, L maxes every upgrade and R turns the normal enemies off (bosses only).
- Dev mode, for testing: in a level press L + R + B together. UP/DOWN pick, A sets, B closes. Switches: ENEMIES, GOD MODE, ONE-HIT BOSSES, NO COOLDOWNS, SAFE EYES (the eye beam pops little guys instead of ending the world), FAST WALK. Actions: SKIP TO BOSS, CLEAR LEVEL, LEVEL UP, MAX UPGRADES, GO TO LEVEL (LEFT/RIGHT picks the number). The switches stay on until a new game. Once dev mode or the level select is used, that run never saves.

## Build
Needs `arm-none-eabi-gcc` and Python 3 with Pillow.

```sh
sh bigrobot/build.sh          # -> bigrobot/bigrobot.gba
```

Tests need `libmgba`: `sh bigrobot/test/run.sh test/play.txt` plays a scripted run and saves screenshots (also `boss.txt`, `boom.txt`, `clear.txt`, `final.txt`, `dead.txt`, `spike.txt`, `new.txt`, `walk.txt`, `bossonly.txt`, `devmenu.txt`, `devmenu2.txt`; `migrate.txt` loads an old save given in `HARNESS_SAV`).

No external GBA libraries. All art (robot, enemies, bosses, backgrounds, the metal font, the title and lava screens) is drawn in code by `tools/make_art.py`; previews land in `art/`.
