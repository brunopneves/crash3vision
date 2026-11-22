from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
from itertools import combinations
import math
from pathlib import Path
from collections.abc import Sequence
from typing import Literal, Mapping

import cv2
import numpy as np

from app.core.auto_alignment import _apply_visual_transform


REGION_DEFAULT_LENGTH_FRACTION = 0.55
REGION_DEFAULT_HEIGHT_FRACTION = 0.09
REGION_MIN_GESTURE_DIAGONAL_FRACTION = 0.025
REGION_MAX_LENGTH_FRACTION = 0.85
REGION_GESTURE_LENGTH_FACTOR = 1.20
DEFORMED_REGION_MIN_HEIGHT_FRACTION = 0.09
DEFORMED_REGION_VERTICAL_MARGIN_FRACTION = 0.04

REGION_LONGITUDINAL_SIGMA_FRACTION = 0.80
REGION_TRANSVERSE_SIGMA_FRACTION = 0.28
REGION_MIN_MATCH_WEIGHT = 0.25

POINT_ANCHOR_COUNT = 3
POINT_ROI_WIDTH_FRACTION = 0.12
POINT_ROI_HEIGHT_FRACTION = 0.10
POINT_ROI_SIGMA_X_FRACTION = 0.40
POINT_ROI_SIGMA_Y_FRACTION = 0.40
POINT_ROI_EXPANSION_FACTOR = 1.50
MIN_MATCH_CONTRIBUTING_ANCHORS = 3
MIN_INLIER_CONTRIBUTING_ANCHORS = 2
MIN_MATCHES_PER_CONTRIBUTING_ANCHOR = 1
MIN_INLIERS_PER_CONTRIBUTING_ANCHOR = 1

SIFT_MAX_FEATURES = 5000
RATIO_TEST_THRESHOLD = 0.82
SECOND_REGION_RATIO_TEST_THRESHOLD = 0.95
NORMALIZED_RATIO_TEST_THRESHOLD = 0.92
MIN_REGION_KEYPOINTS = 8
MIN_ACCEPTED_MATCHES = 8
MIN_MODEL_MATCHES = 6
MIN_MODEL_INLIERS = 6
MIN_INLIER_SPATIAL_SEGMENTS = 3
MIN_INLIER_SPATIAL_SEGMENTS_WITH_SECOND_REGION = 2
REGION_SPATIAL_SEGMENTS = 5
MAX_CANDIDATES = 3
MAX_SPATIAL_GROUPS = 24
SPATIAL_GROUP_HALF_WIDTH_FRACTION = 0.34
SPATIAL_GROUP_HALF_HEIGHT_FRACTION = 0.20
NON_MUTUAL_MATCH_WEIGHT = 0.75
RANSAC_REPROJECTION_THRESHOLD_PX = 4.0
SECOND_REGION_RANSAC_REPROJECTION_THRESHOLD_PX = 6.0
RANSAC_MAX_ITERATIONS = 5000
RANSAC_CONFIDENCE = 0.995
RANSAC_RANDOM_SEED = 20261120

STRUCTURAL_BLUR_SIGMA = 1.2
STRUCTURAL_SOBEL_KERNEL_SIZE = 3
STRUCTURAL_DISPLACEMENT_RADIUS_DIAGONAL = 0.035
STRUCTURAL_MAX_MOTION_GROUPS = 32
STRUCTURAL_MIN_MATCH_CONTRIBUTING_ANCHORS = 2

NORMALIZED_REFERENCE_SCALES = (1.5, 2.0)
NORMALIZED_DEFORMED_SCALES = (0.90, 1.0, 1.10)
NORMALIZED_TEMPLATE_SCALES = (0.85, 0.925, 1.0, 1.075, 1.15)
NORMALIZED_TEMPLATE_TOP_MATCHES = 6
NORMALIZED_TEMPLATE_MIN_SCORE = 0.20
NORMALIZED_TEMPLATE_MAX_RESIDUAL_DIAGONAL = 0.02

# Anchor suggestions are advisory only.  These constants do not participate in
# the final similarity estimation or its acceptance gates.
SUGGESTION_SIFT_MAX_FEATURES = 3000
SUGGESTION_REFERENCE_SCALES = (1.0, 1.5)
SUGGESTION_DEFORMED_SCALES = (0.90, 1.0, 1.10)
SUGGESTION_RATIO_TEST_THRESHOLD = 0.90
SUGGESTION_GEOMETRIC_RATIO_TEST_THRESHOLD = 0.92
SUGGESTION_GRID_X = (0.30, 0.40, 0.50, 0.60)
SUGGESTION_GRID_Y = (0.36, 0.46, 0.56, 0.66, 0.76)
SUGGESTION_MIN_MATCHES_PER_SCALE_PAIR = 2
SUGGESTION_MIN_SEPARATION_NORMALIZED = 0.20
SUGGESTION_MAX_ROTATION_DEG = 12.0
SUGGESTION_MIN_SCALE = 0.75
SUGGESTION_MAX_SCALE = 1.25
SUGGESTION_MODEL_TRANSLATION_TOLERANCE_DIAGONAL = 0.035
SUGGESTION_MODEL_ROTATION_TOLERANCE_DEG = 2.5
SUGGESTION_MODEL_SCALE_TOLERANCE = 0.04

MIN_PLAUSIBLE_SCALE = 0.90
MAX_PLAUSIBLE_SCALE = 1.10
MAX_PLAUSIBLE_ROTATION_DEG = 5.0
MAX_PLAUSIBLE_TRANSLATION_DIAGONAL = 0.40
MAX_ACCEPTABLE_RMSE_PX = 2.0
MIN_ACCEPTABLE_INLIER_RATIO = 0.25
MIN_ACCEPTABLE_INLIER_RATIO_WITH_SECOND_REGION = 0.10
AMBIGUOUS_SCORE_RATIO = 0.90
AMBIGUOUS_MIN_INLIER_FRACTION = 0.70
AMBIGUOUS_TRANSLATION_PX = 5.0
AMBIGUOUS_ROTATION_DEG = 0.50
AMBIGUOUS_SCALE_DELTA = 0.01

RigidAlignmentStatus = Literal["success", "needs_second_region", "failure"]


@dataclass(frozen=True)
class RigidRegion:
    center_x: float
    center_y: float
    length: float
    height: float
    angle_deg: float = 0.0
    directional: bool = False
    point_anchor: bool = False
    roi_scale: float = 1.0

    def normalized(self, image_width: int, image_height: int) -> tuple[float, ...]:
        return (
            self.center_x / max(float(image_width), 1.0),
            self.center_y / max(float(image_height), 1.0),
            self.length / max(float(image_width), 1.0),
            self.height / max(float(image_height), 1.0),
            self.angle_deg,
        )


@dataclass(frozen=True)
class RigidAlignmentDiagnostics:
    reference_keypoints: int
    deformed_keypoints: int
    region_keypoints: int
    accepted_matches: int
    anchor_keypoints: tuple[int, ...] = ()
    anchor_matches: tuple[int, ...] = ()
    roi_scale: float = 1.0
    expansion_attempted: bool = False
    structural_fallback: bool = False
    normalized_multiscale: bool = False
    detection_scales: tuple[float, float] = (1.0, 1.0)


@dataclass(frozen=True)
class RigidAlignmentCandidate:
    dx: float
    dy: float
    rotation_deg: float
    scale: float
    inliers: int
    inlier_ratio: float
    rmse_px: float
    weighted_rmse_px: float
    mean_region_weight: float
    score: float
    spatial_segments: int = REGION_SPATIAL_SEGMENTS
    anchor_matches: tuple[int, ...] = ()
    anchor_inliers: tuple[int, ...] = ()


@dataclass(frozen=True)
class RigidAlignmentResult:
    status: RigidAlignmentStatus
    reason: str
    diagnostics: RigidAlignmentDiagnostics
    candidates: tuple[RigidAlignmentCandidate, ...]

    @property
    def best(self) -> RigidAlignmentCandidate | None:
        return self.candidates[0] if self.candidates else None


@dataclass(frozen=True)
class RigidAnchorSuggestion:
    region: RigidRegion
    score: float
    keypoints: int
    probable_matches: int
    stable_scale_pairs: int
    gradient_score: float
    distinctiveness: float


@dataclass(frozen=True)
class RigidAnchorSuggestionResult:
    suggestions: tuple[RigidAnchorSuggestion, ...]
    reference_keypoints: int
    deformed_keypoints: int


def make_rigid_region(
    image_width: int,
    image_height: int,
    center: tuple[float, float],
    drag_end: tuple[float, float] | None = None,
) -> RigidRegion:
    width = max(float(image_width), 1.0)
    height = max(float(image_height), 1.0)
    default_length = width * REGION_DEFAULT_LENGTH_FRACTION
    region_height = height * REGION_DEFAULT_HEIGHT_FRACTION
    directional = False
    angle_deg = 0.0
    length = default_length
    if drag_end is not None:
        dx = float(drag_end[0]) - float(center[0])
        dy = float(drag_end[1]) - float(center[1])
        gesture_length = math.hypot(dx, dy)
        minimum_gesture = math.hypot(width, height) * (
            REGION_MIN_GESTURE_DIAGONAL_FRACTION
        )
        if gesture_length >= minimum_gesture:
            directional = True
            angle_deg = math.degrees(math.atan2(dy, dx))
            length = max(default_length, gesture_length * REGION_GESTURE_LENGTH_FACTOR)
            length = min(length, width * REGION_MAX_LENGTH_FRACTION)
    return RigidRegion(
        center_x=float(center[0]),
        center_y=float(center[1]),
        length=length,
        height=region_height,
        angle_deg=angle_deg,
        directional=directional,
    )


def make_adaptive_deformed_region(
    image_width: int,
    image_height: int,
    center: tuple[float, float],
    reference_regions: Sequence[RigidRegion],
    reference_image_height: int,
    drag_end: tuple[float, float] | None = None,
) -> RigidRegion:
    region = make_rigid_region(
        image_width,
        image_height,
        center,
        drag_end,
    )
    reference_height = max(float(reference_image_height), 1.0)
    centers_y = [float(item.center_y) for item in reference_regions]
    vertical_span_fraction = (
        (max(centers_y) - min(centers_y)) / reference_height
        if centers_y
        else 0.0
    )
    height_fraction = max(
        DEFORMED_REGION_MIN_HEIGHT_FRACTION,
        vertical_span_fraction
        + 2.0 * DEFORMED_REGION_VERTICAL_MARGIN_FRACTION,
    )
    return replace(
        region,
        height=max(float(image_height), 1.0) * height_fraction,
    )


def make_point_anchor_region(
    image_width: int,
    image_height: int,
    center: tuple[float, float],
) -> RigidRegion:
    return RigidRegion(
        center_x=float(center[0]),
        center_y=float(center[1]),
        length=max(float(image_width), 1.0) * POINT_ROI_WIDTH_FRACTION,
        height=max(float(image_height), 1.0) * POINT_ROI_HEIGHT_FRACTION,
        point_anchor=True,
    )


def expand_point_anchor_regions(
    regions: Sequence[RigidRegion],
    factor: float = POINT_ROI_EXPANSION_FACTOR,
) -> tuple[RigidRegion, ...]:
    scale_factor = max(float(factor), 1.0)
    return tuple(
        replace(
            region,
            length=region.length * scale_factor,
            height=region.height * scale_factor,
            roi_scale=region.roi_scale * scale_factor,
        )
        for region in regions
    )


def corrected_reference_rotation(
    current_rotation_deg: float,
    region: RigidRegion,
) -> tuple[float, float]:
    if not region.directional:
        return float(current_rotation_deg), 0.0
    effective_gesture_angle = float(current_rotation_deg) + region.angle_deg
    correction = -effective_gesture_angle
    return float(current_rotation_deg) + correction, correction


def region_weights(points: np.ndarray, region: RigidRegion) -> np.ndarray:
    flat = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    theta = math.radians(region.angle_deg)
    cosine = math.cos(theta)
    sine = math.sin(theta)
    delta = flat - np.array([region.center_x, region.center_y], dtype=np.float64)
    longitudinal = cosine * delta[:, 0] + sine * delta[:, 1]
    transverse = -sine * delta[:, 0] + cosine * delta[:, 1]
    if region.point_anchor:
        sigma_long = max(region.length * POINT_ROI_SIGMA_X_FRACTION, 1.0)
        sigma_trans = max(region.height * POINT_ROI_SIGMA_Y_FRACTION, 1.0)
    else:
        sigma_long = max(region.length * REGION_LONGITUDINAL_SIGMA_FRACTION, 1.0)
        sigma_trans = max(region.height * REGION_TRANSVERSE_SIGMA_FRACTION, 1.0)
    return np.exp(
        -0.5
        * (
            (longitudinal / sigma_long) ** 2
            + (transverse / sigma_trans) ** 2
        )
    )


def _region_segment_indices(
    points: np.ndarray,
    region: RigidRegion,
) -> np.ndarray:
    flat = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    theta = math.radians(region.angle_deg)
    delta = flat - np.array([region.center_x, region.center_y], dtype=np.float64)
    longitudinal = math.cos(theta) * delta[:, 0] + math.sin(theta) * delta[:, 1]
    normalized = longitudinal / max(region.length, 1.0) + 0.5
    return np.clip(
        np.floor(normalized * REGION_SPATIAL_SEGMENTS),
        0,
        REGION_SPATIAL_SEGMENTS - 1,
    ).astype(np.int32)


def _read_grayscale(path: str | Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None or image.size == 0:
        raise ValueError(f"Failed to load image: {path}")
    return image


def _suggestion_contrast_image(image: np.ndarray) -> np.ndarray:
    return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(image)


def _suggestion_normalized_image(image: np.ndarray) -> np.ndarray:
    clahe = _suggestion_contrast_image(image)
    blurred = cv2.GaussianBlur(clahe, (0, 0), 1.0)
    grad_x = cv2.Sobel(blurred, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(blurred, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(grad_x, grad_y)
    gradient = cv2.normalize(
        magnitude,
        None,
        0,
        255,
        cv2.NORM_MINMAX,
        dtype=cv2.CV_8U,
    )
    return cv2.addWeighted(clahe, 0.35, gradient, 0.65, 0.0)


def _suggestion_sift_features(
    image: np.ndarray,
    scales: Sequence[float],
    *,
    structural: bool | None = True,
) -> tuple[tuple[np.ndarray, np.ndarray], ...]:
    sift = cv2.SIFT_create(nfeatures=SUGGESTION_SIFT_MAX_FEATURES)
    if structural is None:
        normalized = image
    elif structural:
        normalized = _suggestion_normalized_image(image)
    else:
        normalized = _suggestion_contrast_image(image)
    features: list[tuple[np.ndarray, np.ndarray]] = []
    for scale in scales:
        working = normalized
        if not math.isclose(scale, 1.0):
            working = cv2.resize(
                normalized,
                None,
                fx=scale,
                fy=scale,
                interpolation=cv2.INTER_CUBIC,
            )
        keypoints, descriptors = sift.detectAndCompute(working, None)
        if descriptors is None or not keypoints:
            features.append(
                (np.empty((0, 2), dtype=np.float64), np.empty((0, 128), dtype=np.float32))
            )
            continue
        points = np.float64([item.pt for item in keypoints]) / max(scale, 0.1)
        features.append((points, descriptors))
    return tuple(features)


def _normalized_metric(values: Sequence[float]) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        return array
    lower = float(np.percentile(array, 10.0))
    upper = float(np.percentile(array, 90.0))
    if upper <= lower + 1.0e-9:
        return np.ones_like(array) if upper > 0.0 else np.zeros_like(array)
    return np.clip((array - lower) / (upper - lower), 0.0, 1.0)


def _suggestion_mutual_matches(
    reference_features: Sequence[tuple[np.ndarray, np.ndarray]],
    deformed_features: Sequence[tuple[np.ndarray, np.ndarray]],
) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    matches: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    matcher = cv2.BFMatcher(cv2.NORM_L2)
    for ref_points, ref_descriptors in reference_features:
        for dam_points, dam_descriptors in deformed_features:
            if len(ref_descriptors) == 0 or len(dam_descriptors) < 2:
                matches.append(
                    (
                        np.empty((0, 2), dtype=np.float64),
                        np.empty((0, 2), dtype=np.float64),
                        np.empty(0, dtype=np.float64),
                    )
                )
                continue
            pairs = matcher.knnMatch(ref_descriptors, dam_descriptors, k=2)
            reverse_pairs = matcher.knnMatch(
                dam_descriptors, ref_descriptors, k=2
            )
            reverse = {
                best.queryIdx: best
                for pair in reverse_pairs
                if len(pair) == 2
                for best, second in [pair]
                if best.distance
                < SUGGESTION_RATIO_TEST_THRESHOLD * second.distance
            }
            accepted_ref: list[tuple[float, float]] = []
            accepted_dam: list[tuple[float, float]] = []
            qualities: list[float] = []
            for pair in pairs:
                if len(pair) != 2:
                    continue
                best, second = pair
                ratio = best.distance / max(second.distance, 1.0e-9)
                if ratio >= SUGGESTION_RATIO_TEST_THRESHOLD:
                    continue
                if (
                    best.trainIdx not in reverse
                    or reverse[best.trainIdx].trainIdx != best.queryIdx
                ):
                    continue
                accepted_ref.append(tuple(ref_points[best.queryIdx]))
                accepted_dam.append(tuple(dam_points[best.trainIdx]))
                qualities.append(1.0 - ratio)
            matches.append(
                (
                    np.asarray(accepted_ref, dtype=np.float64).reshape(-1, 2),
                    np.asarray(accepted_dam, dtype=np.float64).reshape(-1, 2),
                    np.asarray(qualities, dtype=np.float64),
                )
            )
    return matches


def _suggestion_geometric_matches(
    reference_features: Sequence[tuple[np.ndarray, np.ndarray]],
    deformed_features: Sequence[tuple[np.ndarray, np.ndarray]],
) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    matches: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    matcher = cv2.BFMatcher(cv2.NORM_L2)
    for ref_points, ref_descriptors in reference_features:
        for dam_points, dam_descriptors in deformed_features:
            if len(ref_descriptors) == 0 or len(dam_descriptors) < 2:
                matches.append(
                    (
                        np.empty((0, 2), dtype=np.float64),
                        np.empty((0, 2), dtype=np.float64),
                        np.empty(0, dtype=np.float64),
                    )
                )
                continue
            pairs = matcher.knnMatch(ref_descriptors, dam_descriptors, k=2)
            accepted_by_destination: dict[int, tuple[cv2.DMatch, float]] = {}
            for pair in pairs:
                if len(pair) != 2:
                    continue
                best, second = pair
                ratio = best.distance / max(second.distance, 1.0e-9)
                if ratio >= SUGGESTION_GEOMETRIC_RATIO_TEST_THRESHOLD:
                    continue
                current = accepted_by_destination.get(best.trainIdx)
                if current is None or ratio < current[1]:
                    accepted_by_destination[best.trainIdx] = (best, ratio)
            accepted = list(accepted_by_destination.values())
            matches.append(
                (
                    np.asarray(
                        [ref_points[match.queryIdx] for match, _ in accepted],
                        dtype=np.float64,
                    ).reshape(-1, 2),
                    np.asarray(
                        [dam_points[match.trainIdx] for match, _ in accepted],
                        dtype=np.float64,
                    ).reshape(-1, 2),
                    np.asarray(
                        [1.0 - ratio for _, ratio in accepted],
                        dtype=np.float64,
                    ),
                )
            )
    return matches


def suggest_rigid_region_anchors(
    reference_path: str | Path,
    deformed_path: str | Path,
) -> RigidAnchorSuggestionResult:
    """Suggest three distributed reference anchors without estimating a transform."""
    reference = Path(reference_path).resolve()
    deformed = Path(deformed_path).resolve()
    return _suggest_rigid_region_anchors_cached(
        str(reference),
        reference.stat().st_mtime_ns,
        str(deformed),
        deformed.stat().st_mtime_ns,
    )


@lru_cache(maxsize=16)
def _suggest_rigid_region_anchors_cached(
    reference_path: str,
    reference_mtime_ns: int,
    deformed_path: str,
    deformed_mtime_ns: int,
) -> RigidAnchorSuggestionResult:
    _ = reference_mtime_ns, deformed_mtime_ns
    reference = _read_grayscale(reference_path)
    deformed = _read_grayscale(deformed_path)
    ref_features = _suggestion_sift_features(
        reference, SUGGESTION_REFERENCE_SCALES
    )
    dam_features = _suggestion_sift_features(
        deformed, SUGGESTION_DEFORMED_SCALES
    )
    contrast_ref_features = _suggestion_sift_features(
        reference,
        SUGGESTION_REFERENCE_SCALES,
        structural=False,
    )
    contrast_dam_features = _suggestion_sift_features(
        deformed,
        SUGGESTION_DEFORMED_SCALES,
        structural=False,
    )
    geometric_ref_features = _suggestion_sift_features(
        reference,
        SUGGESTION_REFERENCE_SCALES,
        structural=None,
    )
    geometric_dam_features = _suggestion_sift_features(
        deformed,
        SUGGESTION_DEFORMED_SCALES,
        structural=None,
    )
    reference_keypoints = len(ref_features[0][0]) if ref_features else 0
    deformed_keypoints = (
        len(dam_features[1][0])
        if len(dam_features) > 1
        else (len(dam_features[0][0]) if dam_features else 0)
    )

    pair_matches = _suggestion_mutual_matches(ref_features, dam_features)
    pair_matches.extend(
        _suggestion_mutual_matches(
            contrast_ref_features,
            contrast_dam_features,
        )
    )
    pair_matches.extend(
        _suggestion_geometric_matches(
            geometric_ref_features,
            geometric_dam_features,
        )
    )

    normalized_reference = _suggestion_normalized_image(reference)
    gradient = normalized_reference.astype(np.float32)
    height, width = reference.shape
    length = width * POINT_ROI_WIDTH_FRACTION
    region_height = height * POINT_ROI_HEIGHT_FRACTION

    raw: list[dict[str, float | int | RigidRegion]] = []
    for normalized_y in SUGGESTION_GRID_Y:
        for normalized_x in SUGGESTION_GRID_X:
            region = make_point_anchor_region(
                width,
                height,
                (normalized_x * width, normalized_y * height),
            )
            half_width = length / 2.0
            half_height = region_height / 2.0

            def inside(points: np.ndarray) -> np.ndarray:
                if len(points) == 0:
                    return np.zeros(0, dtype=bool)
                return (
                    (np.abs(points[:, 0] - region.center_x) <= half_width)
                    & (np.abs(points[:, 1] - region.center_y) <= half_height)
                )

            density = int(
                round(
                    sum(
                        int(np.count_nonzero(inside(points)))
                        for points, _ in (*ref_features, *contrast_ref_features)
                    )
                    / max(len(ref_features) + len(contrast_ref_features), 1)
                )
            )
            match_counts: list[int] = []
            distinct_values: list[float] = []
            region_ref_matches: list[np.ndarray] = []
            region_dam_matches: list[np.ndarray] = []
            pair_ref_matches: list[np.ndarray] = []
            pair_dam_matches: list[np.ndarray] = []
            for points, dam_points, qualities in pair_matches:
                mask = inside(points)
                count = int(np.count_nonzero(mask))
                match_counts.append(count)
                pair_ref_matches.append(points[mask])
                pair_dam_matches.append(dam_points[mask])
                if count:
                    distinct_values.extend(float(value) for value in qualities[mask])
                    region_ref_matches.append(points[mask])
                    region_dam_matches.append(dam_points[mask])
            stable_pairs = sum(
                count >= SUGGESTION_MIN_MATCHES_PER_SCALE_PAIR
                for count in match_counts
            )
            probable_matches = int(round(sum(match_counts) / max(len(match_counts), 1)))
            distinctiveness = (
                float(np.mean(distinct_values)) if distinct_values else 0.0
            )
            x0 = max(int(round(region.center_x - half_width)), 0)
            x1 = min(int(round(region.center_x + half_width)), width)
            y0 = max(int(round(region.center_y - half_height)), 0)
            y1 = min(int(round(region.center_y + half_height)), height)
            gradient_score = (
                float(np.mean(gradient[y0:y1, x0:x1]))
                if x1 > x0 and y1 > y0
                else 0.0
            )
            raw.append(
                {
                    "region": region,
                    "keypoints": density,
                    "matches": probable_matches,
                    "stable": stable_pairs,
                    "gradient": gradient_score,
                    "distinctiveness": distinctiveness,
                    "ref_matches": (
                        np.vstack(region_ref_matches)
                        if region_ref_matches
                        else np.empty((0, 2), dtype=np.float64)
                    ),
                    "dam_matches": (
                        np.vstack(region_dam_matches)
                        if region_dam_matches
                        else np.empty((0, 2), dtype=np.float64)
                    ),
                    "pair_ref_matches": tuple(pair_ref_matches),
                    "pair_dam_matches": tuple(pair_dam_matches),
                }
            )

    density_score = _normalized_metric([float(item["keypoints"]) for item in raw])
    match_score = _normalized_metric([float(item["matches"]) for item in raw])
    stability_score = _normalized_metric([float(item["stable"]) for item in raw])
    gradient_score = _normalized_metric([float(item["gradient"]) for item in raw])
    distinct_score = _normalized_metric(
        [float(item["distinctiveness"]) for item in raw]
    )
    base_scores = (
        0.20 * density_score
        + 0.35 * match_score
        + 0.15 * stability_score
        + 0.15 * gradient_score
        + 0.15 * distinct_score
    )

    selected: list[int] = []
    best_combination_score = -math.inf
    eligible = [
        index
        for index, item in enumerate(raw)
        if int(item["matches"]) >= 2
        and int(item["stable"]) >= 2
    ]
    pool_source = eligible if len(eligible) >= POINT_ANCHOR_COUNT else list(range(len(raw)))
    candidate_pool = sorted(
        pool_source,
        key=lambda index: float(base_scores[index]),
    )[-20:]
    for candidate_indices in combinations(candidate_pool, POINT_ANCHOR_COUNT):
        centers = []
        for index in candidate_indices:
            region = raw[index]["region"]
            assert isinstance(region, RigidRegion)
            centers.append(
                np.array(
                    [region.center_x / width, region.center_y / height],
                    dtype=np.float64,
                )
            )
        distances = [
            float(np.linalg.norm(centers[left] - centers[right]))
            for left, right in combinations(range(POINT_ANCHOR_COUNT), 2)
        ]
        minimum_distance = min(distances)
        if minimum_distance < SUGGESTION_MIN_SEPARATION_NORMALIZED:
            continue
        first_delta = centers[1] - centers[0]
        second_delta = centers[2] - centers[0]
        triangle_area = abs(
            float(
                first_delta[0] * second_delta[1]
                - first_delta[1] * second_delta[0]
            )
        ) / 2.0
        models: list[dict[str, object]] = []
        for pair_index in range(len(pair_matches)):
            ref_parts = [
                raw[index]["pair_ref_matches"][pair_index]
                for index in candidate_indices
            ]
            dam_parts = [
                raw[index]["pair_dam_matches"][pair_index]
                for index in candidate_indices
            ]
            ref_matches = np.vstack(ref_parts)
            dam_matches = np.vstack(dam_parts)
            if len(ref_matches) < MIN_MODEL_MATCHES:
                continue
            anchor_ids = np.concatenate(
                [
                    np.full(len(points), anchor, dtype=np.int32)
                    for anchor, points in enumerate(ref_parts)
                ]
            )
            cv2.setRNGSeed(RANSAC_RANDOM_SEED + pair_index)
            matrix, mask = cv2.estimateAffinePartial2D(
                dam_matches.astype(np.float32).reshape(-1, 1, 2),
                ref_matches.astype(np.float32).reshape(-1, 1, 2),
                method=cv2.RANSAC,
                ransacReprojThreshold=RANSAC_REPROJECTION_THRESHOLD_PX,
                maxIters=1000,
                confidence=0.99,
                refineIters=5,
            )
            if matrix is None or mask is None:
                continue
            scale = math.hypot(float(matrix[0, 0]), float(matrix[1, 0]))
            rotation = math.degrees(
                math.atan2(float(matrix[1, 0]), float(matrix[0, 0]))
            )
            if (
                not SUGGESTION_MIN_SCALE <= scale <= SUGGESTION_MAX_SCALE
                or abs(rotation) > SUGGESTION_MAX_ROTATION_DEG
            ):
                continue
            inlier_mask = mask.ravel().astype(bool)
            inliers = int(np.count_nonzero(inlier_mask))
            if inliers < 3:
                continue
            anchor_inliers = np.bincount(
                anchor_ids[inlier_mask], minlength=POINT_ANCHOR_COUNT
            )
            projected = cv2.transform(
                dam_matches.astype(np.float32).reshape(-1, 1, 2), matrix
            ).reshape(-1, 2)
            residuals = np.linalg.norm(projected - ref_matches, axis=1)
            models.append(
                {
                    "dx": float(matrix[0, 2]),
                    "dy": float(matrix[1, 2]),
                    "rotation": rotation,
                    "scale": scale,
                    "inliers": inliers,
                    "anchor_inliers": anchor_inliers,
                    "rmse": float(
                        math.sqrt(np.mean(np.square(residuals[inlier_mask])))
                    ),
                    "geometric": pair_index >= 12,
                    "preferred_geometric": pair_index == 15,
                }
            )

        coherent_models: list[dict[str, object]] = []
        coherent_model_score = -math.inf
        diagonal = math.hypot(width, height)
        for seed in models:
            cluster = [
                model
                for model in models
                if math.hypot(
                    float(model["dx"]) - float(seed["dx"]),
                    float(model["dy"]) - float(seed["dy"]),
                )
                <= diagonal * SUGGESTION_MODEL_TRANSLATION_TOLERANCE_DIAGONAL
                and abs(float(model["rotation"]) - float(seed["rotation"]))
                <= SUGGESTION_MODEL_ROTATION_TOLERANCE_DEG
                and abs(float(model["scale"]) - float(seed["scale"]))
                <= SUGGESTION_MODEL_SCALE_TOLERANCE
            ]
            cluster_score = sum(
                int(model["inliers"])
                * (1.5 if bool(model["geometric"]) else 1.0)
                + (
                    4.0
                    if np.all(np.asarray(model["anchor_inliers"]) > 0)
                    else 0.0
                )
                for model in cluster
            )
            if cluster_score > coherent_model_score:
                coherent_model_score = float(cluster_score)
                coherent_models = cluster

        coherent_inliers = sum(
            int(model["inliers"]) for model in coherent_models
        )
        all_anchor_models = sum(
            bool(np.all(np.asarray(model["anchor_inliers"]) > 0))
            for model in coherent_models
        )
        balanced_anchor_inliers = sum(
            int(np.min(np.asarray(model["anchor_inliers"])))
            for model in coherent_models
        )
        mean_rmse = (
            float(np.mean([float(model["rmse"]) for model in coherent_models]))
            if coherent_models
            else RANSAC_REPROJECTION_THRESHOLD_PX * 2.0
        )
        geometric_inliers = sum(
            int(model["inliers"])
            for model in coherent_models
            if bool(model["geometric"])
        )
        preferred_geometric_inliers = max(
            (
                int(model["inliers"])
                for model in coherent_models
                if bool(model["preferred_geometric"])
            ),
            default=0,
        )
        preferred_anchor_balance = max(
            (
                int(np.min(np.asarray(model["anchor_inliers"])))
                for model in coherent_models
                if bool(model["preferred_geometric"])
            ),
            default=0,
        )
        quality = float(np.mean(base_scores[list(candidate_indices)]))
        centroid = np.mean(np.vstack(centers), axis=0)
        interior_centroid_score = 1.0 - min(
            float(np.linalg.norm(centroid - np.array([0.5, 0.58]))) / 0.35,
            1.0,
        )
        vertical_order = sorted(range(POINT_ANCHOR_COUNT), key=lambda i: centers[i][1])
        upper = centers[vertical_order[0]]
        lower = [centers[index] for index in vertical_order[1:]]
        lower_midpoint_x = (lower[0][0] + lower[1][0]) / 2.0
        triangle_balance = 1.0 - min(
            abs(float(upper[0] - lower_midpoint_x)) / 0.30,
            1.0,
        )
        regional_match_counts = [
            max(int(raw[index]["matches"]), 1)
            for index in candidate_indices
        ]
        regional_match_balance = min(regional_match_counts) / max(
            regional_match_counts
        )
        combination_score = (
            quality
            + 0.30 * min(minimum_distance / 0.45, 1.0)
            + 0.25 * min(triangle_area / 0.05, 1.0)
            + 0.55 * min(len(coherent_models) / 3.0, 1.0)
            + 0.45 * min(coherent_inliers / 24.0, 1.0)
            + 0.65 * min(all_anchor_models / 2.0, 1.0)
            + 0.40 * min(balanced_anchor_inliers / 4.0, 1.0)
            + 0.70 * min(geometric_inliers / 18.0, 1.0)
            + 0.45 * min(preferred_geometric_inliers / 6.0, 1.0)
            + 1.20 * min(preferred_anchor_balance / 2.0, 1.0)
            - (0.70 if preferred_anchor_balance == 0 else 0.0)
            + 0.20
            * max(
                0.0,
                1.0 - mean_rmse / RANSAC_REPROJECTION_THRESHOLD_PX,
            )
            + 0.80 * interior_centroid_score
            + 0.70 * triangle_balance
            + 2.00 * math.sqrt(regional_match_balance)
            - 1.20 * (1.0 - regional_match_balance)
        )
        if combination_score > best_combination_score:
            best_combination_score = combination_score
            selected = list(candidate_indices)

    if not selected:
        selected = list(
            np.argsort(base_scores)[-POINT_ANCHOR_COUNT:][::-1]
        )
    for index in selected:
        raw[index]["final_score"] = float(base_scores[index])

    suggestions = tuple(
        RigidAnchorSuggestion(
            region=raw[index]["region"],  # type: ignore[arg-type]
            score=float(raw[index].get("final_score", base_scores[index])),
            keypoints=int(raw[index]["keypoints"]),
            probable_matches=int(raw[index]["matches"]),
            stable_scale_pairs=int(raw[index]["stable"]),
            gradient_score=float(raw[index]["gradient"]),
            distinctiveness=float(raw[index]["distinctiveness"]),
        )
        for index in selected
    )
    return RigidAnchorSuggestionResult(
        suggestions=suggestions,
        reference_keypoints=reference_keypoints,
        deformed_keypoints=deformed_keypoints,
    )


def _structural_gradient_image(image: np.ndarray) -> np.ndarray:
    """Return a softly blurred Sobel-magnitude image for structural matching."""
    blurred = cv2.GaussianBlur(
        image,
        (0, 0),
        sigmaX=STRUCTURAL_BLUR_SIGMA,
        sigmaY=STRUCTURAL_BLUR_SIGMA,
    )
    gradient_x = cv2.Sobel(
        blurred,
        cv2.CV_32F,
        1,
        0,
        ksize=STRUCTURAL_SOBEL_KERNEL_SIZE,
    )
    gradient_y = cv2.Sobel(
        blurred,
        cv2.CV_32F,
        0,
        1,
        ksize=STRUCTURAL_SOBEL_KERNEL_SIZE,
    )
    magnitude = cv2.magnitude(gradient_x, gradient_y)
    return cv2.normalize(
        magnitude,
        None,
        0,
        255,
        cv2.NORM_MINMAX,
        dtype=cv2.CV_8U,
    )


def _region_detection_mask(
    image_shape: tuple[int, int],
    regions: Sequence[RigidRegion],
    scale: float,
) -> np.ndarray:
    height, width = image_shape
    mask = np.zeros((height, width), dtype=np.uint8)
    for region in regions:
        theta = math.radians(region.angle_deg)
        cosine = math.cos(theta)
        sine = math.sin(theta)
        half_length = region.length * scale / 2.0
        half_height = region.height * scale / 2.0
        center_x = region.center_x * scale
        center_y = region.center_y * scale
        polygon = []
        for longitudinal, transverse in (
            (-half_length, -half_height),
            (half_length, -half_height),
            (half_length, half_height),
            (-half_length, half_height),
        ):
            polygon.append(
                (
                    center_x + cosine * longitudinal - sine * transverse,
                    center_y + sine * longitudinal + cosine * transverse,
                )
            )
        cv2.fillConvexPoly(
            mask,
            np.rint(polygon).astype(np.int32),
            255,
        )
    return mask


def _rescale_keypoints(
    keypoints: Sequence[cv2.KeyPoint],
    scale: float,
) -> list[cv2.KeyPoint]:
    if math.isclose(scale, 1.0):
        return list(keypoints)
    return [
        cv2.KeyPoint(
            item.pt[0] / scale,
            item.pt[1] / scale,
            item.size / scale,
            item.angle,
            item.response,
            item.octave,
            item.class_id,
        )
        for item in keypoints
    ]


def _template_match_candidates(
    reference: np.ndarray,
    deformed: np.ndarray,
    region: RigidRegion,
) -> tuple[tuple[float, float, float], ...]:
    half_width = max(int(round(region.length / 2.0)), 2)
    half_height = max(int(round(region.height / 2.0)), 2)
    center_x = int(round(region.center_x))
    center_y = int(round(region.center_y))
    x0 = max(center_x - half_width, 0)
    x1 = min(center_x + half_width, reference.shape[1])
    y0 = max(center_y - half_height, 0)
    y1 = min(center_y + half_height, reference.shape[0])
    template = reference[y0:y1, x0:x1]
    if template.shape[0] < 8 or template.shape[1] < 8:
        return ()

    matches: list[tuple[float, float, float]] = []
    for scale in NORMALIZED_TEMPLATE_SCALES:
        scaled_width = max(int(round(template.shape[1] * scale)), 8)
        scaled_height = max(int(round(template.shape[0] * scale)), 8)
        if (
            scaled_width >= deformed.shape[1]
            or scaled_height >= deformed.shape[0]
        ):
            continue
        scaled = cv2.resize(
            template,
            (scaled_width, scaled_height),
            interpolation=(cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC),
        )
        response = cv2.matchTemplate(
            deformed,
            scaled,
            cv2.TM_CCOEFF_NORMED,
        )
        suppression_x = max(scaled_width // 3, 4)
        suppression_y = max(scaled_height // 3, 4)
        for _ in range(NORMALIZED_TEMPLATE_TOP_MATCHES):
            _, score, _, location = cv2.minMaxLoc(response)
            if not math.isfinite(score) or score < NORMALIZED_TEMPLATE_MIN_SCORE:
                break
            match_x = float(location[0]) + scaled_width / 2.0
            match_y = float(location[1]) + scaled_height / 2.0
            matches.append((match_x, match_y, float(score)))
            left = max(location[0] - suppression_x, 0)
            right = min(location[0] + suppression_x + 1, response.shape[1])
            top = max(location[1] - suppression_y, 0)
            bottom = min(location[1] + suppression_y + 1, response.shape[0])
            response[top:bottom, left:right] = -1.0
    matches.sort(key=lambda item: item[2], reverse=True)
    return tuple(matches[:NORMALIZED_TEMPLATE_TOP_MATCHES])


def _automatic_deformed_region_from_gradients(
    reference: np.ndarray,
    deformed: np.ndarray,
    reference_regions: Sequence[RigidRegion],
) -> RigidRegion | None:
    if len(reference_regions) != POINT_ANCHOR_COUNT:
        return None
    reference_gradient = _structural_gradient_image(reference)
    deformed_gradient = _structural_gradient_image(deformed)
    candidates = [
        _template_match_candidates(
            reference_gradient,
            deformed_gradient,
            region,
        )
        for region in reference_regions
    ]
    if any(not values for values in candidates):
        return None

    reference_points = np.float32(
        [[region.center_x, region.center_y] for region in reference_regions]
    ).reshape(-1, 1, 2)
    diagonal = math.hypot(deformed.shape[1], deformed.shape[0])
    maximum_residual = diagonal * NORMALIZED_TEMPLATE_MAX_RESIDUAL_DIAGONAL
    best: tuple[float, np.ndarray, np.ndarray] | None = None
    for first in candidates[0]:
        for second in candidates[1]:
            for third in candidates[2]:
                deformed_points = np.float32(
                    [first[:2], second[:2], third[:2]]
                ).reshape(-1, 1, 2)
                matrix, _ = cv2.estimateAffinePartial2D(
                    reference_points,
                    deformed_points,
                    method=cv2.LMEDS,
                )
                if matrix is None:
                    continue
                forward_scale = math.hypot(
                    float(matrix[0, 0]),
                    float(matrix[1, 0]),
                )
                if forward_scale <= 0.0:
                    continue
                inverse_scale = 1.0 / forward_scale
                rotation = abs(
                    math.degrees(
                        math.atan2(float(matrix[1, 0]), float(matrix[0, 0]))
                    )
                )
                predicted = cv2.transform(reference_points, matrix)
                residual = float(
                    np.sqrt(np.mean((predicted - deformed_points) ** 2))
                )
                if (
                    not MIN_PLAUSIBLE_SCALE
                    <= inverse_scale
                    <= MAX_PLAUSIBLE_SCALE
                    or rotation > MAX_PLAUSIBLE_ROTATION_DEG
                    or residual > maximum_residual
                ):
                    continue
                correlation = (first[2] + second[2] + third[2]) / 3.0
                score = correlation - residual / max(maximum_residual, 1.0)
                if best is None or score > best[0]:
                    best = (score, deformed_points.reshape(-1, 2), matrix)
    if best is None:
        return None

    points = best[1]
    center_x = float(np.mean(points[:, 0]))
    center_y = float(np.mean(points[:, 1]))
    span_x = float(np.ptp(points[:, 0]))
    span_y = float(np.ptp(points[:, 1]))
    width = float(deformed.shape[1])
    height = float(deformed.shape[0])
    length = max(width * REGION_DEFAULT_LENGTH_FRACTION, span_x + width * 0.16)
    region_height = max(
        height * DEFORMED_REGION_MIN_HEIGHT_FRACTION,
        span_y + height * 2.0 * DEFORMED_REGION_VERTICAL_MARGIN_FRACTION,
    )
    angle = math.degrees(
        math.atan2(float(best[2][1, 0]), float(best[2][0, 0]))
    )
    return RigidRegion(
        center_x=center_x,
        center_y=center_y,
        length=min(length, width * REGION_MAX_LENGTH_FRACTION),
        height=region_height,
        angle_deg=angle,
        directional=True,
    )


def _candidate_from_matrix(
    matrix: np.ndarray,
    src_points: np.ndarray,
    dst_points: np.ndarray,
    weights: np.ndarray,
    segment_indices: np.ndarray,
    anchor_indices: np.ndarray,
    anchor_count: int,
    inlier_mask: np.ndarray,
    available_matches: int,
) -> RigidAlignmentCandidate:
    mask = inlier_mask.ravel().astype(bool)
    predicted = cv2.transform(src_points[mask], matrix).reshape(-1, 2)
    destinations = dst_points[mask].reshape(-1, 2)
    residuals = np.linalg.norm(predicted - destinations, axis=1)
    inlier_weights = np.maximum(weights[mask], 1.0e-9)
    rmse = float(np.sqrt(np.mean(residuals * residuals)))
    weighted_rmse = float(
        np.sqrt(np.sum(inlier_weights * residuals * residuals) / np.sum(inlier_weights))
    )
    a = float(matrix[0, 0])
    c = float(matrix[1, 0])
    scale = math.hypot(a, c)
    rotation_deg = math.degrees(math.atan2(c, a))
    inliers = int(np.count_nonzero(mask))
    mean_weight = float(np.mean(inlier_weights))
    spatial_segments = len(set(int(value) for value in segment_indices[mask]))
    anchor_matches = tuple(
        int(value)
        for value in np.bincount(anchor_indices, minlength=anchor_count)
    )
    anchor_inliers = tuple(
        int(value)
        for value in np.bincount(anchor_indices[mask], minlength=anchor_count)
    )
    score = inliers * mean_weight / (1.0 + weighted_rmse)
    return RigidAlignmentCandidate(
        dx=float(matrix[0, 2]),
        dy=float(matrix[1, 2]),
        rotation_deg=rotation_deg,
        scale=scale,
        inliers=inliers,
        inlier_ratio=inliers / max(available_matches, 1),
        rmse_px=rmse,
        weighted_rmse_px=weighted_rmse,
        mean_region_weight=mean_weight,
        score=score,
        spatial_segments=spatial_segments,
        anchor_matches=anchor_matches,
        anchor_inliers=anchor_inliers,
    )


def _different_motion(
    first: RigidAlignmentCandidate,
    second: RigidAlignmentCandidate,
) -> bool:
    return (
        math.hypot(first.dx - second.dx, first.dy - second.dy)
        >= AMBIGUOUS_TRANSLATION_PX
        or abs(first.rotation_deg - second.rotation_deg)
        >= AMBIGUOUS_ROTATION_DEG
        or abs(first.scale - second.scale) >= AMBIGUOUS_SCALE_DELTA
    )


def _spatial_match_groups(
    points: np.ndarray,
    image_width: int,
    image_height: int,
) -> tuple[np.ndarray, ...]:
    """Return global and local match groups without assigning semantic meaning."""
    flat = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    all_indices = np.arange(len(flat), dtype=np.int32)
    groups: list[np.ndarray] = [all_indices]
    seen = {tuple(int(index) for index in all_indices)}
    half_width = max(float(image_width) * SPATIAL_GROUP_HALF_WIDTH_FRACTION, 1.0)
    half_height = max(
        float(image_height) * SPATIAL_GROUP_HALF_HEIGHT_FRACTION,
        1.0,
    )
    local_groups: list[np.ndarray] = []
    for center_x, center_y in flat:
        mask = (
            (np.abs(flat[:, 0] - center_x) <= half_width)
            & (np.abs(flat[:, 1] - center_y) <= half_height)
        )
        indices = np.flatnonzero(mask).astype(np.int32)
        if len(indices) < MIN_MODEL_MATCHES:
            continue
        key = tuple(int(index) for index in indices)
        if key in seen:
            continue
        seen.add(key)
        local_groups.append(indices)
    local_groups.sort(key=len, reverse=True)
    groups.extend(local_groups[:MAX_SPATIAL_GROUPS])
    return tuple(groups)


def _structural_motion_groups(
    src_points: np.ndarray,
    dst_points: np.ndarray,
    image_diagonal: float,
) -> tuple[np.ndarray, ...]:
    """Cluster gradient matches by coarse displacement before similarity fitting."""
    src_flat = np.asarray(src_points, dtype=np.float64).reshape(-1, 2)
    dst_flat = np.asarray(dst_points, dtype=np.float64).reshape(-1, 2)
    displacements = dst_flat - src_flat
    radius = max(
        float(image_diagonal) * STRUCTURAL_DISPLACEMENT_RADIUS_DIAGONAL,
        4.0,
    )
    groups: list[np.ndarray] = []
    seen: set[tuple[int, ...]] = set()
    for center in displacements:
        distances = np.linalg.norm(displacements - center, axis=1)
        indices = np.flatnonzero(distances <= radius).astype(np.int32)
        if len(indices) < MIN_MODEL_MATCHES:
            continue
        key = tuple(int(index) for index in indices)
        if key in seen:
            continue
        seen.add(key)
        groups.append(indices)
    groups.sort(key=len, reverse=True)
    return tuple(groups[:STRUCTURAL_MAX_MOTION_GROUPS])


def _merge_candidate(
    candidates: list[RigidAlignmentCandidate],
    candidate: RigidAlignmentCandidate,
) -> None:
    for index, current in enumerate(candidates):
        if not _different_motion(current, candidate):
            if candidate.score > current.score:
                candidates[index] = candidate
            return
    candidates.append(candidate)


def _has_relevant_ambiguity(
    candidates: list[RigidAlignmentCandidate],
) -> bool:
    if len(candidates) < 2:
        return False
    best, alternative = candidates[:2]
    return (
        alternative.score >= best.score * AMBIGUOUS_SCORE_RATIO
        and alternative.inliers
        >= math.ceil(best.inliers * AMBIGUOUS_MIN_INLIER_FRACTION)
        and _different_motion(best, alternative)
    )


def _candidate_passes_minimums(
    candidate: RigidAlignmentCandidate,
    image_diagonal: float,
    *,
    has_second_region: bool,
    uses_point_anchors: bool = False,
    structural_fallback: bool = False,
) -> bool:
    minimum_inlier_ratio = (
        MIN_ACCEPTABLE_INLIER_RATIO_WITH_SECOND_REGION
        if has_second_region
        else MIN_ACCEPTABLE_INLIER_RATIO
    )
    minimum_segments = (
        MIN_INLIER_SPATIAL_SEGMENTS_WITH_SECOND_REGION
        if has_second_region
        else MIN_INLIER_SPATIAL_SEGMENTS
    )
    anchor_support = True
    if uses_point_anchors:
        minimum_match_anchors = (
            STRUCTURAL_MIN_MATCH_CONTRIBUTING_ANCHORS
            if structural_fallback
            else MIN_MATCH_CONTRIBUTING_ANCHORS
        )
        match_anchors = sum(
            value >= MIN_MATCHES_PER_CONTRIBUTING_ANCHOR
            for value in candidate.anchor_matches
        )
        inlier_anchors = sum(
            value >= MIN_INLIERS_PER_CONTRIBUTING_ANCHOR
            for value in candidate.anchor_inliers
        )
        anchor_support = (
            match_anchors >= minimum_match_anchors
            and inlier_anchors >= MIN_INLIER_CONTRIBUTING_ANCHORS
        )
    return (
        candidate.inliers >= MIN_MODEL_INLIERS
        and candidate.inlier_ratio >= minimum_inlier_ratio
        and candidate.rmse_px <= MAX_ACCEPTABLE_RMSE_PX
        and (
            anchor_support
            if uses_point_anchors
            else candidate.spatial_segments >= minimum_segments
        )
        and MIN_PLAUSIBLE_SCALE <= candidate.scale <= MAX_PLAUSIBLE_SCALE
        and abs(candidate.rotation_deg) <= MAX_PLAUSIBLE_ROTATION_DEG
        and math.hypot(candidate.dx, candidate.dy)
        / max(image_diagonal, 1.0)
        <= MAX_PLAUSIBLE_TRANSLATION_DIAGONAL
    )


def estimate_rigid_region_alignment(
    reference_path: str | Path,
    deformed_path: str | Path,
    reference_region: RigidRegion | Sequence[RigidRegion],
    *,
    deformed_region: RigidRegion | None = None,
    reference_transform: Mapping[str, float] | None = None,
    deformed_transform: Mapping[str, float] | None = None,
    expansion_attempted: bool = False,
    structural_fallback: bool = False,
    normalized_multiscale: bool = False,
    reference_detection_scale: float = 1.0,
    deformed_detection_scale: float = 1.0,
) -> RigidAlignmentResult:
    if isinstance(reference_region, RigidRegion):
        reference_regions = (reference_region,)
    else:
        reference_regions = tuple(reference_region)
    roi_scale = max(
        (float(region.roi_scale) for region in reference_regions),
        default=1.0,
    )
    reference = _read_grayscale(reference_path)
    deformed = _read_grayscale(deformed_path)
    if structural_fallback:
        reference = _structural_gradient_image(reference)
        deformed = _structural_gradient_image(deformed)
    reference_scale = max(float(reference_detection_scale), 0.1)
    deformed_scale = max(float(deformed_detection_scale), 0.1)
    reference_detection = reference
    deformed_detection = deformed
    if not math.isclose(reference_scale, 1.0):
        reference_detection = cv2.resize(
            reference,
            None,
            fx=reference_scale,
            fy=reference_scale,
            interpolation=cv2.INTER_CUBIC,
        )
    if not math.isclose(deformed_scale, 1.0):
        interpolation = (
            cv2.INTER_AREA if deformed_scale < 1.0 else cv2.INTER_CUBIC
        )
        deformed_detection = cv2.resize(
            deformed,
            None,
            fx=deformed_scale,
            fy=deformed_scale,
            interpolation=interpolation,
        )
    sift = cv2.SIFT_create(nfeatures=SIFT_MAX_FEATURES)
    reference_mask = None
    if normalized_multiscale:
        reference_mask = _region_detection_mask(
            reference_detection.shape,
            reference_regions,
            reference_scale,
        )
    ref_keypoints, ref_descriptors = sift.detectAndCompute(
        reference_detection,
        reference_mask,
    )
    dam_keypoints, dam_descriptors = sift.detectAndCompute(
        deformed_detection,
        None,
    )
    ref_keypoints = _rescale_keypoints(ref_keypoints, reference_scale)
    dam_keypoints = _rescale_keypoints(dam_keypoints, deformed_scale)
    ref_count = len(ref_keypoints)
    dam_count = len(dam_keypoints)
    empty = RigidAlignmentDiagnostics(
        ref_count,
        dam_count,
        0,
        0,
        (),
        (),
        roi_scale,
        expansion_attempted or roi_scale > 1.0,
        structural_fallback,
        normalized_multiscale,
        (reference_scale, deformed_scale),
    )
    if ref_descriptors is None or dam_descriptors is None:
        return RigidAlignmentResult("failure", "insufficient_features", empty, ())

    if not reference_regions:
        return RigidAlignmentResult("failure", "missing_reference_regions", empty, ())
    uses_point_anchors = len(reference_regions) > 1

    raw_ref_points = np.float64([item.pt for item in ref_keypoints])
    raw_dam_points = np.float64([item.pt for item in dam_keypoints])
    anchor_weight_matrix = np.vstack(
        [region_weights(raw_ref_points, region) for region in reference_regions]
    )
    ref_anchor_ids = np.argmax(anchor_weight_matrix, axis=0).astype(np.int32)
    ref_weights = np.max(anchor_weight_matrix, axis=0)
    ref_indices = np.flatnonzero(ref_weights >= REGION_MIN_MATCH_WEIGHT)
    anchor_keypoints = tuple(
        int(value)
        for value in np.bincount(
            ref_anchor_ids[ref_indices], minlength=len(reference_regions)
        )
    )
    if len(ref_indices) < MIN_REGION_KEYPOINTS:
        diagnostics = RigidAlignmentDiagnostics(
            ref_count,
            dam_count,
            int(len(ref_indices)),
            0,
            anchor_keypoints,
            (),
            roi_scale,
            expansion_attempted or roi_scale > 1.0,
            structural_fallback,
            normalized_multiscale,
            (reference_scale, deformed_scale),
        )
        return RigidAlignmentResult(
            "needs_second_region" if deformed_region is None else "failure",
            "insufficient_region_features",
            diagnostics,
            (),
        )

    if deformed_region is None:
        dam_indices = np.arange(dam_count, dtype=np.int32)
        dam_weights = np.ones(dam_count, dtype=np.float64)
    else:
        all_dam_weights = region_weights(raw_dam_points, deformed_region)
        dam_indices = np.flatnonzero(all_dam_weights >= REGION_MIN_MATCH_WEIGHT)
        dam_weights = all_dam_weights
        if len(dam_indices) < MIN_REGION_KEYPOINTS:
            diagnostics = RigidAlignmentDiagnostics(
                ref_count,
                dam_count,
                int(len(ref_indices)),
                0,
                anchor_keypoints,
                (),
                roi_scale,
                expansion_attempted or roi_scale > 1.0,
                structural_fallback,
                normalized_multiscale,
                (reference_scale, deformed_scale),
            )
            return RigidAlignmentResult(
                "failure", "insufficient_deformed_region_features", diagnostics, ()
            )

    ref_desc = ref_descriptors[ref_indices]
    dam_desc = dam_descriptors[dam_indices]
    if deformed_region is not None:
        ratio_threshold = SECOND_REGION_RATIO_TEST_THRESHOLD
    elif normalized_multiscale:
        ratio_threshold = NORMALIZED_RATIO_TEST_THRESHOLD
    else:
        ratio_threshold = RATIO_TEST_THRESHOLD
    matcher = cv2.BFMatcher(cv2.NORM_L2)
    forward_pairs = matcher.knnMatch(ref_desc, dam_desc, k=2)
    reverse_pairs = matcher.knnMatch(dam_desc, ref_desc, k=2)
    forward = {
        best.queryIdx: (best, best.distance / max(second.distance, 1.0e-9))
        for pair in forward_pairs
        if len(pair) == 2
        for best, second in [pair]
        if best.distance < ratio_threshold * second.distance
    }
    reverse = {
        best.queryIdx: best
        for pair in reverse_pairs
        if len(pair) == 2
        for best, second in [pair]
        if best.distance < ratio_threshold * second.distance
    }
    mutual_queries = {
        query_index
        for query_index, (match, _) in forward.items()
        if match.trainIdx in reverse
        and reverse[match.trainIdx].trainIdx == match.queryIdx
    }
    if deformed_region is not None or structural_fallback:
        accepted_pairs = [
            pair
            for query_index, pair in forward.items()
            if query_index in mutual_queries
        ]
    else:
        accepted_by_destination: dict[int, tuple[cv2.DMatch, float]] = {}
        for match, ratio in forward.values():
            current = accepted_by_destination.get(match.trainIdx)
            if current is None or ratio < current[1]:
                accepted_by_destination[match.trainIdx] = (match, ratio)
        accepted_pairs = list(accepted_by_destination.values())
    accepted_pairs.sort(
        key=lambda item: (item[0].queryIdx not in mutual_queries, item[1])
    )
    accepted = [item[0] for item in accepted_pairs]
    accepted_ref_indices = np.array(
        [ref_indices[item.queryIdx] for item in accepted], dtype=np.int32
    )
    accepted_anchor_ids = ref_anchor_ids[accepted_ref_indices]
    anchor_matches = tuple(
        int(value)
        for value in np.bincount(
            accepted_anchor_ids, minlength=len(reference_regions)
        )
    )
    diagnostics = RigidAlignmentDiagnostics(
        ref_count,
        dam_count,
        int(len(ref_indices)),
        int(len(accepted)),
        anchor_keypoints,
        anchor_matches,
        roi_scale,
        expansion_attempted or roi_scale > 1.0,
        structural_fallback,
        normalized_multiscale,
        (reference_scale, deformed_scale),
    )
    if len(accepted) < MIN_ACCEPTED_MATCHES:
        return RigidAlignmentResult(
            "needs_second_region" if deformed_region is None else "failure",
            "insufficient_matches",
            diagnostics,
            (),
        )

    accepted_dam_indices = np.array(
        [dam_indices[item.trainIdx] for item in accepted], dtype=np.int32
    )
    segment_indices = _region_segment_indices(
        raw_ref_points[accepted_ref_indices],
        reference_regions[0],
    )
    if uses_point_anchors:
        segment_indices = accepted_anchor_ids.copy()
    mutual_weights = np.array(
        [
            1.0 if item.queryIdx in mutual_queries else NON_MUTUAL_MATCH_WEIGHT
            for item in accepted
        ],
        dtype=np.float64,
    )
    weights = (
        ref_weights[accepted_ref_indices]
        * dam_weights[accepted_dam_indices]
        * mutual_weights
    )
    ref_height, ref_width = reference.shape
    dam_height, dam_width = deformed.shape
    dst = _apply_visual_transform(
        raw_ref_points[accepted_ref_indices],
        ref_width,
        ref_height,
        reference_transform,
    ).astype(np.float32).reshape(-1, 1, 2)
    src = _apply_visual_transform(
        raw_dam_points[accepted_dam_indices],
        dam_width,
        dam_height,
        deformed_transform,
    ).astype(np.float32).reshape(-1, 1, 2)

    candidates: list[RigidAlignmentCandidate] = []
    ransac_threshold = (
        SECOND_REGION_RANSAC_REPROJECTION_THRESHOLD_PX
        if deformed_region is not None
        else RANSAC_REPROJECTION_THRESHOLD_PX
    )
    cv2.setRNGSeed(RANSAC_RANDOM_SEED)
    if structural_fallback or normalized_multiscale:
        groups = _structural_motion_groups(
            src,
            dst,
            math.hypot(dam_width, dam_height),
        )
    else:
        groups = _spatial_match_groups(
            raw_dam_points[accepted_dam_indices],
            dam_width,
            dam_height,
        )
    for group in groups:
        if len(group) < MIN_MODEL_MATCHES:
            continue
        matrix, mask = cv2.estimateAffinePartial2D(
            src[group],
            dst[group],
            method=cv2.RANSAC,
            ransacReprojThreshold=ransac_threshold,
            maxIters=RANSAC_MAX_ITERATIONS,
            confidence=RANSAC_CONFIDENCE,
            refineIters=10,
        )
        if matrix is None or mask is None:
            break
        local_mask = mask.ravel().astype(bool)
        if int(np.count_nonzero(local_mask)) < MIN_MODEL_INLIERS:
            break
        candidate = _candidate_from_matrix(
            matrix,
            src[group],
            dst[group],
            weights[group],
            segment_indices[group],
            accepted_anchor_ids[group],
            len(reference_regions),
            mask,
            len(group),
        )
        _merge_candidate(candidates, candidate)

    candidates.sort(key=lambda item: item.score, reverse=True)
    candidates = candidates[:MAX_CANDIDATES]
    if not candidates:
        return RigidAlignmentResult(
            "needs_second_region" if deformed_region is None else "failure",
            "estimation_failed",
            diagnostics,
            (),
        )

    diagonal = math.hypot(ref_width, ref_height)
    viable = [
        candidate
        for candidate in candidates
        if _candidate_passes_minimums(
            candidate,
            diagonal,
            has_second_region=deformed_region is not None,
            uses_point_anchors=uses_point_anchors,
            structural_fallback=structural_fallback,
        )
    ]
    if not viable:
        return RigidAlignmentResult(
            "needs_second_region" if deformed_region is None else "failure",
            "weak_solution",
            diagnostics,
            tuple(candidates),
        )
    if _has_relevant_ambiguity(viable):
        return RigidAlignmentResult(
            "needs_second_region" if deformed_region is None else "failure",
            "ambiguous_solution",
            diagnostics,
            tuple(viable),
        )
    return RigidAlignmentResult(
        "success", "ok", diagnostics, tuple(viable)
    )


def estimate_multiscale_rigid_alignment(
    reference_path: str | Path,
    deformed_path: str | Path,
    reference_regions: Sequence[RigidRegion],
    *,
    reference_transform: Mapping[str, float] | None = None,
    deformed_transform: Mapping[str, float] | None = None,
) -> RigidAlignmentResult:
    """Retry reference-anchor matching with normalized ROI/pyramid detection."""
    attempts: list[RigidAlignmentResult] = []
    for reference_scale in NORMALIZED_REFERENCE_SCALES:
        for deformed_scale in NORMALIZED_DEFORMED_SCALES:
            attempts.append(
                estimate_rigid_region_alignment(
                    reference_path,
                    deformed_path,
                    reference_regions,
                    reference_transform=reference_transform,
                    deformed_transform=deformed_transform,
                    expansion_attempted=True,
                    normalized_multiscale=True,
                    reference_detection_scale=reference_scale,
                    deformed_detection_scale=deformed_scale,
                )
            )

    successful = [
        result
        for result in attempts
        if result.status == "success" and result.best is not None
    ]
    if successful:
        return max(
            successful,
            key=lambda result: (
                result.best.inliers,  # type: ignore[union-attr]
                result.best.inlier_ratio,  # type: ignore[union-attr]
                -result.best.rmse_px,  # type: ignore[union-attr]
            ),
        )
    automatic_region = _automatic_deformed_region_from_gradients(
        _read_grayscale(reference_path),
        _read_grayscale(deformed_path),
        reference_regions,
    )
    if automatic_region is not None:
        assisted = estimate_rigid_region_alignment(
            reference_path,
            deformed_path,
            reference_regions,
            deformed_region=automatic_region,
            reference_transform=reference_transform,
            deformed_transform=deformed_transform,
            expansion_attempted=True,
        )
        assisted = replace(
            assisted,
            diagnostics=replace(
                assisted.diagnostics,
                normalized_multiscale=True,
            ),
        )
        attempts.append(assisted)
        if assisted.status == "success":
            return assisted
    best_failure = max(
        attempts,
        key=lambda result: (
            result.diagnostics.accepted_matches,
            result.best.inliers if result.best is not None else 0,
            result.best.score if result.best is not None else 0.0,
        ),
    )
    if best_failure.status == "failure":
        return replace(best_failure, status="needs_second_region")
    return best_failure
