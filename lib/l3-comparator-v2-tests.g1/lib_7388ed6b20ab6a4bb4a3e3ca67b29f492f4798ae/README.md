# Tests of L3_comparator_V2

The test plan of the interface `l3-comparator-v2`, the clocked comparator of the Virtuoso cell `RISCA_JL/L3_comparator_V2`. Both testbenches come from the Maestro test of `RISCA_JL/_tb_L3_comparator_V1`; each runs on its own, on any circuit of the interface.

- `tb_pss_pnoise`: a periodic steady state and a periodic noise analysis at a 5 GHz clock give the input-referred noise, the energy of one comparison, the kickback on the inputs and the delay. Presets `nom` (VCM = 0.55 V) and `vcm_sweep` (VCM from 0.3 V to 0.7 V, nine points).
- `tb_tran_decision`: a transient of one clock period with transient noise, at Vin = 0, gives the decision, the output at 200 ps and the delay. Presets `nom` and `mc_lds_200`, a Monte Carlo of mismatch with 200 samples; the mean of its decisions is the probability that the output DCMPP goes high, which shows the spread of the input offset.
