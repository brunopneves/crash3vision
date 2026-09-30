# CRASH3Vision Methodology

## 1. Purpose

CRASH3Vision implements a semi-assisted image-based workflow for measuring permanent vehicle deformation and estimating deformation energy and Energy Equivalent Speed (EES) using CRASH3-derived methods.

The software was developed as a research tool to evaluate whether calibrated digital images can support the extraction of structural deformation parameters that are traditionally measured manually in the field.

The current methodology should be interpreted as a **preliminary proof-of-concept**, with validation concentrated on frontal vehicle deformation.

---

## 2. General workflow

The workflow implemented in CRASH3Vision follows the sequence below:

1. Load a reference image and/or a damaged-vehicle image.
2. Align reference and damaged images when both are available.
3. Calibrate image scale using a known metric reference.
4. Define the total damaged width (**W**).
5. Divide W into five equal intervals.
6. Measure the six structural crush ordinates (**C1–C6**).
7. Define or retrieve the structural stiffness coefficients (**A** and **B**).
8. Calculate deformation energy using the CRASH3-derived formulation.
9. Estimate the Energy Equivalent Speed (**EES**).
10. Save project data, measurements and technical outputs.

Because six crush ordinates are defined across the damaged width, they delimit **five equal intervals**. Accordingly, the interval width used in the energy formulation is **W/5**.

---

## 3. Image acquisition and calibration

The method is intended for digital images with sufficient geometric quality to allow structural interpretation and measurement.

Calibration can use known references visible in the image, including:

- metric rulers or measuring scales;
- known vehicle dimensions;
- other reliable scene references with known dimensions.

In the experimental study, aerial or near-nadir views were preferred because they reduce perspective effects and preserve a more suitable geometric relationship between the vehicle structure and the image plane.

Image quality remains an important limitation. Resolution, contrast, shadows, viewing angle and partial structural obstruction may affect the repeatability of the markings.

---

## 4. Reference and damaged-image alignment

When both an intact/reference image and a damaged image are available, CRASH3Vision allows visual alignment and semi-transparent overlay of both images.

This workflow is useful for comparing the original structural contour with the post-impact geometry.

The software also supports a single-image workflow when only the damaged vehicle image is available.

The purpose of image alignment is not to replace engineering interpretation, but to provide a reproducible visual basis for locating the structural references used during deformation measurement.

---

## 5. Definition of damaged width

The operator manually defines the total damaged width (**W**) over the structural region selected for analysis.

W is subdivided into five equal intervals, establishing the horizontal locations associated with the six crush ordinates:

- C1
- C2
- C3
- C4
- C5
- C6

The six ordinates represent structural deformation depths distributed across the damaged width.

---

## 6. Structural crush measurements

Each crush ordinate represents the depth of permanent structural deformation at its corresponding position.

The markings are performed manually by the operator using the image as the measurement surface after calibration.

The method is therefore **semi-assisted** rather than fully automated: the software supports geometric measurement, visualization, calculation and traceability, while the interpretation of the relevant structural reference remains the responsibility of the examiner.

This residual operator dependence is one of the current limitations of the method and was specifically considered in the experimental evaluation using multiple independent examiners.

---

## 7. Structural offset

In some frontal impacts, the external bumper surface may not correspond directly to the structural member most relevant to energy absorption.

CRASH3Vision therefore provides an optional offset reference line that can be used to represent the approximate original position of the bumper reinforcement or crossmember.

This feature can assist the operator when the internal structure is partially visible or when a structural reference must be projected from the external vehicle contour.

The use of this offset requires technical interpretation and should not be treated as an automatic reconstruction of hidden geometry.

---

## 8. Structural stiffness coefficients

CRASH3-derived energy calculations depend on the structural stiffness coefficients **A** and **B**.

CRASH3Vision supports:

- manual A/B entry;
- A/B values derived from documented NHTSA crash-test data;
- an internal NHTSA-related coefficient library;
- import/export of A/B records;
- a generic demonstration library.

The generic `stiffness_library.json` contains illustrative values only and is not an authoritative technical reference. Any coefficient used in technical or forensic work should be independently verified against an appropriate source.

---

## 9. Deformation energy

The software implements the CRASH3-derived deformation-energy expression used in the associated research:

```text
E = (W/5) × [ (A/2) × Σkᵢ·Cᵢ + (B/6) × Σkᵢ·Cᵢ² + 5G ] × (1 + tan²α)
```

Where:

- **E** is the deformation energy;
- **W** is the damaged width;
- **C1–C6** are the structural crush depths;
- **A** and **B** are structural stiffness coefficients;
- **G = A²/(2B)** is the residual energy term;
- **α** is the impact angle;
- **kᵢ** are the weighting coefficients used in the integration scheme.

The software uses SI units for the calculation workflow.

---

## 10. Energy Equivalent Speed

After deformation energy is estimated, EES is calculated from:

```text
EES = √(2E / m)
```

Where:

- **E** is the estimated deformation energy;
- **m** is the vehicle mass.

EES represents the speed corresponding to the calculated deformation energy and should be interpreted within the assumptions and limitations of the underlying CRASH3 methodology.

---

## 11. Experimental design

The methodology was evaluated in two complementary phases with different purposes.

### Phase 1 — Controlled NHTSA reference

Phase 1 assessed the error associated with obtaining deformation measurements from images by comparing the resulting EES estimates with reference values from controlled NHTSA crash-test documentation.

The sample was constrained by the limited availability of NHTSA tests with overhead or near-nadir camera views suitable for the proposed image-based method.

Five compatible vehicle tests were identified.

To increase measurement replication within this limited sample:

- 3 forensic examiners participated;
- each examiner performed 3 independent measurements per vehicle;
- total: **45 measurements**.

This phase was designed primarily to estimate the error introduced by replacing conventional deformation measurement with image-based measurement under controlled reference conditions.

### Phase 2 — Real-world field application

Phase 2 evaluated the methodology under operational conditions using real damaged vehicles documented by UAV imagery.

The reference consisted of conventional manual field measurements.

The field sample was limited to three suitable damaged vehicles available during the study period.

Again:

- 3 forensic examiners participated;
- each examiner performed 3 independent measurements per vehicle;
- total: **27 measurements**.

This phase should be interpreted as a preliminary operational proof-of-concept rather than as a large-scale validation study.

---

## 12. Traceability and reproducibility

CRASH3Vision was designed to preserve the main elements of the analytical workflow, including:

- source images;
- calibration;
- geometric markings;
- W and C1–C6 measurements;
- A/B coefficients;
- calculation parameters;
- energy and EES outputs;
- project files;
- technical report outputs.

This structure is intended to improve later review, technical audit and reproducibility compared with workflows in which deformation measurements exist only as field notes or manual measurements.

---

## 13. Current scope and limitations

The current methodology has the following limitations:

- small experimental sample;
- validation concentrated on frontal impacts;
- manual interpretation of structural landmarks;
- dependence on image resolution and contrast;
- sensitivity to perspective and viewing geometry;
- possible uncertainty when internal structures are partially hidden;
- dependence on valid stiffness coefficients;
- residual inter-examiner variability.

The current results should therefore be interpreted as a **preliminary experimental validation / proof-of-concept**.

Further research should expand the vehicle sample, impact configurations and acquisition conditions, and investigate automated or AI-assisted structural landmark detection, uncertainty propagation and comparison with photogrammetry, LiDAR and 3D scanning approaches.

---

## 14. Associated research

The methodology was developed and evaluated in:

**B. P. Neves, J. G. Silva Neto, R. de O. Mapele**  
*Metodologia semiassistida por imagem para mensuração de deformações veiculares e estimativa da EES pelo método CRASH3.*  
XXVIII Congresso Nacional de Criminalística — CNC 2026, Brazil.
