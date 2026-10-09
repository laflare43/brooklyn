# Pitkin Ave / Van Siclen / Bradford / Glenmore block — Roblox models

A recreation of the real block around **Fiorentino Plaza** (East New York, Brooklyn),
generated from the OpenStreetMap export in `data/map.osm`. Footprints, positions,
street layout and building heights come straight from that map data.

> **Not tested in Studio yet.** These files were generated and validated by script
> (well-formed XML, unique referents, orthonormal rotations, matching MaterialVariant
> base materials) and previewed with a software renderer, but they have not been opened
> in Roblox Studio. If something imports wrong, tell me what Studio says.

## Files

| File | What it is | Parts |
|---|---|---|
| `Block_Streets.rbxmx` | ground slab, roads, curbs, sidewalks, paths, crosswalks, markings, lawns, pools, lamps, hydrants, signals, trees, ~190 parked cars | ~2.9k |
| `Block_Project_FiorentinoPlaza.rbxmx` | the 9 housing-complex buildings (red brick, stepped bays, entrances, bulkheads) | ~7.2k |
| `Block_Buildings_West.rbxmx` | surrounding buildings, west half (rowhouses, Pitkin Ave storefronts) | ~7.5k |
| `Block_Buildings_East.rbxmx` | surrounding buildings, east half | ~6.8k |
| `MaterialVariants.rbxmx` | the 8 MaterialVariants (no textures yet) | – |
| `MaterialVariants_Setup.luau` | command-bar script that builds the variants with your uploaded texture ids | – |
| `Studio_Setup.luau` | command-bar script: removes the Baseplate, sets daylight lighting and StreamingEnabled | – |

All files use absolute coordinates around one origin (the map centre, lat 40.672833,
lon -73.891728), so they line up when inserted together.

## Scale and orientation

* **1 stud = 0.30 m.** A 4-storey building is about 42 studs; a door is about 7 studs.
* **+X = east, −Z = north, +Y = up.** (Roblox's default "north" is −Z.)
* Everything is anchored. Walls are hollow shells; interiors are not modelled.

## Import (about 5 minutes)

1. Open your place in Studio and paste `Studio_Setup.luau` into the command bar (View > Command Bar) and
   press Enter. It deletes the default **Baseplate** (the block brings its own ground), sets up daylight
   (Future lighting, atmosphere, soft shadows) and turns on StreamingEnabled. Also move or delete the
   default SpawnLocation: it sits at the map centre, which is covered by a road or building.
2. In the Explorer, right-click **Workspace → Insert from File…** and pick the four
   `Block_*.rbxmx` files, one at a time. They drop in at the right positions.
3. Right-click **MaterialService → Insert from File…** and pick `MaterialVariants.rbxmx`.
   (Or paste `MaterialVariants_Setup.luau` into the command bar and press Enter.)
4. Total is about 24k parts. `Studio_Setup.luau` already enables StreamingEnabled, so Studio and players
   only load what is nearby.

## Making the MaterialVariants look right (textures)

The variants exist after step 3 but show the plain base materials until the texture maps
are uploaded, because I can't upload images to Roblox for you.

1. In Studio open **View → Asset Manager → Images → Bulk Import** and select every PNG in
   `textures/` (22 files, 6.7 MB).
2. For each uploaded image, right-click → **Copy ID**.
3. Put the ids in `textures/asset_ids.json` (a template is in that folder) and run
   `python3 tools/make_block.py --only variants`, **or** type them into the `IDS` table at the
   top of `MaterialVariants_Setup.luau` and run it in the command bar.

The colour maps are near-neutral *luminance* patterns that multiply with each part's real
colour, so brick stays brick-red and asphalt stays dark. If the bumps look inverted, regenerate
the normal maps with `--textures --flip-green`.

## What is real and what is generic

| Real (from the map) | Generic NYC treatment (not in the map) |
|---|---|
| building footprints, down to the 0.6 m brick-pier jogs | window layout, window styles, AC units, blinds |
| building heights → number of storeys (3.1 m each) | entrances, stoops, door colours |
| street centrelines, widths (measured from the mapped sidewalks), one-way flags | store signs (colour bands, **no text**), roll gates, awnings |
| sidewalks, crosswalks (zebra/ladder), traffic-signal crossings | fire escapes on 3+ storey older buildings |
| parks, garden, schoolyard, three pools, the Fiorentino lawn | street trees, lamps, hydrants, manholes (procedural) |
| | brick colours, roof equipment |

Buildings are classified automatically: **project** (inside the Fiorentino Plaza outline, or a
large slab right beside it), **commercial** (Pitkin Ave frontage), **row** (rowhouses),
**school**, and **accessory** (garages and sheds). Each model is named with its type and address
or OSM id, so individual buildings are easy to find and replace.

## Regenerating

```
python3 tools/make_block.py --osm data/map.osm --out models/block            # everything
python3 tools/make_block.py --only streets                                    # one piece
python3 tools/make_block.py --textures                                        # rebuild the PNGs
python3 tools/make_block.py --stud-m 0.28                                     # different scale
python3 tools/validate_rbxmx.py models/block/*.rbxmx                          # structural checks
```

## Known limits

* Four buildings that sit outside the mapped area (including the J.H.S. 292 school, 99 % outside the
  export) are left out: this export has no streets or sidewalks around them. Export a larger area from
  openstreetmap.org to include them.
* Nothing is modelled inside the buildings. Walls are hollow shells; windows are dark glass.
* Facade layouts are generic. Photos of the real buildings would let me match window styles, brick
  tone, entrances and fences exactly.
