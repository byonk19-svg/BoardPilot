# Authored construction method review

The installed recipe `kreg720_19_05_14in_bookcase`, version `1.0.0`, defines a narrowly supported indoor plywood fabrication method. Its technical graph can be complete while its physical build review remains unperformed. It does not certify a shelf load, overall stability, tool access under real workholding, or site installation.

## Exact applicability

The supported case has outside width 762 mm, height 914.4 mm and depth 355.6 mm, measured main panels 19.05 mm and measured back 6.35 mm. Zero to four fixed shelves use the same deterministic template and connection rules. These are actual dimensions, rather than nominal labels converted without measurement.

The original 18 mm / 6 mm reference remains valid design geometry and receives its normal design packet. Selecting this known recipe for that reference reports incompatible measured stock. The Kreg 720 manual specifies gauge ranges but does not provide a numeric interval proving that every 18 mm panel falls in its 3/4 range. No stock is silently changed to satisfy the recipe.

## Primary evidence

- [KPHJ720/720PRO Global manual](https://www.kregtool.com/on/demandware.static/-/Library-Sites-RefArchSharedLibrary/default/dw59d64a56/manuals/KPHJ720PRO_Global.pdf), 06/2020 104909 V1, English printed pages 12-17: use the actual-stock gauge, select the matching stop collar, clamp the workpiece, and select 1-1/4 in screws for the gauged 3/4 range. Printed page 13 describes 5/8 to 1-1/2 in edge offsets and 6 to 8 in spacing for wide panels. The local downloaded PDF and rendered chart were read; the web reader refused the oversized file.
- [Kreg screw guide](https://learn.kregtool.com/learn/how-to-select-right-pocket-hole-screw/), updated June 29, 2026: actual thickness governs selection; coarse thread is preferred for plywood. This supports indoor zinc coarse-thread hardware identification, rather than a furniture capacity claim.
- [Kreg zinc pocket screws](https://www.kregtool.com/en/products/pocket-hole-joinery/pocket-hole-screws-plugs/zinc-pocket-hole-screws/SMLZINCSCREWS.html): the SML-C125-100 option is a #8 coarse-thread zinc Maxi-Loc 1-1/4 in screw in a 100-count package. The exact imperial conversion is 31.75 mm; the manufacturer's 32 mm label is a rounded equivalent.
- [Kreg / The Creative Mom Built In Bookcase](https://learn.kregtool.com/plans/built-in-bookcase/): a published method uses pocket screws and glue, then attaches a separate thin plywood back with glue and brads. Its supplied list includes 1-1/4 in screws and brads. Its original dimensions and its 100-count supplies are not reused as this project's dimensions or required fastener counts.
- [DEWALT DWBN18PP project pack](https://www.dewalt.com/en-us/product/dwbn18pp/18-gauge-brad-nail-project-pack): indoor steel 18-gauge brads include a 1-1/4 in length. Only that length is specified here. The source does not publish the count of that length in the mixed pack, so brad purchase quantity and price remain unknown.

Some manufacturer pages reject a direct fetch with HTTP 403; their primary-domain indexed content was available. The stale 320 manual link returned HTTP 404 and was not treated as a verified numeric thickness rule.

## Local reference and quantity rules

All horizontal panels use their marked local +T face. The pocket jig references each local L end edge; no hole diameter, drill angle, bore depth or pocket outline is invented from the mesh. The station records identify where to align the manufacturer's guide. Nominal version-1 CAD remains unmachined panels; the operation diagrams are explicitly labeled reference illustrations.

The supported carcass depth is derived from outside depth minus back thickness. Three guide stations per end are centered about local W=0 with 152.4 mm spacing. Their front-edge distances derive to 22.225, 174.625 and 327.025 mm. Their 22.225 mm end offsets and 152.4 mm pitch satisfy the cited manual's wide-panel guidance. Each horizontal-to-side connection uses three screws, so the required quantity is `3 * 2 * (fixed_shelf_count + 2)`. With two shelves this is 24 screws, separately represented as one 100-count pack purchased when that package is chosen.

The back is a separate attachment method. Its brad centerlines come from each contacted carcass edge in the same resolved ledger. Authored layout choices use 25.4 mm end offsets and at most 180 mm spacing, with brads centered on the measured edge thickness. These choices received a geometric and source-consistency software review; they are not manufacturer-approved fastener spacing or a structural determination. The two-shelf supported case derives 32 required brads. Their unknown mixed-package purchase quantity stays null.

## Technical checks and sequencing

The graph checks every required connection exactly once; named parts, stable joints, hardware type and dimensions, positive integer fastener counts, operation dependencies, missing tools and finishing-to-size requirements. A missing connection, duplicate attachment, unknown part, cycle, undefined hardware or missing required tool produces an actionable incomplete result. A nonzero rough allowance requires an explicit finishing operation.

Loose panels are cut, labeled, finished to size and drilled before assembly. A dry fit precedes the first side attachment. The second side follows the first, and the applied back follows the squared carcass. The final check names dimensions, squareness, seated fasteners, breakout and adhesive cure. The generated packet includes local station diagrams, joint-derived hardware and these dependency-ordered instructions.

Catalog data, generator version and the generator file hash contribute to the recipe fingerprint. Synthetic graph fixtures are test-only and absent from the production catalog. A source or rule change requires a reviewed recipe version and regeneration; modifying a status flag cannot create a physical review.

## Remaining physical and installation evidence

No furniture was built during this software implementation. Physical review must record the exact project and recipe fingerprints, actual stock, jig gauge confirmation, screw seating and breakout, thin-back behavior, clamping, driver access, squareness, observed issues and any changes made. Service-load conclusions require their own identified scope.

The published bookcase source calls for tip-over restraint. Before service, the actual wall substrate and intended use require a site-specific restraint selection and installation review. The recipe does not invent wall anchors or installation instructions for an unknown substrate. Its completeness describes carcass fabrication; physical review and site installation remain separate open gates.
