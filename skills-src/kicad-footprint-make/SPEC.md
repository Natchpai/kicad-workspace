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
| `body` | `{"x", "y", "h", "at"}`. Required. Package body size in the top view: `x` across the page, `y` down it. Dual rows sit left and right, so for SOIC and SOT-23 `x` is the lead-to-lead side. `at` = body center when it is not the origin (connectors with pin 1 at the origin). `h` is for the record only. Drives fab, silk and courtyard. |
| `model` | 3D model path, written as given (for example `${KICAD10_3DMODEL_DIR}/Package_SON.3dshapes/....step`). |
| `fab_pin1` | Pin 1 mark on F.Fab: `dot` (default; plain body rectangle with a filled dot inside the pin 1 corner, diameter 10% of the short body side, 0.2 to 0.5 mm), `bevel` (KLC F5.2 corner bevel, for connectors and odd shapes) or `none` (non-polarized R/C/L). |
| `courtyard` | Courtyard clearance. Default 0.25; 0.15 when the body is under 1.5 mm in both x and y (as the stock KiCad generators read KLC F5.3); 1.0 with `grid`. Use 0.5 for connectors, canned capacitors and crystals (KLC F5.3). |
| `options` | Override the drawing defaults below. |

`options` defaults: `pad_ratio` 0.25, `ep_ratio` 0 (square exposed pads: rounded tab and pad primitives leave notches where they join), `paste_ratio` 0.1, `max_radius` 0.25 (corner radius cap, mm), `silk_width` 0.15, `silk_offset` 0.1 (silk outline at body + this), `silk_clearance` 0.2, `silk_min_len` 0.1, `fab_width` 0.1, `crtyd_width` 0.05, `marker_size` 0.28.

## Pad keys shared by `rows`, `grid` and `pads`

Put these on the row group, the `grid` object or the single pad they apply to.

- `shape`: `roundrect` (SMD default), `rect` (only when the datasheet asks for square corners), `oval`, `circle` (grid default when the pad is round; needs w = h, since KiCad draws a circle from the x size only; an unequal grid pad defaults to `oval`).
- `ratio`: roundrect ratio. House style 0.1 to 0.25; the script accepts 0 to 0.5.
- `radius`: corner radius in mm, as the datasheet gives it (`(R0.05) ALL PAD CORNERS`); turned into the ratio radius / shorter pad side. Overrides `ratio`.
- `paste`: `true` (1:1, default), `false` (no paste layer), or `{"margin": -0.05}` / `{"ratio": -0.1}` for a pad paste margin.
- `mask_margin`: pad solder mask margin. Leave it out unless the datasheet asks for one (KLC F4.6).
- `fab_property` (`grid` and `pads`): KLC F6.3 fab property, `bga`, `heatsink` or `mechanical`. `grid` defaults to `bga` (set `null` for an LGA); use `mechanical` for THT shield and mounting pads. `zone_connect` (`pads`) sets the zone connection (2 = solid, the default for `heatsink`).

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

KiCad 10 format (`version 20260206`). UUIDs are uuid5 of the name, so the same spec gives the same bytes. `--newline auto` (default) copies the line ending of a `.kicad_mod` already in the output folder; `lf` and `crlf` force one.
