# L3_bridge_cap_V2

Schematic of the Virtuoso cell `RISCA_JL/L3_bridge_cap_V2` (view schematic), exported with rnl-virtuoso and turned into a TOA circuit with toa-virtuoso.

- `L3_bridge_cap_V2.scs`: the Spectre netlist, with its drawing in RNL 0.4 records.
- `eda-symbol.rnl`, `eda-style.rnl`: the symbol and style packages the drawing uses (CC0-1.0).
- Subcircuits, each an object of its own (see `uses`): `LB_sandwitch_cap`, `LB_trangate`.
- The cells of `tcbn28hpcplusbwp12t30p140` are not included (see `external`).
