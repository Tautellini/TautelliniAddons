<span style="color:#3598db"><strong>Day and night brightness for the game world. Your UI stays untouched.</strong></span>

WorldLight makes the world of WoW Forever brighter or darker depending on whether it is day or night. Action bars, unit frames, chat, the map, tooltips and menus keep their normal look.

***

### Features

*   Separate brightness for day and night, from -100 (darker) to +100 (brighter)
*   Fades out indoors and in dungeons and raids, where the game has no day or night.
*   Brightening uses a moonlight color tint by default. Pick any color you like in the settings.
*   Night and day start at the realm time hours you choose, by default night from 20:00 to 6:00
*   Or follows the server's own day and night, the same signal that drives the sun and moon icon on the minimap
*   Smooth fade between day and night, with adjustable length

***

### Settings

Find them under Options > AddOns > WorldLight.

| Setting           |Default    |What it does                                                                    |
| ----------------- |---------- |------------------------------------------------------------------------------- |
| Enabled           |on         |turns WorldLight on or off                                                      |
| Day brightness    |0          |-100 darker to +100 brighter during the day                                     |
| Night brightness  |+30        |-100 darker to +100 brighter at night                                           |
| Light color       |moonlight  |color of the light added when brightening                                       |
| Fade length       |60 minutes |how long the change takes after day turns into night and back                   |
| Tint indoors      |off        |keep the tint inside buildings and caves                                        |
| Tint in instances |off        |keep the tint in dungeons and raids                                             |
| Indoor fade       |2 seconds  |how long the tint takes to fade out and back in at doors and instance entrances |

***

### How WorldLight differs from gamma mods

Gamma mods work by changing the game's Gamma setting. That setting applies to the whole screen, so every change also brightens or darkens your interface. WorldLight never touches Gamma. It places a tint layer between the 3D world and the interface, so only the world changes. At the moment, brightening behaves much like the in-game Brightness option, but it is applied automatically, uses a soft moonlight color by default and stays separate from your graphics settings.

|                           |Traditional Gamma                                        |WorldLight                                                                                                |
| ------------------------- |-------------------------------------------------------- |--------------------------------------------------------------------------------------------------------- |
| What changes              |The whole screen, UI included                            |Only the 3D world                                                                                         |
| Your own gamma setting    |Overwritten                                              |Never touched                                                                                             |
| After disabling the addon |Gamma stays at the last value unless the mod restores it |Everything looks exactly as before                                                                        |
| Picture                   |True gamma curve                                         |Tint layer: clean darkening, brightening adds a soft moonlight that looks slightly flatter at high values |

***

### Slash commands

| Command                                            |Effect                                                                |
| -------------------------------------------------- |--------------------------------------------------------------------- |
| <code>/worldlight</code>                           |open the settings                                                     |
| <code>/worldlight on</code> or <code>off</code>    |turn WorldLight on or off                                             |
| <code>/worldlight day &lt;-100 to 100&gt;</code>   |set the day brightness                                                |
| <code>/worldlight night &lt;-100 to 100&gt;</code> |set the night brightness                                              |
| <code>/worldlight status</code>                    |show day or night, your location and whether the tint is active there |

***

### Feedback

Bug reports and ideas are welcome at [https://github.com/Tautellini/TautelliniAddons/issues](https://github.com/Tautellini/TautelliniAddons/issues)

This project will never collect your data and it will always be free.

Wanna support me?

I like a good espresso: [https://ko-fi.com/tautellini](https://ko-fi.com/tautellini)
