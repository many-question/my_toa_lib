# Decision of a clocked comparator in one clock period, with transient noise

The testbench `tb_tran_decision` of the interface `l3-comparator-v2`, exported by toa-virtuoso 0.1.0 from the test `RISCA_JL:_tb_L3_comparator_V1:1` of the Maestro setup of the Virtuoso cell `RISCA_JL/_tb_L3_comparator_V1`.

## Files

- `tb.scs`: the testbench's own netlist: stimuli, loads, the block measured as an instance, the analyses and options. It holds no models and no circuit of the block.
- `analyze.py`: the outputs of the test, translated from the Virtuoso calculator into Python (standard library only). Called as `analyze.py <results> <output>` on the PSF ASCII results.
- `eda-symbol.rnl`: an RNL package of rnl-virtuoso that the drawing uses (CC0-1.0).
- `eda-style.rnl`: an RNL package of rnl-virtuoso that the drawing uses (CC0-1.0).

## Running it

Assemble a deck `input.scs` (the model files of the local file map, the netlists of the circuit's expanded tree, then `tb.scs` with the parameters of one point of a preset) and run

    spectre input.scs +escchars +aps -format psfascii -raw psf

then `python3 analyze.py psf out`. The block `L3_comparator_V2` is the instance `I0`; the deck must define a subcircuit of that name with the ports of the interface in order.

## Metrics

| id | unit | expression |
|---|---|---|
| `decision` | 1 | `average(int((value(VT("/DCMPP") 2e-10) + 0.45)))` |
| `vout` | V | `average(value(VT("/DCMPP") 2e-10))` (added by the configuration, not an output of the test) |
| `tdel` | s | `average(cross((VT("/DCMPP") + VT("/DCMPN")) 0.45 1 "rising"))` (added by the configuration, not an output of the test) |

Outputs of the test that are not metrics here:

- `(average(average(clip(getData("/V1/PLUS" ?result "tran") 1e-10 3e-10 ?interpolate nil))) * 2e-10)`: an output without a name (give it an id in the configuration to keep it)
- `vnoise`: needs the analysis pnoise, which the test does not run
- `energy`: needs the analysis pss, which the test does not run
- `kickback`: needs the analysis pss, which the test does not run
- `tdel`: needs the analysis pss, which the test does not run
- `int((value(VT("/DCMPP") 2e-10) + 0.45))`: an output without a name (give it an id in the configuration to keep it)
