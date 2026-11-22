from __future__ import annotations

from dataclasses import dataclass, replace
import math
from pathlib import Path
from typing import Literal, Mapping

import cv2
import numpy as np


# Conservative MVP constants. These are engineering safeguards and scoring
# priors, not scientific acceptance criteria.
SIFT_MAX_FEATURES = 5000
RATIO_TEST_THRESHOLD = 0.70
MIN_KEYPOINTS_PER_IMAGE = 20
MIN_ACCEPTED_MATCHES = 12
MIN_MATCHES_FOR_MODEL = 6
MIN_MODEL_INLIERS = 5
MAX_HYPOTHESES = 3
RANSAC_REPROJECTION_THRESHOLD_PX = 4.0
RANSAC_MAX_ITERATIONS = 5000
RANSAC_CONFIDENCE = 0.995
RANSAC_RANDOM_SEED = 20261119

# Experimental rigid-region refinement. The region follows the documented
# front-up convention and is deliberately not used to generate M1/M2/M3.
RIGID_REGION_X_MIN = 0.20
RIGID_REGION_X_MAX = 0.80
RIGID_REGION_Y_MIN = 0.40
RIGID_REGION_Y_MAX = 0.95
RIGID_COMPATIBILITY_RESIDUAL_PX = 8.0
RIGID_RANSAC_REPROJECTION_THRESHOLD_PX = 3.0
RIGID_MIN_MATCHES = 6
RIGID_MIN_RMSE_IMPROVEMENT_PX = 0.05
RIGID_MIN_RMSE_IMPROVEMENT_RATIO = 0.05
RIGID_MAX_TRANSLATION_CHANGE_PX = 40.0
RIGID_MAX_ROTATION_CHANGE_DEG = 3.0
RIGID_MAX_SCALE_CHANGE = 0.05

MIN_PLAUSIBLE_SCALE = 0.70
MAX_PLAUSIBLE_SCALE = 1.40
MAX_PLAUSIBLE_ROTATION_DEG = 30.0
MAX_PLAUSIBLE_TRANSLATION_DIAGONAL = 0.35

EDGE_FRACTION = 0.12
LATERAL_FRACTION = 0.18
BODY_X_MIN = 0.15
BODY_X_MAX = 0.85
BODY_Y_MIN = 0.30
BODY_Y_MAX = 0.95

IDENTITY_TRANSLATION_DIAGONAL = 0.015
IDENTITY_ROTATION_DEG = 0.50
IDENTITY_SCALE_DELTA = 0.015

HIGH_SCORE_MIN = 85.0
HIGH_SCORE_MARGIN_MIN = 7.0
HIGH_INLIERS_MIN = 10
HIGH_RMSE_MAX_PX = 3.0
HIGH_SUPPORT_AREA_MIN = 0.03
HIGH_BODY_FRACTION_MIN = 0.60
HIGH_MAX_SCALE_DELTA = 0.10
HIGH_MAX_ABS_ROTATION_DEG = 5.0
HIGH_SPARSE_INLIERS_THRESHOLD = 15
HIGH_SPARSE_MAX_SCALE_DELTA = 0.05
HIGH_SPARSE_MAX_ABS_ROTATION_DEG = 3.0
MEDIUM_SCORE_MIN = 60.0

Confidence = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class AlignmentDiagnostics:
    reference_keypoints: int
    deformed_keypoints: int
    candidate_matches: int
    accepted_matches: int


@dataclass(frozen=True)
class AlignmentRefinement:
    rigid_matches: int
    rmse_before_px: float | None
    rmse_after_px: float | None
    original_dx: float
    original_dy: float
    original_rotation_deg: float
    original_scale: float
    refined_dx: float | None
    refined_dy: float | None
    refined_rotation_deg: float | None
    refined_scale: float | None
    translation_change_px: float | None
    rotation_change_deg: float | None
    scale_change: float | None
    used_refined: bool


@dataclass(frozen=True)
class AlignmentHypothesis:
    model_index: int
    dx: float
    dy: float
    rotation_deg: float
    scale: float
    inliers: int
    inlier_ratio: float
    inlier_rmse_px: float
    centroid_x: float
    centroid_y: float
    bbox_x_min: float
    bbox_y_min: float
    bbox_x_max: float
    bbox_y_max: float
    dispersion_x: float
    dispersion_y: float
    support_area_ratio: float
    edge_fraction: float
    lateral_fraction: float
    body_fraction: float
    plausible: bool
    near_identity: bool
    score: float
    refinement: AlignmentRefinement | None = None


@dataclass(frozen=True)
class _ExtractedHypothesis:
    hypothesis: AlignmentHypothesis
    inlier_indices: np.ndarray


@dataclass(frozen=True)
class AutoAlignmentResult:
    diagnostics: AlignmentDiagnostics
    hypotheses: tuple[AlignmentHypothesis, ...]
    confidence: Confidence
    selected_index: int | None
    confidence_reasons: tuple[str, ...]

    @property
    def best(self) -> AlignmentHypothesis | None:
        if not self.hypotheses:
            return None
        return self.hypotheses[0]

    @property
    def selected(self) -> AlignmentHypothesis | None:
        if self.selected_index is None:
            return None
        return self.hypotheses[self.selected_index]


class AutoAlignmentError(RuntimeError):
    def __init__(
        self,
        code: str,
        diagnostics: AlignmentDiagnostics | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.diagnostics = diagnostics


def _read_grayscale(path: str | Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None or image.size == 0:
        raise AutoAlignmentError("image_load_failed")
    return image


def _transform_value(
    transform: Mapping[str, float] | None,
    key: str,
    default: float,
) -> float:
    if transform is None:
        return default
    return float(transform.get(key, default))


def _apply_visual_transform(
    points: np.ndarray,
    width: int,
    height: int,
    transform: Mapping[str, float] | None,
) -> np.ndarray:
    """Map raw pixels through the current QGraphicsPixmapItem similarity."""
    x = _transform_value(transform, "x", 0.0)
    y = _transform_value(transform, "y", 0.0)
    scale = _transform_value(transform, "scale", 1.0)
    rotation_deg = _transform_value(transform, "rotation_deg", 0.0)
    theta = math.radians(rotation_deg)
    cosine = math.cos(theta)
    sine = math.sin(theta)

    center = np.array([width / 2.0, height / 2.0], dtype=np.float64)
    centered = np.asarray(points, dtype=np.float64).reshape(-1, 2) - center
    matrix = scale * np.array(
        [[cosine, -sine], [sine, cosine]], dtype=np.float64
    )
    return centered @ matrix.T + center + np.array([x, y], dtype=np.float64)


def _effective_reference_bounds(
    width: int,
    height: int,
    transform: Mapping[str, float] | None,
) -> tuple[np.ndarray, np.ndarray]:
    corners = np.array(
        [[0.0, 0.0], [width, 0.0], [width, height], [0.0, height]],
        dtype=np.float64,
    )
    effective = _apply_visual_transform(corners, width, height, transform)
    return effective.min(axis=0), effective.max(axis=0)


def _score_hypothesis(
    *,
    dx: float,
    dy: float,
    rotation_deg: float,
    scale: float,
    inliers: int,
    inlier_ratio: float,
    rmse: float,
    normalized_points: np.ndarray,
    reference_diagonal: float,
) -> dict[str, float | bool | tuple[float, ...]]:
    centroid = normalized_points.mean(axis=0)
    bbox_min = normalized_points.min(axis=0)
    bbox_max = normalized_points.max(axis=0)
    dispersion = normalized_points.std(axis=0)
    bbox_size = bbox_max - bbox_min
    support_area = float(bbox_size[0] * bbox_size[1])

    edge_mask = (
        (normalized_points[:, 0] < EDGE_FRACTION)
        | (normalized_points[:, 0] > 1.0 - EDGE_FRACTION)
        | (normalized_points[:, 1] < EDGE_FRACTION)
        | (normalized_points[:, 1] > 1.0 - EDGE_FRACTION)
    )
    lateral_mask = (
        (normalized_points[:, 0] < LATERAL_FRACTION)
        | (normalized_points[:, 0] > 1.0 - LATERAL_FRACTION)
    )
    body_mask = (
        (normalized_points[:, 0] >= BODY_X_MIN)
        & (normalized_points[:, 0] <= BODY_X_MAX)
        & (normalized_points[:, 1] >= BODY_Y_MIN)
        & (normalized_points[:, 1] <= BODY_Y_MAX)
    )
    edge_fraction = float(np.mean(edge_mask))
    lateral_fraction = float(np.mean(lateral_mask))
    body_fraction = float(np.mean(body_mask))

    translation_diagonal = math.hypot(dx, dy) / max(reference_diagonal, 1.0)
    plausible = (
        MIN_PLAUSIBLE_SCALE <= scale <= MAX_PLAUSIBLE_SCALE
        and abs(rotation_deg) <= MAX_PLAUSIBLE_ROTATION_DEG
        and translation_diagonal <= MAX_PLAUSIBLE_TRANSLATION_DIAGONAL
    )
    near_identity = (
        translation_diagonal <= IDENTITY_TRANSLATION_DIAGONAL
        and abs(rotation_deg) <= IDENTITY_ROTATION_DEG
        and abs(scale - 1.0) <= IDENTITY_SCALE_DELTA
    )

    score = 0.0
    score += 18.0 * min(inliers / 12.0, 1.0)
    score += 16.0 * max(0.0, 1.0 - rmse / 5.0)
    score += 12.0 * min(support_area / 0.08, 1.0)
    score += 6.0 * min(float(dispersion[0]) / 0.12, 1.0)
    score += 6.0 * min(float(dispersion[1]) / 0.08, 1.0)
    score += 10.0 * (1.0 - edge_fraction)
    score += 20.0 * body_fraction
    rear_support = min(max((float(centroid[1]) - 0.35) / 0.45, 0.0), 1.0)
    score += 20.0 * rear_support
    score += 8.0 if plausible else -30.0
    score += 4.0 * min(inlier_ratio / 0.30, 1.0)

    if support_area < 0.015:
        score -= 20.0 * (1.0 - support_area / 0.015)
    if bbox_size[0] < 0.12:
        score -= 15.0 * (1.0 - float(bbox_size[0]) / 0.12)
    if bbox_size[1] < 0.06:
        score -= 15.0 * (1.0 - float(bbox_size[1]) / 0.06)
    if lateral_fraction > 0.65:
        score -= 20.0 * (lateral_fraction - 0.65) / 0.35
    if edge_fraction > 0.65:
        score -= 25.0 * (edge_fraction - 0.65) / 0.35
    if near_identity:
        score -= 30.0 * (1.0 - body_fraction)
        if centroid[1] < 0.30:
            score -= 20.0

    return {
        "centroid": (float(centroid[0]), float(centroid[1])),
        "bbox": (
            float(bbox_min[0]),
            float(bbox_min[1]),
            float(bbox_max[0]),
            float(bbox_max[1]),
        ),
        "dispersion": (float(dispersion[0]), float(dispersion[1])),
        "support_area": support_area,
        "edge_fraction": edge_fraction,
        "lateral_fraction": lateral_fraction,
        "body_fraction": body_fraction,
        "plausible": plausible,
        "near_identity": near_identity,
        "score": min(max(score, 0.0), 100.0),
    }


def _extract_hypotheses(
    src_points: np.ndarray,
    dst_points: np.ndarray,
    normalized_dst_points: np.ndarray,
    reference_diagonal: float,
) -> tuple[_ExtractedHypothesis, ...]:
    remaining = np.arange(len(src_points), dtype=np.int32)
    hypotheses: list[_ExtractedHypothesis] = []
    cv2.setRNGSeed(RANSAC_RANDOM_SEED)

    for model_index in range(1, MAX_HYPOTHESES + 1):
        if len(remaining) < MIN_MATCHES_FOR_MODEL:
            break
        matrix, inlier_mask = cv2.estimateAffinePartial2D(
            src_points[remaining],
            dst_points[remaining],
            method=cv2.RANSAC,
            ransacReprojThreshold=RANSAC_REPROJECTION_THRESHOLD_PX,
            maxIters=RANSAC_MAX_ITERATIONS,
            confidence=RANSAC_CONFIDENCE,
            refineIters=10,
        )
        if matrix is None or inlier_mask is None:
            break

        local_inliers = inlier_mask.ravel().astype(bool)
        inlier_indices = remaining[local_inliers]
        inlier_count = int(len(inlier_indices))
        if inlier_count < MIN_MODEL_INLIERS:
            break

        predicted = cv2.transform(src_points[inlier_indices], matrix)
        residuals = predicted.reshape(-1, 2) - dst_points[inlier_indices].reshape(
            -1, 2
        )
        rmse = float(np.sqrt(np.mean(np.sum(residuals * residuals, axis=1))))

        a = float(matrix[0, 0])
        c = float(matrix[1, 0])
        scale = math.hypot(a, c)
        rotation_deg = math.degrees(math.atan2(c, a))
        dx = float(matrix[0, 2])
        dy = float(matrix[1, 2])
        inlier_ratio = inlier_count / len(remaining)
        support = _score_hypothesis(
            dx=dx,
            dy=dy,
            rotation_deg=rotation_deg,
            scale=scale,
            inliers=inlier_count,
            inlier_ratio=inlier_ratio,
            rmse=rmse,
            normalized_points=normalized_dst_points[inlier_indices],
            reference_diagonal=reference_diagonal,
        )
        centroid = support["centroid"]
        bbox = support["bbox"]
        dispersion = support["dispersion"]
        hypotheses.append(
            _ExtractedHypothesis(
                hypothesis=AlignmentHypothesis(
                    model_index=model_index,
                    dx=dx,
                    dy=dy,
                    rotation_deg=rotation_deg,
                    scale=scale,
                    inliers=inlier_count,
                    inlier_ratio=inlier_ratio,
                    inlier_rmse_px=rmse,
                    centroid_x=centroid[0],  # type: ignore[index]
                    centroid_y=centroid[1],  # type: ignore[index]
                    bbox_x_min=bbox[0],  # type: ignore[index]
                    bbox_y_min=bbox[1],  # type: ignore[index]
                    bbox_x_max=bbox[2],  # type: ignore[index]
                    bbox_y_max=bbox[3],  # type: ignore[index]
                    dispersion_x=dispersion[0],  # type: ignore[index]
                    dispersion_y=dispersion[1],  # type: ignore[index]
                    support_area_ratio=float(support["support_area"]),
                    edge_fraction=float(support["edge_fraction"]),
                    lateral_fraction=float(support["lateral_fraction"]),
                    body_fraction=float(support["body_fraction"]),
                    plausible=bool(support["plausible"]),
                    near_identity=bool(support["near_identity"]),
                    score=float(support["score"]),
                ),
                inlier_indices=inlier_indices,
            )
        )
        remaining = remaining[~local_inliers]

    return tuple(
        sorted(hypotheses, key=lambda item: item.hypothesis.score, reverse=True)
    )


def _similarity_matrix(hypothesis: AlignmentHypothesis) -> np.ndarray:
    theta = math.radians(hypothesis.rotation_deg)
    cosine = math.cos(theta)
    sine = math.sin(theta)
    return np.array(
        [
            [hypothesis.scale * cosine, -hypothesis.scale * sine, hypothesis.dx],
            [hypothesis.scale * sine, hypothesis.scale * cosine, hypothesis.dy],
        ],
        dtype=np.float64,
    )


def _decompose_similarity(
    matrix: np.ndarray,
) -> tuple[float, float, float, float]:
    a = float(matrix[0, 0])
    c = float(matrix[1, 0])
    return (
        float(matrix[0, 2]),
        float(matrix[1, 2]),
        math.degrees(math.atan2(c, a)),
        math.hypot(a, c),
    )


def _point_rmse(
    src_points: np.ndarray,
    dst_points: np.ndarray,
    matrix: np.ndarray,
) -> float:
    predicted = cv2.transform(src_points, matrix)
    residuals = predicted.reshape(-1, 2) - dst_points.reshape(-1, 2)
    return float(np.sqrt(np.mean(np.sum(residuals * residuals, axis=1))))


def _refine_hypothesis_in_rigid_region(
    extracted: _ExtractedHypothesis,
    src_points: np.ndarray,
    dst_points: np.ndarray,
    normalized_dst_points: np.ndarray,
    reference_diagonal: float,
) -> AlignmentHypothesis:
    hypothesis = extracted.hypothesis
    original_matrix = _similarity_matrix(hypothesis)
    predicted = cv2.transform(src_points, original_matrix).reshape(-1, 2)
    destinations = dst_points.reshape(-1, 2)
    residuals = np.linalg.norm(predicted - destinations, axis=1)
    rigid_region = (
        (normalized_dst_points[:, 0] >= RIGID_REGION_X_MIN)
        & (normalized_dst_points[:, 0] <= RIGID_REGION_X_MAX)
        & (normalized_dst_points[:, 1] >= RIGID_REGION_Y_MIN)
        & (normalized_dst_points[:, 1] <= RIGID_REGION_Y_MAX)
    )
    compatible = rigid_region & (
        residuals <= RIGID_COMPATIBILITY_RESIDUAL_PX
    )
    rigid_indices = np.flatnonzero(compatible)
    initial_rmse = (
        _point_rmse(
            src_points[rigid_indices],
            dst_points[rigid_indices],
            original_matrix,
        )
        if len(rigid_indices)
        else None
    )

    refinement = AlignmentRefinement(
        rigid_matches=int(len(rigid_indices)),
        rmse_before_px=initial_rmse,
        rmse_after_px=None,
        original_dx=hypothesis.dx,
        original_dy=hypothesis.dy,
        original_rotation_deg=hypothesis.rotation_deg,
        original_scale=hypothesis.scale,
        refined_dx=None,
        refined_dy=None,
        refined_rotation_deg=None,
        refined_scale=None,
        translation_change_px=None,
        rotation_change_deg=None,
        scale_change=None,
        used_refined=False,
    )
    if len(rigid_indices) < RIGID_MIN_MATCHES:
        return replace(hypothesis, refinement=refinement)

    cv2.setRNGSeed(RANSAC_RANDOM_SEED + hypothesis.model_index)
    refined_matrix, refined_inlier_mask = cv2.estimateAffinePartial2D(
        src_points[rigid_indices],
        dst_points[rigid_indices],
        method=cv2.RANSAC,
        ransacReprojThreshold=RIGID_RANSAC_REPROJECTION_THRESHOLD_PX,
        maxIters=RANSAC_MAX_ITERATIONS,
        confidence=RANSAC_CONFIDENCE,
        refineIters=10,
    )
    if refined_matrix is None or refined_inlier_mask is None:
        return replace(hypothesis, refinement=refinement)

    local_inliers = refined_inlier_mask.ravel().astype(bool)
    comparison_indices = rigid_indices[local_inliers]
    if len(comparison_indices) < RIGID_MIN_MATCHES:
        return replace(hypothesis, refinement=refinement)

    rmse_before = _point_rmse(
        src_points[rigid_indices],
        dst_points[rigid_indices],
        original_matrix,
    )
    rmse_after = _point_rmse(
        src_points[rigid_indices],
        dst_points[rigid_indices],
        refined_matrix,
    )
    refined_dx, refined_dy, refined_rotation, refined_scale = (
        _decompose_similarity(refined_matrix)
    )
    translation_change = math.hypot(
        refined_dx - hypothesis.dx, refined_dy - hypothesis.dy
    )
    rotation_change = abs(refined_rotation - hypothesis.rotation_deg)
    scale_change = abs(refined_scale - hypothesis.scale)
    translation_diagonal = math.hypot(refined_dx, refined_dy) / max(
        reference_diagonal, 1.0
    )
    refined_plausible = (
        MIN_PLAUSIBLE_SCALE <= refined_scale <= MAX_PLAUSIBLE_SCALE
        and abs(refined_rotation) <= MAX_PLAUSIBLE_ROTATION_DEG
        and translation_diagonal <= MAX_PLAUSIBLE_TRANSLATION_DIAGONAL
    )
    improved = (
        rmse_after <= rmse_before - RIGID_MIN_RMSE_IMPROVEMENT_PX
        and rmse_after
        <= rmse_before * (1.0 - RIGID_MIN_RMSE_IMPROVEMENT_RATIO)
    )
    bounded_change = (
        translation_change <= RIGID_MAX_TRANSLATION_CHANGE_PX
        and rotation_change <= RIGID_MAX_ROTATION_CHANGE_DEG
        and scale_change <= RIGID_MAX_SCALE_CHANGE
    )
    use_refined = bool(improved and refined_plausible and bounded_change)
    refinement = replace(
        refinement,
        rigid_matches=int(len(rigid_indices)),
        rmse_before_px=rmse_before,
        rmse_after_px=rmse_after,
        refined_dx=refined_dx,
        refined_dy=refined_dy,
        refined_rotation_deg=refined_rotation,
        refined_scale=refined_scale,
        translation_change_px=translation_change,
        rotation_change_deg=rotation_change,
        scale_change=scale_change,
        used_refined=use_refined,
    )
    if not use_refined:
        return replace(hypothesis, refinement=refinement)
    return replace(
        hypothesis,
        dx=refined_dx,
        dy=refined_dy,
        rotation_deg=refined_rotation,
        scale=refined_scale,
        refinement=refinement,
    )


def _classify_confidence(
    hypotheses: tuple[AlignmentHypothesis, ...],
) -> tuple[Confidence, int | None, tuple[str, ...]]:
    if not hypotheses:
        return "low", None, ("no_hypotheses",)

    best = hypotheses[0]
    runner_up_score = hypotheses[1].score if len(hypotheses) > 1 else 0.0
    margin = best.score - runner_up_score
    dominant_nonidentity_model = (
        best.inliers >= 30
        and best.inlier_ratio >= 0.70
        and best.edge_fraction < 0.50
        and not best.near_identity
    )
    high_checks = (
        (best.score >= HIGH_SCORE_MIN, "score_below_high_threshold"),
        (margin >= HIGH_SCORE_MARGIN_MIN, "insufficient_score_margin"),
        (best.inliers >= HIGH_INLIERS_MIN, "insufficient_inliers"),
        (best.inlier_rmse_px <= HIGH_RMSE_MAX_PX, "rmse_above_high_threshold"),
        (
            best.support_area_ratio >= HIGH_SUPPORT_AREA_MIN,
            "support_area_below_high_threshold",
        ),
        (
            best.body_fraction >= HIGH_BODY_FRACTION_MIN
            or dominant_nonidentity_model,
            "insufficient_body_support",
        ),
        (
            abs(best.scale - 1.0) <= HIGH_MAX_SCALE_DELTA,
            "scale_change_too_large",
        ),
        (
            abs(best.rotation_deg) <= HIGH_MAX_ABS_ROTATION_DEG,
            "rotation_too_large",
        ),
        (
            best.inliers >= HIGH_SPARSE_INLIERS_THRESHOLD
            or (
                abs(best.scale - 1.0) <= HIGH_SPARSE_MAX_SCALE_DELTA
                and abs(best.rotation_deg)
                <= HIGH_SPARSE_MAX_ABS_ROTATION_DEG
            ),
            "sparse_extreme_transform",
        ),
        (best.plausible, "implausible_transform"),
    )
    failed_high_checks = tuple(reason for passed, reason in high_checks if not passed)
    if not failed_high_checks:
        return "high", 0, ("high_gate_passed",)
    if best.score >= MEDIUM_SCORE_MIN and best.plausible:
        return "medium", None, failed_high_checks + ("medium_no_auto_apply",)
    low_reasons = failed_high_checks
    if best.score < MEDIUM_SCORE_MIN:
        low_reasons += ("score_below_medium_threshold",)
    if not best.plausible:
        low_reasons += ("implausible_transform",)
    return "low", None, low_reasons


def estimate_auto_alignment(
    reference_path: str | Path,
    deformed_path: str | Path,
    *,
    reference_transform: Mapping[str, float] | None = None,
    deformed_transform: Mapping[str, float] | None = None,
) -> AutoAlignmentResult:
    """Estimate visual-space similarity hypotheses without raster warping."""
    reference = _read_grayscale(reference_path)
    deformed = _read_grayscale(deformed_path)

    sift = cv2.SIFT_create(nfeatures=SIFT_MAX_FEATURES)
    ref_keypoints, ref_descriptors = sift.detectAndCompute(reference, None)
    dam_keypoints, dam_descriptors = sift.detectAndCompute(deformed, None)

    ref_count = len(ref_keypoints)
    dam_count = len(dam_keypoints)
    empty_diagnostics = AlignmentDiagnostics(ref_count, dam_count, 0, 0)
    if (
        ref_descriptors is None
        or dam_descriptors is None
        or ref_count < MIN_KEYPOINTS_PER_IMAGE
        or dam_count < MIN_KEYPOINTS_PER_IMAGE
    ):
        raise AutoAlignmentError("insufficient_features", empty_diagnostics)

    matcher = cv2.BFMatcher(cv2.NORM_L2)
    candidate_pairs = matcher.knnMatch(dam_descriptors, ref_descriptors, k=2)
    reverse_pairs = matcher.knnMatch(ref_descriptors, dam_descriptors, k=2)
    forward = {
        best.queryIdx: best
        for pair in candidate_pairs
        if len(pair) == 2
        for best, second in [pair]
        if best.distance < RATIO_TEST_THRESHOLD * second.distance
    }
    reverse = {
        best.queryIdx: best
        for pair in reverse_pairs
        if len(pair) == 2
        for best, second in [pair]
        if best.distance < RATIO_TEST_THRESHOLD * second.distance
    }
    accepted = [
        match
        for match in forward.values()
        if match.trainIdx in reverse
        and reverse[match.trainIdx].trainIdx == match.queryIdx
    ]
    diagnostics = AlignmentDiagnostics(
        reference_keypoints=ref_count,
        deformed_keypoints=dam_count,
        candidate_matches=len(candidate_pairs),
        accepted_matches=len(accepted),
    )
    if len(accepted) < MIN_ACCEPTED_MATCHES:
        raise AutoAlignmentError("insufficient_matches", diagnostics)

    raw_src = np.float64([dam_keypoints[item.queryIdx].pt for item in accepted])
    raw_dst = np.float64([ref_keypoints[item.trainIdx].pt for item in accepted])
    dam_height, dam_width = deformed.shape
    ref_height, ref_width = reference.shape
    effective_src = _apply_visual_transform(
        raw_src, dam_width, dam_height, deformed_transform
    )
    effective_dst = _apply_visual_transform(
        raw_dst, ref_width, ref_height, reference_transform
    )

    bounds_min, bounds_max = _effective_reference_bounds(
        ref_width, ref_height, reference_transform
    )
    bounds_size = np.maximum(bounds_max - bounds_min, 1.0)
    normalized_dst = (effective_dst - bounds_min) / bounds_size
    reference_diagonal = float(math.hypot(bounds_size[0], bounds_size[1]))

    extracted_hypotheses = _extract_hypotheses(
        effective_src.astype(np.float32).reshape(-1, 1, 2),
        effective_dst.astype(np.float32).reshape(-1, 1, 2),
        normalized_dst,
        reference_diagonal,
    )
    if not extracted_hypotheses:
        raise AutoAlignmentError("estimation_failed", diagnostics)

    src_points = effective_src.astype(np.float32).reshape(-1, 1, 2)
    dst_points = effective_dst.astype(np.float32).reshape(-1, 1, 2)
    hypotheses = tuple(
        _refine_hypothesis_in_rigid_region(
            extracted,
            src_points,
            dst_points,
            normalized_dst,
            reference_diagonal,
        )
        for extracted in extracted_hypotheses
    )

    confidence, selected_index, confidence_reasons = _classify_confidence(
        hypotheses
    )
    return AutoAlignmentResult(
        diagnostics=diagnostics,
        hypotheses=hypotheses,
        confidence=confidence,
        selected_index=selected_index,
        confidence_reasons=confidence_reasons,
    )
