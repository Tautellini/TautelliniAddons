# WorldLight changelog

## 1.1.0

**New**
- Icon in the in-game addon list.
- "Custom day and night times" with a start hour for night and day in realm time. On by default, with night from 20:00 to 6:00. Turn it off to follow the server's own switch as before.

## 1.0.2

**New**
- "Tint indoors" and "Tint in instances" settings, if you want the tint there too.
- "Indoor fade" setting for how long the tint takes to fade out and back in when you enter or leave a building or instance. The default is now 2 seconds.

**Improved**
- `/worldlight status` now shows whether you are outdoors, indoors or in an instance, and whether the tint is off there.

**Fixed**
- The tint now turns off when you walk into a building such as a bank. Before, it only noticed indoor areas after a zone change.

## 1.0.1

**New**
- Light color setting with Blizzard's color picker. Brightening now uses a cool moonlight color by default, which looks less foggy than white. Choose white to get the old look back.

## 1.0.0

First release.

- Day and night brightness for the game world, UI untouched
- Follows the server's day and night cycle
- Smooth fade with adjustable length
- Off indoors and in instances
- Settings panel and slash commands
