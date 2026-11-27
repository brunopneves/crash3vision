# CRASH3Vision Experimental Validation

## 1. Overview

CRASH3Vision was evaluated in two complementary experimental phases designed to investigate different aspects of the image-based deformation-measurement workflow.

- **Phase 1** compared image-based measurements with controlled NHTSA crash-test references.
- **Phase 2** compared image-based measurements with conventional manual field measurements on real damaged vehicles documented by UAV.

The study should be interpreted as a **preliminary proof-of-concept**, not as definitive validation across all vehicles, crash configurations or operational conditions.

---

## 2. Phase 1 — Controlled NHTSA evaluation

### Purpose

The purpose of Phase 1 was to estimate the error associated with obtaining CRASH3 deformation measurements from images rather than through conventional direct measurement.

The resulting EES estimates were compared with reference EES values reported in the corresponding NHTSA crash-test documentation.

### Sample selection

The sample was constrained by the availability of NHTSA tests that provided an overhead or near-nadir camera view suitable for image-based deformation measurement.

Five compatible frontal crash tests were identified.

The small number of suitable tests was partially compensated by repeated independent measurements.

### Measurement design

For each vehicle:

- 3 forensic examiners;
- 3 independent markings per examiner;
- 9 measurements per vehicle.

Total:

- **5 vehicles**
- **45 measurements**

### Main result

The global Mean Absolute Percentage Error (MAPE) for EES was:

**3.52%**

The mean standard deviation of the absolute error across the evaluated vehicles was approximately:

**0.94 km/h**

Three of the five vehicles presented errors at or below approximately 2%.

The largest errors were associated with images of lower resolution or reduced contrast.

---

## 3. Image quality analysis

Phase 1 also explored the relationship between image resolution and measurement error.

The observed Pearson correlation was:

**r = -0.908**

The linear regression produced:

**R² = 0.824**

These values indicate a strong negative association in the evaluated sample: higher image resolution tended to be associated with lower MAPE.

Because the analysis included only five vehicle models, this result should be interpreted as a preliminary trend rather than as a universal performance threshold.

Other relevant image factors identified during the study included:

- contrast between vehicle and background;
- shadows;
- viewing angle;
- structural obstruction;
- visibility of the deformation region.

---

## 4. Phase 2 — Real-world UAV evaluation

### Purpose

Phase 2 evaluated the workflow under real operational conditions.

Image-based measurements obtained from UAV photographs were compared with conventional manual measurements performed in the field.

### Sample

The field sample consisted of three suitable real damaged vehicles available during the study period.

This limited sample is one of the reasons the study is characterized as a proof-of-concept.

### Measurement design

For each vehicle:

- 3 forensic examiners;
- 3 independent markings per examiner;
- 9 measurements per vehicle.

Total:

- **3 vehicles**
- **27 measurements**

### Main result

The global MAPE for EES was:

**4.60%**

The mean standard deviation of the absolute error was:

**0.505 km/h**

The evaluated vehicles presented MAPE values of approximately:

- Agile: **3.61%**
- Etios: **5.09%**
- Classic: **5.10%**

In absolute terms, the image-based EES estimates remained close to the manual field references within the low-energy range evaluated.

These values should not be interpreted as evidence of zero or negligible uncertainty. The Phase 2 vehicles were associated with relatively low deformation-energy levels, which reduces the magnitude of deviations when expressed in km/h.

---

## 5. Statistical comparison

Paired t-tests were applied to the mean values by vehicle.

Results:

- **Phase 1:** p = 0.116
- **Phase 2:** p = 0.774

At α = 0.05, the study did not reject the null hypothesis of no statistically significant difference between the image-based estimates and their respective references.

These results must be interpreted together with the small number of vehicle-level samples and should not be treated as proof of equivalence.

---

## 6. Inter-examiner repeatability

Three forensic examiners independently performed the image-based measurements after brief operational training and alignment of general interpretation criteria.

Across the repeated measurements, the results showed relatively low dispersion under the evaluated conditions. This qualitative observation is consistent with operational repeatability, but the standard-deviation values reported above describe the dispersion of the absolute error and should not be interpreted as standalone inter-rater reliability coefficients.

Manual landmark placement remains subjective, and inter-examiner variability should be expected, particularly when:

- image resolution is limited;
- contrast is poor;
- the structural reference is partially hidden;
- the deformation contour is ambiguous.

---

## 7. Operational time

In Phase 2, the image-based workflow reduced the average time required to obtain deformation parameters from:

**19.3 minutes to 11.1 minutes per vehicle**

This corresponds to an observed average reduction of approximately:

**40.9%**

The field comparison included the operational time associated with the UAV-based image acquisition workflow used in the study.

This result applies only to the tested conditions and should not be generalized to every crash scene or documentation workflow.

---

## 8. Consolidated results

| Metric | Phase 1 — NHTSA | Phase 2 — UAV / field |
|---|---:|---:|
| Vehicles | 5 | 3 |
| Measurements | 45 | 27 |
| Examiners | 3 | 3 |
| Measurements per examiner/vehicle | 3 | 3 |
| Global MAPE | **3.52%** | **4.60%** |
| Mean standard deviation of absolute error | **0.94 km/h** | **0.505 km/h** |
| Paired t-test | p = 0.116 | p = 0.774 |
| Reference | NHTSA EES | Manual field measurement |

Overall:

- **8 vehicles**
- **72 independent markings**

The two phases address different questions and should not be interpreted as a single homogeneous validation dataset.

---

## 9. Interpretation

The experimental results support the feasibility of using calibrated digital images to obtain deformation parameters for CRASH3-derived EES estimation under the tested conditions.

The findings suggest that:

- image-based measurements can approximate controlled and field reference values;
- repeated measurements remained relatively stable across the evaluated operators and conditions;
- image quality materially affects measurement performance;
- digital-image workflows can improve traceability and reduce measurement time.

The evidence remains preliminary because of the small vehicle sample and limited impact configurations.

---

## 10. Limitations

The current validation is limited by:

- only 5 compatible NHTSA tests in Phase 1;
- only 3 suitable real-world vehicles in Phase 2;
- frontal impacts only;
- dependence on image quality;
- operator interpretation;
- limited evaluation of perspective distortion;
- dependence on appropriate structural stiffness coefficients;
- low-energy field cases in Phase 2.

The study therefore supports the methodology as a **proof-of-concept**, not as a universally validated replacement for conventional crash-reconstruction measurements.

---

## 11. Future validation

Future work should include:

- larger and more diverse vehicle samples;
- additional impact directions;
- broader deformation-energy ranges;
- formal uncertainty propagation;
- expanded inter-examiner reliability analysis;
- perspective and distortion correction;
- comparison with photogrammetry, LiDAR and 3D scanning;
- automated or AI-assisted landmark detection;
- validation using independently sourced technical references.

---

## 12. Associated research

**B. P. Neves, J. G. Silva Neto, R. de O. Mapele**  
*Metodologia semiassistida por imagem para mensuração de deformações veiculares e estimativa da EES pelo método CRASH3.*  
XXVIII Congresso Nacional de Criminalística — CNC 2026, Brazil.

## 13. Stored project consistency

Opening and saving a project apply the same checks to the scientific fields. The checks use the existing CRASH3 and EES functions. When their inputs are available, the stored energy and speed must be compatible with those inputs and with each other. Accepted results retain their stored values.

The project format has no precision metadata. For each field, the validator uses half of the rounding increment suggested by the shortest decimal representation of its value, subject to these maximum increments.

| Field | Maximum rounding increment |
| --- | ---: |
| EES in m/s | 0.1 m/s |
| EES in km/h | 0.1 km/h |
| Energy | 1 J |
| Mass | 1 kg |
| Width, W/5 intervals and crush in pixels | 1 px |
| Width, W/5 intervals and crush in meters | 0.01 m |
| Calibration scale | 0.00001 m/px |
| A and B | 0.01 in the respective SI units |
| Angle | 0.01° |

Legacy centimeter fields are converted to SI before checking their intervals. A W value derived from pixel width and scale inherits both input intervals. An interval derived directly as W/5 contributes no additional precision. The six stored positions, when available, must admit five equal spacings, and W and C1–C6 must admit a common scale wherever both units are available.

EES intervals are converted to a common unit and, when energy and mass are available, compared with the range implied by those two inputs. The CRASH3 inputs bound the energy range when the width, six crush values and coefficients are available. The upper energy bound evaluates the existing formula at the two ends of the admissible B interval. A convex minimization brackets the lower bound in B.

Saving checks that each referenced image is decodable at the path that will be used when reopening the project. A successful save depends on those images remaining available at their referenced paths.

The inferred decimal resolution can differ from the original measurement precision. Exact decimal values and trailing zeroes can be indistinguishable after reading the numbers. Files rounded more coarsely than these limits can be rejected. Small discrepancies within a compatible interval can be accepted. These bounds address storage rounding and do not describe measurement uncertainty.
