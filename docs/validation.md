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

The mean standard deviation across the evaluated vehicles was approximately:

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

The mean standard deviation was:

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

The study observed relatively low dispersion among the repeated measurements within the evaluated conditions.

This suggests that the workflow can support repeatable measurements when operators use a common geometric interpretation protocol.

However, manual landmark placement remains subjective, and inter-examiner variability should be expected, particularly when:

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
| Mean standard deviation | **0.94 km/h** | **0.505 km/h** |
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
- repeated measurements can remain relatively stable across different examiners;
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
