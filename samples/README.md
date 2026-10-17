# Working sample exports

Both folders contain complete loose artifact sets and a portable `project.zip` with every inventoried payload plus the manifest. ZIPs exclude their own checksum from the manifest; the outer hashes are recorded in `export-evidence.json`.

| Sample | Actual input / output | Construction state |
|---|---|---|
| `reference-bookcase` | Supplied 30 × 12 × 36 in baseline; measured 18 mm main / 6 mm back; two fixed shelves; Letter design packet, native metric sheets and verified stock plan | Method unselected; design packet |
| `authored-bookcase` | Separate 30 × 14 × 36 in case; measured 19.05 mm main / 6.35 mm back; two fixed shelves; A4 packet, native metric sheets and verified stock plan | Authored Kreg 720/720PRO method technically checked; physical fabrication and installation unreviewed |

To edit, launch the app, choose **Import project ZIP**, select a sample's `project.zip`, review validation, and import as a new project. Generate using the installed template before the imported project's local model becomes verified. Source provenance is retained; local IDs are fresh.

The CAD files represent nominal finished panels. Planned jig/fastener references are explicit separate instructions, not modeled holes. Sheet prices are unknown in these supplied samples; a known subtotal of zero does not make the project free or complete. The USD 70/25/95 browser test uses separate synthetic price inputs.

`bookcase-baseline` contains older M1 CLI evidence and is not the final working export; use the two folders above.
