# L0_RISCA

Schematic of the Virtuoso cell `RISCA_JL/L0_RISCA` (view schematic), exported with rnl-virtuoso and turned into a TOA circuit with toa-virtuoso.

- `L0_RISCA.scs`: the Spectre netlist, with its drawing in RNL 0.4 records.
- `eda-symbol.rnl`, `eda-style.rnl`: the symbol and style packages the drawing uses (CC0-1.0).
- Subcircuits, each an object of its own (see `uses`): `L1_IO_ring`, `L1_RISCA_core_V1`, `L1_clk_buffer`, `LB_RES50`, `V1_decap`, `V1_decap_notap`.
- The models of the devices of the process `tsmc28` are not included.
- The cells of `RISCA_FIFO` are not included (see `external`).
