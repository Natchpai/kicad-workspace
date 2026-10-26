# Footprint spec (make_footprint.py)

One JSON object per footprint. All sizes in mm, from the datasheet. Coordinates: x right, y down (top view), origin at the footprint origin (package center unless `body.at` moves the body). `rows`, `grid`, `pads` and `ep` can be combined.

Every `at`, tab, via `at` and aperture position is an absolute footprint coordinate. Only the computed layouts are relative: `rows` and `grid` around their `at`, and via `grid` and paste `grid` around the exposed-pad center. Bad values (missing drill, drill bigger than the pad, size ≤ 0, ratio outside 0 to 0.5, a string where a number belongs) stop the script with `spec error`.

## Header

| Key | Meaning |
|---|---|
| `name` | Footprint name, equal to the output file name. Required. |
| `descr`, `tags` | Optional. Footprint description and keywords. Put the datasheet document and land-pattern drawing number in `descr`. |
| `datasheet` | Optional. Datasheet property URL. |
| `attr` | `smd` or `through_hole`. Default: `through_hole` when any non-via THT pad exists, else `smd`. |
| `body` | `{"x", "y", "h", "at"}`. Required. Package body size in the top view: `x` across the page, `y` down it. Dual rows sit left and right, so for SOIC and SOT-23 `x` is the lead-to-lead side. `at` = body center when it is not the origin (connectors with pin 1 at the origin). `h` is for the record only. Drives fab, silk and courtyard. Polarized capacitors: `chamfer` cuts both pin 1 side corners of the fab and silk outline (the base plate shape), `d` draws the can circle on F.Fab. |
| `model` | 3D model path, written as given (for example `${KICAD10_3DMODEL_DIR}/Package_SON.3dshapes/....step`). |
| `fab_pin1` | Pin 1 mark on F.Fab, one per footprint: `dot` (default; filled dot, radius by the short body side: under 1.5 mm 0.1, under 3.2 mm 0.15, under 3.9 mm 0.2, under 10 mm 0.25, else 0.3. Placed on the body diagonal 3 radii in from the pin 1 corner; for pin 1 in the middle of a side (diodes, LEDs) level with pin 1 at its pad's outer end, radius + 0.05; for a `grid` body of 5 mm or more on ball A1, radius 0.35), `arrow` (connectors and DIP switches, KLC F5.2: filled arrow with a 0.1 mm line on pad 1's long axis, on the body side, tip 0.2 mm off the pad end, pointing at the pad; 0.3 long x 0.4 wide, or 0.5 x 0.6 when the pad is 1 mm or wider), `plus` (polarized capacitors: a drawn 0.8 mm + at the silk "+"; the default when `silk_pin1` is `plus`) or `none` (non-polarized R/C/L; also turns the silk mark off). |
| `silk_pin1` | Pin 1 mark on F.SilkS: `arrow` (default; filled arrow 0.3 long x 0.4 wide, 0.1 mm line, beside pin 1 outside the silk outline, level with pin 1, pointing at it), `plus` (polarized SMD capacitors, KLC F5.1: a visible `Polar` property "+" on F.SilkS, 1 x 1 mm, 0.15 mm thick, over the outer end of pad 1 and past the pad edge toward the pin 1 corner; the default when `fab_pin1` is `plus`) or `none` (default when `fab_pin1` is `none`). No dot on silkscreen. The mark sits on the body side pin 1 is nearer to (left or right on a tie) and moves out until it is `silk_clearance` from copper and clear of the silk outline. |
| `courtyard` | Courtyard clearance. Default 0.25; 0.15 when the body is under 1.5 mm in both x and y (as the stock KiCad generators read KLC F5.3); 1.0 with `grid`. Use 0.5 for connectors, canned capacitors and crystals (KLC F5.3). The courtyard then grows by the same amount on every side until it holds the silk pin 1 mark (KLC F5.1). |
| `options` | Override the drawing defaults below. |

`options` defaults: `pad_ratio` 0.25, `ep_ratio` 0 (square exposed pads: rounded tab and pad primitives leave notches where they join), `paste_ratio` 0.1, `max_radius` 0.25 (corner radius cap, mm), `silk_width` 0.15, `silk_offset` 0.1 (silk outline at body + this), `silk_clearance` 0.2, `silk_min_len` 0.1, `fab_width` 0.1, `crtyd_width` 0.05, `marker_size` 0.28 (silk pin 1 arrow length, rounded to 0.3; the arrow is 2/3 of that per side, 0.4 mm wide), `marker_width` 0.1 (silk pin 1 arrow line).

DFM house rules (the script stops with `spec error` below them): `silk_width` and `silk_clearance` at least 0.15 mm; `marker_width` at least 0.1 mm, and under 0.15 mm only when `marker_size` is over 0.15 mm. REF** on F.SilkS is 1 x 1 mm, 0.15 mm thick. `${REFERENCE}` on F.Fab is 1 x 1 mm, 0.1 mm thick; when 5 characters do not fit inside the body with 0.1 mm to spare (0.9 × size per character), it takes the largest size that fits, in 0.05 mm steps (C0402: 0.15 mm, 3x3 QFN: 0.6 mm); a smaller hand-set size also passes, with a thickness of 15% of the size. A hand-set text with height and width apart (for example 0.7 x 0.65) is a house style to tell footprints apart; `fp_check.py` reports it as INFO and does not check it.

F.SilkS and F.Fab points and text positions sit on a 0.05 mm grid (house rule, for hand edits). Silk lines and the pin 1 mark round away from the body and copper, so clearances only grow; the mark's center line rounds to the nearest node, so it can be up to 0.025 mm off pin 1. The fab outline rounds to the nearest node, so it can differ from `body` by up to 0.025 mm; the fab pin 1 dot diameter is a multiple of 0.1 mm. The courtyard stays on the 0.01 mm grid (KLC F5.3).

## Pad keys shared by `rows`, `grid` and `pads`

Put these on the row group, the `grid` object or the single pad they apply to.

- `shape`: `roundrect` (SMD default), `rect` (only when the datasheet asks for square corners), `oval`, `circle` (grid default when the pad is round; needs w = h, since KiCad draws a circle from the x size only; an unequal grid pad defaults to `oval`).
- `ratio`: roundrect ratio. House style 0.1 to 0.25; the script accepts 0 to 0.5.
- `radius`: corner radius in mm, as the datasheet gives it (`(R0.05) ALL PAD CORNERS`); turned into the ratio radius / shorter pad side. Overrides `ratio`.
- `paste`: `true` (1:1, default), `false` (no paste layer), or `{"margin": -0.05}` / `{"ratio": -0.1}` for a pad paste margin.
- `mask_margin`: pad solder mask margin. Leave it out unless the datasheet asks for one (KLC F4.6).
- `fab_property` (`grid` and `pads`): KLC F6.3 fab property, `bga`, `heatsink` or `mechanical`. `grid` defaults to `bga` (set `null` for an LGA); use `mechanical` for THT shield and mounting pads. `zone_connect` (`pads`) sets the zone connection (2 = solid, the default for `heatsink`).

Polarized SMD capacitor (aluminum or polymer can):

```json
{"name": "CP_Elec_Panasonic_OS-CON-SVPK_6.3x6.3mm_H5.9mm", "silk_pin1": "plus",
 "body": {"x": 6.6, "y": 6.6, "d": 6.3, "chamfer": 1.1},
 "pads": [{"number": "1", "at": [-2.8, 0], "size": [3.5, 1.6]}, {"number": "2", "at": [2.8, 0], "size": [3.5, 1.6]}]}
```

## `rows`: dual or quad leads

List of row groups. Pin 1 at the top left, counterclockwise.

| Key | Meaning |
|---|---|
| `layout` | `dual` (left column top to bottom, then right column bottom to top) or `quad` (left, bottom, right, top). |
| `pins` | Dual: total pins (even). |
| `pins_x`, `pins_y` | Quad: pins on the top/bottom sides and on the left/right sides. |
| `pitch` | Pad pitch. |
| `span` / `span_x`, `span_y` | Center-to-center distance between opposite pad rows. Dual takes `span`; quad takes `span` for both axes or `span_x` (left to right rows) and `span_y` (top to bottom rows). |
| `pad` | `[L, W]`: length along the lead, width across it. Top and bottom pads are turned 90°. |
| `numbers` | Optional explicit number list in place order; `null` skips a place (depopulated pin). |
| `start` | First number when `numbers` is absent (default 1). |
| `at` | Row group center offset. |

```json
{"name": "SOIC-8_3.9x4.9mm_P1.27mm", "body": {"x": 3.9, "y": 4.9},
 "rows": [{"layout": "dual", "pins": 8, "pitch": 1.27, "span": 4.95, "pad": [1.95, 0.6]}]}
```

## `grid`: BGA and LGA

| Key | Meaning |
|---|---|
| `rows`, `cols` | Grid size (rows along y, columns along x). |
| `a1` | Corner of A1 in the top view: `top-left` (default), `top-right`, `bottom-left`, `bottom-right`. KLC F4.2 wants top-left; use another corner only to keep the datasheet orientation, and say why. |
| `letters` | `rows` (default: letters count down the rows) or `cols` (letters count across the columns). |
| `pitch` | Number, or `[px, py]`. |
| `pad` | Diameter, or `[w, h]`. |
| `empty` | Positions with no ball, for example `["C3", "C4"]`. |
| `skip_letters` | Row letters not used. Default `IOQSXZ` (JEDEC); after Z come AA, AB. |
| `at` | Grid center offset from the origin (for a grid that is off the body center, give `body.at` or this). |

```json
{"name": "BGA-64_9.0x9.0mm_Layout10x10_P0.8mm", "body": {"x": 9, "y": 9},
 "grid": {"rows": 10, "cols": 10, "pitch": 0.8, "pad": 0.5, "empty": ["C3", "C4", "..."]}}
```

## `pads`: free list

Connectors, modules, mounting pads, odd shapes.

| Key | Meaning |
|---|---|
| `number` | Pad number. Mounting pads share one number (for example `MP`). |
| `type` | `smd` (default), `thru_hole`, `np_thru_hole` (number is left empty). |
| `at` | `[x, y]` or `[x, y, rot]`. |
| `size` | Number or `[w, h]`. |
| `drill` | Number, or `[w, h]` for an oval drill. Required for `thru_hole` and `np_thru_hole`; at most the pad size. The script warns below a 0.15 mm annular ring (KLC F7.5). |
| `layers` | Override the layer list (for example `["B.Cu", "B.Mask", "B.Paste"]` for a bottom pad). |

THT shape defaults to `circle` for a round pad, else `oval`. KLC F7.3: give pin 1 `"shape": "roundrect"` (or `rect`) on polarized THT parts.

```json
{"name": "JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical", "courtyard": 0.5,
 "body": {"x": 7.4, "y": 5.75, "at": [1.25, 0.525]},
 "pads": [{"number": "1", "type": "thru_hole", "shape": "roundrect", "at": [0, 0], "size": [1.7, 2], "drill": 1},
          {"number": "2", "type": "thru_hole", "at": [2.5, 0], "size": [1.7, 2], "drill": 1}]}
```

## `ep`: exposed pads, thermal vias and stencil

A list (one object is also accepted).

| Key | Meaning |
|---|---|
| `number` | Pad number. Vias get the same number (KLC F4.3). |
| `size`, `at` | Main pad size and center. |
| `tabs` | `[[cx, cy, w, h], ...]`: extra copper joined to the pad. The pad becomes one custom pad with rectangle primitives. |
| `ratio` / `radius` | Corner ratio (default `ep_ratio`, 0 = square), or corner radius in mm. |
| `vias` | `{"at": [[x, y], ...]}` or `{"grid": [nx, ny], "pitch": [px, py]}`, plus `drill` and `dia`. Datasheets often give only the drill; label the `dia` you choose `ASSUMED`. KLC F4.4.6: drill 0.2 to 0.3 mm. |
| `bottom` | B.Cu pad under the thermal vias, no B.Mask (KLC F4.4.2). Default `true` (exposed-pad size) when `vias` is given; `[w, h]` for another size; `false` when the datasheet says not to, or to match a stock footprint without one. |
| `mask_margin` | Solder mask margin of the exposed pad. |
| `paste` | Required. See below. |

The exposed pad, its B.Cu pad and its vias get the `heatsink` fab property and solid zone connection (KLC F6.3).

`paste.mode`:
- `explicit`: `"apertures": [[cx, cy, w, h], ...]` from the datasheet stencil drawing. Preferred when the datasheet gives one.
- `grid`: `"n": [nx, ny], "coverage": 0.5` splits the main pad (not the tabs) into nx × ny cells and scales each window by √coverage. The result is `ESTIMATED`; the windows can land on vias, so read the via-under-paste warnings and switch to `explicit` to avoid them. KLC F6.3 wants 50 to 80% (65% recommended) unless the datasheet says otherwise; the summary prints the coverage of pad + tabs and of the main pad alone.
- `pad`: paste on the whole pad (1:1).
- `none`: no paste.
- `ratio`: aperture corner ratio (default `paste_ratio`), or `radius` in mm (`(R0.05) TYP` on a stencil drawing). Coverage is computed from the aperture rectangles; corner rounding is not subtracted (under 1% at ratio 0.1).

Apertures are written as paste-only pads with an empty number (stock KiCad style).

```json
{"name": "Texas_DRC0010J_ThermalVias", "descr": "Texas DRC0010J, VSON-10 3x3mm, 0.5mm pitch, TI SLVSGF4C land pattern 4218878/B",
 "body": {"x": 3.0, "y": 3.0, "h": 1.0},
 "model": "${KICAD10_3DMODEL_DIR}/Package_SON.3dshapes/VSON-10-1EP_3x3mm_P0.5mm_EP1.65x2.4mm.step",
 "rows": [{"layout": "dual", "pins": 10, "pitch": 0.5, "span": 2.8, "pad": [0.6, 0.24]}],
 "ep": [{"number": "11", "size": [1.65, 2.4],
   "tabs": [[-0.25, -1.45, 0.25, 0.5], [0.25, -1.45, 0.25, 0.5], [-0.25, 1.45, 0.25, 0.5], [0.25, 1.45, 0.25, 0.5]],
   "vias": {"at": [[-0.575, 0], [0.575, 0], [0, -0.95], [0, 0.95]], "drill": 0.2, "dia": 0.5},
   "paste": {"mode": "explicit", "apertures": [[0, -0.63, 1.5, 1.06], [0, 0.63, 1.5, 1.06],
     [-0.25, -1.53, 0.25, 0.34], [0.25, -1.53, 0.25, 0.34], [-0.25, 1.53, 0.25, 0.34], [0.25, 1.53, 0.25, 0.34]]}}]}
```

## Output

KiCad 10 format (`version 20260206`). UUIDs are uuid5 of the name, so the same spec gives the same bytes. Line endings are LF by default (KLC G1); `--newline auto` copies the line ending of a `.kicad_mod` already in the output folder, `crlf` writes CRLF.
