# L1_RISCA_core_V1

Schematic of the Virtuoso cell `RISCA_JL/L1_RISCA_core_V1` (view schematic), exported with rnl-virtuoso and turned into a TOA circuit with toa-virtuoso.

- `L1_RISCA_core_V1.scs`: the Spectre netlist, with its drawing in RNL 0.4 records.
- `eda-symbol.rnl`, `eda-style.rnl`: the symbol and style packages the drawing uses (CC0-1.0).
- Subcircuits, each an object of its own (see `uses`): `L2_Ib_mirror`, `L2_frame_gen_V1`, `L2_single_ch_V2`.
- The models of the devices of the process `tsmc28` are not included.
- The cells of `tcbn28hpcplusbwp12t30p140` are not included (see `external`).
