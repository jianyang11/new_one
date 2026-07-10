# PU LOCO v3 Morphology-Condition Map

## Boundary

This zero-API diagnostic uses only `config.SPLIT['train']` bearing IDs within each PU operating condition. LOCO held-out test windows and test bearing IDs are not read.

## Mechanism From v1/v2

- v1 failed on kinematics: recipes rendered at source training rpm produced BPFO/BPFI errors of about -40% or +66.7% when evaluated at a different held-out rpm.
- v2 corrected `fr_hz`, impact rate, and current fault frequency, but still failed downstream. The remaining mismatch is morphology: resonance-band energy, impulse shape, modulation, and background spectrum depend on torque/load/transfer path and are not a linear rpm rescale.
- `noise_aug` remains strong because it perturbs real windows from the training operating conditions, preserving realistic morphology diversity.

## Operating Conditions

| condition | rpm | torque Nm | radial load N |
|---|---:|---:|---:|
| N09_M07_F10 | 900 | 0.7 | 1000 |
| N15_M01_F10 | 1500 | 0.1 | 1000 |
| N15_M07_F04 | 1500 | 0.7 | 400 |
| N15_M07_F10 | 1500 | 0.7 | 1000 |

## Focus Feature Predictability

Predictability uses leave-one-condition-out inverse-distance interpolation in `(rpm, torque, radial load)` space. With only four operating conditions, this is a development diagnostic, not a final statistical model.

| class | feature | rel LOO MAE | rho rpm | rho torque | rho load | verdict | values by condition |
|---|---|---:|---:|---:|---:|---|---|
| IR | band_2_500_1000_frac_median | 0.917 | -0.775 | -0.258 | 0.775 | not_predictable | `{"N09_M07_F10":0.21473788334524205,"N15_M01_F10":0.07935834440292136,"N15_M07_F04":0.055693431871644036,"N15_M07_F10":0.06923563843692329}` |
| IR | band_7_3000_4000_frac_median | 0.200 | 0.775 | -0.775 | 0.258 | weak | `{"N09_M07_F10":0.4280989502090518,"N15_M01_F10":0.6564287228012635,"N15_M07_F04":0.4910224604144111,"N15_M07_F10":0.6506813551644993}` |
| IR | env_peak_prominence_median | 0.131 | 0.258 | -0.258 | 0.775 | interpolatable | `{"N09_M07_F10":2.738434730014286,"N15_M01_F10":3.285407425532701,"N15_M07_F04":2.526301820597755,"N15_M07_F10":3.3323566735492625}` |
| IR | ir_resonance_3000_3600_frac_median | 0.169 | 0.775 | -0.775 | 0.258 | interpolatable | `{"N09_M07_F10":0.3525548380454514,"N15_M01_F10":0.5296355139753934,"N15_M07_F04":0.42696291262046304,"N15_M07_F10":0.522000428833123}` |
| IR | mod_depth_fr_median | 0.168 | 0.775 | -0.258 | 0.258 | interpolatable | `{"N09_M07_F10":3.0337225752464274,"N15_M01_F10":4.5661545966356645,"N15_M07_F04":3.760393167730248,"N15_M07_F10":4.616747687093433}` |
| IR | or_resonance_600_1200_frac_median | 0.787 | -0.775 | -0.258 | 0.775 | not_predictable | `{"N09_M07_F10":0.19184166514118134,"N15_M01_F10":0.08000277323530061,"N15_M07_F04":0.04913415851124823,"N15_M07_F10":0.06946845609013404}` |
| IR | vib_crest_median | 0.069 | -0.775 | -0.258 | 0.775 | interpolatable | `{"N09_M07_F10":5.249262951659379,"N15_M01_F10":4.841167326879531,"N15_M07_F04":4.335598865852539,"N15_M07_F10":4.771078955800608}` |
| IR | vib_kurtosis_median | 0.129 | -0.775 | -0.258 | 0.775 | interpolatable | `{"N09_M07_F10":5.091019907388562,"N15_M01_F10":4.3115219606019135,"N15_M07_F04":3.6500785119909986,"N15_M07_F10":4.163217435114921}` |
| IR | vib_rms_median | 0.277 | 0.775 | -0.775 | 0.258 | weak | `{"N09_M07_F10":0.08915694671021274,"N15_M01_F10":0.2294601957688712,"N15_M07_F04":0.19939854912889365,"N15_M07_F10":0.20883300842542746}` |
| OR | band_2_500_1000_frac_median | 0.175 | -0.775 | -0.258 | 0.775 | interpolatable | `{"N09_M07_F10":0.5300593843318337,"N15_M01_F10":0.48823494349163954,"N15_M07_F04":0.3463829573840794,"N15_M07_F10":0.43161514961143244}` |
| OR | band_7_3000_4000_frac_median | 0.282 | 0.775 | 0.258 | -0.258 | weak | `{"N09_M07_F10":0.1352302632275726,"N15_M01_F10":0.31132866143265714,"N15_M07_F04":0.32757991700125405,"N15_M07_F10":0.35912929368080976}` |
| OR | env_peak_prominence_median | 0.446 | 0.258 | -0.775 | 0.775 | weak | `{"N09_M07_F10":22.29248579065074,"N15_M01_F10":49.37575555208113,"N15_M07_F04":21.1783768277966,"N15_M07_F10":40.345603176193464}` |
| OR | ir_resonance_3000_3600_frac_median | 0.284 | 0.775 | 0.258 | -0.258 | weak | `{"N09_M07_F10":0.1153319786957337,"N15_M01_F10":0.2776860309357272,"N15_M07_F04":0.2800287371187094,"N15_M07_F10":0.32061782917539505}` |
| OR | mod_depth_fr_median | 0.223 | 0.775 | -0.775 | 0.258 | weak | `{"N09_M07_F10":4.091825150326375,"N15_M01_F10":7.822978097157645,"N15_M07_F04":5.8429170179027015,"N15_M07_F10":6.719423213159143}` |
| OR | or_resonance_600_1200_frac_median | 0.158 | 0.258 | -0.775 | 0.775 | interpolatable | `{"N09_M07_F10":0.4058302857669105,"N15_M01_F10":0.43124347917205874,"N15_M07_F04":0.27584305487121485,"N15_M07_F10":0.4252042070800438}` |
| OR | vib_crest_median | 0.112 | -0.775 | 0.775 | 0.258 | interpolatable | `{"N09_M07_F10":5.057900778241937,"N15_M01_F10":4.00420602408632,"N15_M07_F04":4.045487305347507,"N15_M07_F10":4.175741609681291}` |
| OR | vib_kurtosis_median | 0.277 | -0.775 | 0.258 | 0.775 | weak | `{"N09_M07_F10":6.728053219908114,"N15_M01_F10":4.181418071407806,"N15_M07_F04":4.158897578049027,"N15_M07_F10":4.271443951013442}` |
| OR | vib_rms_median | 0.267 | 0.775 | -0.775 | 0.258 | weak | `{"N09_M07_F10":0.174031741255756,"N15_M01_F10":0.388494822450491,"N15_M07_F04":0.28404772524268007,"N15_M07_F10":0.3545291911080156}` |
| healthy | band_2_500_1000_frac_median | 0.279 | -0.775 | 0.775 | -0.258 | weak | `{"N09_M07_F10":0.11922485614174977,"N15_M01_F10":0.07130413856768425,"N15_M07_F04":0.07691038357780383,"N15_M07_F10":0.07240838395366106}` |
| healthy | band_7_3000_4000_frac_median | 0.095 | 0.775 | -0.775 | 0.258 | interpolatable | `{"N09_M07_F10":0.2408679793439945,"N15_M01_F10":0.3119373231924226,"N15_M07_F04":0.2944373192536399,"N15_M07_F10":0.30022096666474973}` |
| healthy | ir_resonance_3000_3600_frac_median | 0.132 | 0.775 | -0.775 | 0.258 | interpolatable | `{"N09_M07_F10":0.17974592527715558,"N15_M01_F10":0.2646186599459882,"N15_M07_F04":0.2374620104458639,"N15_M07_F10":0.24917861827372662}` |
| healthy | or_resonance_600_1200_frac_median | 0.206 | -0.775 | 0.775 | -0.258 | weak | `{"N09_M07_F10":0.14773614513906158,"N15_M01_F10":0.10091436164949741,"N15_M07_F04":0.10288922129846474,"N15_M07_F10":0.10163578092514255}` |
| healthy | vib_crest_median | 0.155 | -0.775 | 0.258 | -0.258 | interpolatable | `{"N09_M07_F10":7.026029276737525,"N15_M01_F10":5.192072583630757,"N15_M07_F04":5.333966036628739,"N15_M07_F10":5.1867325405268705}` |
| healthy | vib_kurtosis_median | 0.411 | -0.775 | 0.258 | -0.258 | weak | `{"N09_M07_F10":9.266843196368772,"N15_M01_F10":4.900869930217148,"N15_M07_F04":4.916194346713557,"N15_M07_F10":4.809971079400367}` |
| healthy | vib_rms_median | 0.098 | 0.775 | -0.775 | 0.258 | interpolatable | `{"N09_M07_F10":0.11881432832803507,"N15_M01_F10":0.1522070587898346,"N15_M07_F04":0.14956368253152033,"N15_M07_F10":0.15171043244643018}` |

## v3 Implication

Features marked `interpolatable` are candidates for morphology interpolation/extrapolation in v3 recipes. Features marked `weak` or `not_predictable` should not be blindly extrapolated; v3 should either borrow nearest-condition morphology for them or require an explicit LLM reasoning step using the train-condition table.

## Artifacts

- `morphology_condition_features.csv`
- `morphology_condition_trends.csv`
