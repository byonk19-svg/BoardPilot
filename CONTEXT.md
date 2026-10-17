# Woodworking design

## Language

**Measured thickness**: The actual thickness of a panel, which determines its
geometry and fit. A nominal label is descriptive stock metadata.

**Draft**: Edits that have not yet been accepted as a project revision.

**Saved design**: An immutable accepted revision. Its CAD may still be building.

**Verified model**: Saved CAD and its measured parts that passed geometry checks
for one revision. It may be older than the saved design while a build is pending.

**Cut list**: Grouped physical panel dimensions and quantities belonging to a
verified model. Display conversions do not change its exact measurements.

**Assembly method**: A construction recipe with explicit material and geometry
requirements. Checked dimensions alone do not establish an assembly method or
physical approval.
