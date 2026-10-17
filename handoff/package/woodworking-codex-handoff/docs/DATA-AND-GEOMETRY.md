# Data and geometry contract

## 1. Fixed cabinet template

This fixture defines an open-front cabinet with full-height sides, top and bottom between the sides, zero to four equally spaced fixed shelves, and a full-cover applied back. Every part is rectangular. It models butt interfaces without fasteners, machining, edge banding, doors, or drawers. **No hardware specification or load rating is implied.** Dimensions, material labels, stock, and kerf below are declared fixture inputs.

CAD coordinates are right-handed: X runs left to right, Y front to back, and Z bottom to top. The outside bounding box starts at the origin. **Outside depth includes the applied back.**

| Canonical ProjectSpec field | Symbol | Baseline |
|---|---|---:|
| `dimensions.outside_width_mm` | $W$ | `762` = 30 in |
| `dimensions.outside_height_mm` | $H$ | `914.4` = 36 in |
| `dimensions.outside_depth_mm` | $D$ | `304.8` = 12 in |
| `dimensions.fixed_shelf_count` | $n$ | `2` |
| `materials.main.actual_thickness_mm` | $t$ | `18` |
| `materials.back.actual_thickness_mm` | $b$ | `6` |
| `manufacturing.saw_kerf_mm` | $k$ | `3.2` |
| `manufacturing.rough_allowance_per_edge_mm` | $a$ | `0` |
| `manufacturing.sheet_edge_trim_mm` | $e$ | `10` |
| `manufacturing.stock_sheets` | — | Separate 2440 × 1220 × 18 mm and 2440 × 1220 × 6 mm stock |

Main and back nominal labels may be `3/4 in` and `1/4 in`; they are metadata. Their conversions, 19.05 and 6.35 mm, never replace the actual 18 and 6 mm inputs. The stock dimensions are also actual numeric inputs, independent of any nominal sheet label. Each stock entry references `material_id` and inherits that material's actual thickness; the stock schema has no independent thickness or quantity field. The baseline entries `main_sheet` and `back_sheet` reference `plywood_main` and `plywood_back`, respectively.

## 2. Normalization and formulas

Canonical millimeter values are normalized decimal strings with at most six fractional digits. Parse user measurements and convert units exactly. **Reject raw input whose exact converted millimeter value requires more than six fractional digits** after insignificant trailing zeros are removed; normalization does not round an input to make it acceptable. Use Fraction/Decimal arithmetic internally. **HALF_EVEN at 0.000001 mm applies only to derived positions and values**, once at the final resolved-ledger/kernel boundary. Presentation rounding must never feed back into fabrication values.

Let carcass depth be $C$, inside width $I$, and target clear opening height $g$:

$$
C=D-b,\qquad I=W-2t,\qquad
g=\frac{H-(n+2)t}{n+1}.
$$

For shelf slot $j=1,\ldots,n$:

$$
z_{\text{shelf bottom},j}=j(g+t),\qquad
z_{\text{shelf center},j}=j(g+t)+\frac{t}{2}.
$$

The bottom occupies Z $[0,t]$; the top occupies $[H-t,H]$. Opening $q=0,\ldots,n$ occupies:

$$
X=[t,W-t],\quad Y=[0,C],\quad
Z=[t+q(g+t),(q+1)(g+t)].
$$

Baseline values are **C = 298.8 mm, I = 726 mm, g = 280.8 mm**. The clear opening is measured between faces; shelf-center spacing is $g+t$.

## 3. Definitions, instances, and manufacturing dimensions

A manufactured definition describes one reusable part shape. An instance places that shape in the assembly. Semantic IDs persist across dimensional revisions; a separate content hash changes with manufacturing attributes.

| Definition ID | Finished local L × W × T, mm | Quantity | Instance IDs |
|---|---|---:|---|
| `panel_side` | 914.4 × 298.8 × 18 | 2 | `side_left`, `side_right` |
| `panel_horizontal` | 726 × 298.8 × 18 | 4 | `bottom`, `shelf_01`, `shelf_02`, `top` |
| `panel_back` | 914.4 × 762 × 6 | 1 | `back` |

Baseline: **three definitions, seven instances, six main-thickness pieces, one back**. Generally, horizontal quantity is $n+2$, main-piece count $n+4$, and total count $n+5$.

Shelf IDs are fixed template slots `shelf_01` through `shelf_04`. Count reductions remove the highest slots; increases restore them. Surviving IDs persist even when equal spacing moves their positions. Count editing does not support arbitrary middle-shelf deletion.

Each local box is centered on its origin:

$$
[-L/2,L/2]\times[-W_{\!local}/2,W_{\!local}/2]\times[-T/2,T/2].
$$

Local L is the specified face axis, **not necessarily the longest dimension**. In this baseline, materials use `face_grain: along_L` and stock uses `grain_axis: length`, so grain is locked; nesting allows 0° or 180°, not 90°. Installed grain runs vertically on sides/back and across the cabinet width on horizontal panels. The schema also permits `none`; that is a distinct grain setting, not the baseline fixture's policy.

Rough face dimensions are $L_r=L+2a$, $W_r=W_{local}+2a$; thickness stays actual stock thickness. Assembly geometry uses finished dimensions; nesting uses rough rectangles. Baseline rough equals finished. At $a=1$ mm, rough faces become 916.4 × 300.8, 728 × 300.8, and 916.4 × 764 mm. **Kerf is not added to either finished or rough part dimensions.**

Definition grouping must include material, actual thickness, dimensions, grain, allowances, and any future edge/machining attributes. Equal bounding boxes alone will not establish equivalence once drilling or joinery exists.

## 4. Proper rotations and center placement

Matrices below are written as rows and multiply column vectors:

$$
p_{world}=R p_{local}+c.
$$

$$
R_h=\begin{bmatrix}1&0&0\\0&1&0\\0&0&1\end{bmatrix},\quad
R_s=\begin{bmatrix}0&0&-1\\0&1&0\\1&0&0\end{bmatrix},\quad
R_b=\begin{bmatrix}0&1&0\\0&0&1\\1&0&0\end{bmatrix}.
$$

Each satisfies $R^TR=I_3$ and $\det R=+1$. Side local axes map to $(+Z,+Y,-X)$; back axes map to $(+Z,+X,+Y)$. Replacing the side thickness direction with +X while keeping the other axes produces a reflection. Both side instances deliberately use the same proper rotation; local +T is not labeled an outward face.

| Instance | Rotation | General center | Baseline center, mm |
|---|---|---|---|
| `side_left` | $R_s$ | $(t/2,C/2,H/2)$ | (9, 149.4, 457.2) |
| `side_right` | $R_s$ | $(W-t/2,C/2,H/2)$ | (753, 149.4, 457.2) |
| `bottom` | $R_h$ | $(W/2,C/2,t/2)$ | (381, 149.4, 9) |
| `shelf_01` | $R_h$ | $(W/2,C/2,g+3t/2)$ | (381, 149.4, 307.8) |
| `shelf_02` | $R_h$ | $(W/2,C/2,2g+5t/2)$ | (381, 149.4, 606.6) |
| `top` | $R_h$ | $(W/2,C/2,H-t/2)$ | (381, 149.4, 905.4) |
| `back` | $R_b$ | $(W/2,D-b/2,H/2)$ | (381, 301.8, 457.2) |

Sides occupy X [0,18] and [744,762]; horizontal panels occupy X [18,744]. Main parts occupy Y [0,298.8]; the back occupies Y [298.8,304.8]. Overall AABB is exactly **(0,0,0) to (762,304.8,914.4) mm**. Butt faces may touch; interiors do not overlap.

### Per-definition GLB conversion

Export each unique definition at its local origin; use the instance manifest for assembly. For CAD millimeters to glTF meters:

$$
A=\begin{bmatrix}1&0&0\\0&0&1\\0&-1&0\end{bmatrix},\qquad
p_g=0.001A p_{cad}.
$$

If this conversion is baked into each local GLB, manifest transforms must be:

$$
R_g=A R A^{-1},\qquad c_g=0.001A c.
$$

In particular:

$$
R_{s,g}=\begin{bmatrix}0&-1&0\\1&0&0\\0&0&1\end{bmatrix},\qquad
R_{b,g}=\begin{bmatrix}0&0&-1\\1&0&0\\0&-1&0\end{bmatrix}.
$$

Do not apply another scene-level conversion. Expected glTF centers include `side_left` (0.009, 0.4572, −0.1494), `shelf_01` (0.381, 0.3078, −0.1494), and `back` (0.381, 0.4572, −0.3018) meters. Convert units after resolving millimeters; rounding meters prematurely loses precision.

## 5. Baseline invariants and mutations

All three baseline openings have clear size **726 × 298.8 × 280.8 mm**, with Z intervals [18,298.8], [316.8,597.6], and [615.6,896.4].

| Quantity | Exact baseline result |
|---|---:|
| Main face area: $2HC+(n+2)IC$ | 1,414,160.64 mm² |
| Back face area: $WH$ | 696,772.8 mm² |
| Main volume | 25,454,891.52 mm³ |
| Back volume | 4,180,636.8 mm³ |
| Total part/assembled-union volume | 29,635,528.32 mm³ |

Each mutation below starts independently from baseline.

| Mutation | Horizontal finished L × W × T, mm | Opening target g, mm | Total volume, mm³ |
|---|---|---:|---:|
| Width = 36 in = 914.4 mm | 878.4 × 298.8 × 18 | 280.8 | 33,750,328.32 |
| Actual main thickness = 19 mm | 724 × 298.8 × 19 | $4192/15$ | 31,004,271.36 |
| Outside depth = 14 in = 355.6 mm | 726 × 349.6 × 18 | 280.8 | 33,963,200.64 |
| Shelf count = 0 | 726 × 298.8 × 18, quantity 2 | 878.4 | 21,826,091.52 |
| Actual back thickness = 9 mm | 726 × 295.8 × 18 | 280.8 | 31,470,275.52 |

**Width:** sides remain unchanged; back becomes 914.4 × 914.4 × 6 mm. Right-side X center becomes 905.4; all horizontal/back X centers become 457.2 mm. Y/Z values stay unchanged.

**Main thickness:** sides become 914.4 × 298.8 × 19 mm; back remains unchanged. Side X centers are 9.5 and 752.5. Bottom/top Z centers are 9.5 and 904.9. Exact shelf Z centers are $9239/30$ and $18193/30$ mm, resolving to **307.966667 and 606.433333**. Target g resolves to 279.466667, while gaps re-measured from resolved boxes are 279.466667 / 279.466666 / 279.466667 mm. Assert equality before quantization and use **0.000002 mm** absolute tolerance for resolved placement/contact checks. Never compute later shelf positions from an already rounded g.

**Depth:** sides become 914.4 × 349.6 × 18 mm; main Y centers become 174.8; back Y center becomes 352.6 mm. Back face size and all X/Z values stay unchanged.

**Back thickness:** main Y centers become 147.9; back becomes 914.4 × 762 × 9 mm centered at Y = 300.3. Outside depth stays 304.8 mm.

Shelf-count fixtures, with all other baseline parameters unchanged:

| n | Horizontal quantity / total instances | g, mm | Shelf center Z values, mm |
|---:|---|---:|---|
| 0 | 2 / 5 | 878.4 | None |
| 1 | 3 / 6 | 430.2 | 457.2 |
| 2 | 4 / 7 | 280.8 | 307.8, 606.6 |
| 3 | 5 / 8 | 206.1 | 233.1, 457.2, 681.3 |
| 4 | 6 / 9 | 161.28 | 188.28, 367.56, 546.84, 726.12 |

Zero shelves leaves one opening X [18,744], Y [0,298.8], Z [18,896.4]. There are no zero-size placeholder shelves. Counts 1, 3, and 4 have respective total volumes 25,730,809.92, 33,540,246.72, and 37,444,965.12 mm³.

## 6. Stock layout and executable geometric cut sequence

This is a deterministic valid candidate, without an optimal-yield claim. Sheet coordinates are Sx/Sy, with grain along Sx. Ten-millimeter trims leave **[10,2430] × [10,1210]**, a 2420 × 1200 mm rectangle. Treat main/back stock as separate material pools.

Sort rough rectangles by decreasing L, decreasing W, then lexicographic instance ID. The baseline main-sheet placements are:

| Instance | Sx, mm | Sy, mm | Rough L × W, mm |
|---|---:|---:|---|
| `side_left` | 10 | 10 | 914.4 × 298.8 |
| `side_right` | 927.6 | 10 | 914.4 × 298.8 |
| `bottom` | 10 | 312 | 726 × 298.8 |
| `shelf_01` | 739.2 | 312 | 726 × 298.8 |
| `shelf_02` | 1468.4 | 312 | 726 × 298.8 |
| `top` | 10 | 614 | 726 × 298.8 |

All rotations are 0°. Row part envelopes are 1832, 2184.4, and 726 mm long. Their combined height including two intervening kerfs is 902.8 mm. **These envelopes omit cuts needed to release the last row and the last part in each row.** Reserve the trailing bands below as well.

First trim the original sheet. For this fixture, removed trim-cut bands are X [6.8,10] and [2430,2433.2], then Y [6.8,10] and [1210,1213.2] on the remaining piece. These lie within the declared discard margins and preserve the exact usable rectangle.

Then isolate rows in order using full-width cuts through the current remainder; crosscut each isolated row using the listed bands in ascending X order:

| Step/piece | Removed kerf band(s), mm | Resulting offcut |
|---|---|---|
| Isolate row 1 | Y [308.8,312] | Pass upper remainder to next step |
| Isolate row 2 | Y [610.8,614] | Pass upper remainder to next step |
| Isolate row 3 | Y [912.8,916] | X [10,2430], Y [916,1210] |
| Crosscut row 1 | X [924.4,927.6], [1842,1845.2] | X [1845.2,2430], Y [10,308.8] |
| Crosscut row 2 | X [736,739.2], [1465.2,1468.4], [2194.4,2197.6] | X [2197.6,2430], Y [312,610.8] |
| Crosscut row 3 | X [736,739.2] | X [739.2,2430], Y [614,912.8] |

There are three row-isolation kerfs and six crosscut kerfs after trimming. The final row-release cut ends at Y = 916; the longest row-release crosscut ends at X = 2197.6, both within usable stock.

On the separately trimmed back sheet, place `back` at (10,10), face 914.4 × 762 mm. Isolate a strip with Y kerf [772,775.2], then crosscut with X kerf [924.4,927.6]. Offcuts are [10,2430] × [775.2,1210] and [927.6,2430] × [10,772].

These cut bands partition the usable sheets exactly:

| Stock | Part area | Internal kerf area | Remaining offcut area | Sum, mm² |
|---|---:|---:|---:|---:|
| Main | 1,414,160.64 | 28,968.96 | 1,460,870.4 | 2,904,000 |
| Back | 696,772.8 | 10,182.4 | 2,197,044.8 | 2,904,000 |

Each original sheet adds 72,800 mm² of reserved edge bands, giving 2,976,800 mm² total. Edge bands include trimming kerf and discard; internal kerf above excludes them. These are geometric cut allocations, not machine-specific operating instructions.

### Synthetic exact-fit kerf test

For a 306.4 × 100 mm sheet with no trim, three 100 × 100 mm rough pieces and k = 3.2 fit at X = 0, 103.2, 206.4. Kerfs are [100,103.2] and [203.2,206.4]. The last part reaches the stock boundary:

$$
3(100)+2(3.2)=306.4.
$$

There is no trailing separation cut at an already finished stock edge. A 306.3 mm sheet fails. A 300 mm sheet also fails despite equal kerf-free area. With 5 mm trims on all edges, 316.4 × 110 mm restores the same usable region; X starts become 5, 108.2, 211.4. Adding 1 mm allowance to each L edge makes the required width $3(102)+2(3.2)=312.4$ mm.

Whenever the last part ends inside stock and an offcut remains, a release cut must be modeled outside that part. Do not infer a valid cut sequence from nonoverlapping placement rectangles alone. Any partially overhanging blade/edge-cut behavior requires explicit support; this fixture uses full kerf bands contained in the source piece.

## 7. Parser, validity, and revision regressions

Use exact conversion 1 in = 25.4 mm. Supported fractional denominators are 1, 2, 4, 8, 16, 32, 64. Examples:

| Input | Normalized millimeters |
|---|---:|
| `30 1/2 in` | `774.7` |
| `3/4 in` or `0.75 in` | `19.05` |
| `1 1/8 in` | `28.575` |
| `23 7/16 in` | `595.3125` |
| `1/64 in` | `0.396875` |

Reject malformed numbers, zero denominators, unsupported denominators, nonfinite values, excess precision, and ambiguous unitless input without a declared default. In particular, raw `1.2345678 mm`, `18.0000005 mm`, and `18.0000015 mm` are rejected. Nominal-only edits leave geometry unchanged. An explicit actual-thickness change to 19.05 mm produces horizontal length 723.9 and g = 279.4 mm.

The following are **internal derived-value rounding tests**, not accepted user measurements:

| Exact internally derived value, mm | Resolved value, mm | Rule |
|---|---:|---|
| 18.0000005 | 18 | HALF_EVEN tie to the even last digit |
| 18.0000015 | 18.000002 | HALF_EVEN tie to the even last digit |

Validate $t>0$, $b>0$, $W>2t$, $D>b$, $H>(n+2)t$, and integer $0\le n\le4$. Kerf, trim, and rough allowance must be nonnegative; usable stock must have positive dimensions. Reject features that collapse at resolved precision: n = 2, t = 18, H = 72.000001 mm gives a positive exact gap that rounds to zero.

Also apply the product support bounds in `API-AND-JOBS.md`; mathematical boundary fixtures can deliberately fall outside those bounds to exercise domain errors. Test W = 36 mm, D = 6 mm, and H = 72 mm with baseline thickness/count; each produces a zero required dimension. Shelf count −1, 1.5, or 5 fails. A stock entry must reference a declared material and inherit its thickness, without silently substituting another material. A valid cabinet whose grain-locked sides exceed usable stock remains valid geometry but reports an unplaceable part. For example, 900 × 1220 mm stock with 10 mm trims offers only 880 mm along grain, below the 914.4 mm side length.

Every artifact carries its immutable source revision and resolved-ledger hash. Start export A at baseline revision r1; change width to 36 inches at r2; let export B finish before A. Late A must not replace r2 downloads or preview. Reject a bundle combining r1's 726 mm horizontal cut list with r2's 878.4 mm assembly. Also test old failures arriving late, kerf-only changes, and restoring old dimensions under a new revision.

All outputs consume one resolved ledger. Keep definition geometry, instance identity, and transforms explicit; do not reconstruct cut sizes from world mesh bounds or merged assembly meshes. Regression coverage must check quantities, proper rotations/grain, all requested mutations, exact unit parsing, cut-band partitions, stock-material separation, invalid states, and revision coherence.
