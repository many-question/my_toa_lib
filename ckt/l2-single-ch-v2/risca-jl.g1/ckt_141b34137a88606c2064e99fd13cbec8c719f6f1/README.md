# L2_single_ch_V2

Schematic of the Virtuoso cell `RISCA_JL/L2_single_ch_V2` (view schematic), exported with rnl-virtuoso and turned into a TOA circuit with toa-virtuoso.

- `L2_single_ch_V2.scs`: the Spectre netlist, with its drawing in RNL 0.4 records.
- `eda-symbol.rnl`, `eda-style.rnl`: the symbol and style packages the drawing uses (CC0-1.0).
- Subcircuits, each an object of its own (see `uses`): `L3_CDAC_V1`, `L3_DAC_swi_V2`, `L3_bridge_cap_V2`, `L3_clk_mux_V1`, `L3_comparator_V1`, `L3_conf_V1`, `L3_data_bus`, `L3_gm_cell_V1`, `L3_input_MUX_V1`, `L3_logic_V2`, `L3_res_rx_V2`, `LB_RDAC`, `LB_vcmbooster`, `LB_vcmbooster_LV`.
- The models of the devices of the process `tsmc28` are not included.
- The cells of `tcbn28hpcplusbwp12t30p140` are not included (see `external`).
