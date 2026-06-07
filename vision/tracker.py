from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
import torch
import torch.nn as nn
import torchvision.transforms as T
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small
from ultralytics import SAM, YOLO

import config


def _iou(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    aa = max(1, (ax2 - ax1) * (ay2 - ay1))
    ba = max(1, (bx2 - bx1) * (by2 - by1))
    return inter / float(aa + ba - inter)


def _clamp_box(bbox: Tuple[int, int, int, int], w: int, h: int) -> Tuple[int, int, int, int]:
    x1, y1, x2, y2 = bbox
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w - 1, x2), min(h - 1, y2)
    if x2 <= x1 or y2 <= y1:
        return 0, 0, max(1, w - 1), max(1, h - 1)
    return x1, y1, x2, y2


def _to_numpy(x) -> np.ndarray:
    if hasattr(x, "cpu"):
        return x.cpu().numpy()
    return np.asarray(x)


def _openvino_dir(weights: Path) -> Path:
    direct = weights.parent / f"{weights.stem}_openvino_model"
    if direct.is_dir():
        return direct
    for p in weights.parent.glob(f"{weights.stem}*_openvino_model"):
        if p.is_dir():
            return p
    return direct


def _load_yolo(infer_device: str) -> YOLO:
    weights = Path(config.YOLO_WEIGHTS)
    if not infer_device.startswith("intel:"):
        model = YOLO(str(weights), task="detect")
        if infer_device != "cpu":
            model.to(infer_device)
        return model
    ov_dir = _openvino_dir(weights)
    if not ov_dir.is_dir():
        print("Exporting YOLO to OpenVINO (one-time)...")
        YOLO(str(weights), task="detect").export(format="openvino")
        ov_dir = _openvino_dir(weights)
    if not ov_dir.is_dir():
        raise RuntimeError("OpenVINO export failed — set DEVICE = 'cpu'")
    return YOLO(str(ov_dir), task="detect")


class _ReIDBackbone(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        m = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
        self.feat = m.features
        self.pool = m.avgpool

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.feat(x)
        x = self.pool(x)
        return torch.flatten(x, 1)


class SentryTracker:
    def __init__(self) -> None:
        self.status = "SEARCHING"
        self.target_embedding: Optional[np.ndarray] = None
        self.current_mask: Optional[np.ndarray] = None
        self.last_frame: Optional[np.ndarray] = None
        self.last_boxes: List[Tuple[int, int, int, int]] = []
        self._infer_device, self._device = self._resolve_devices()
        self.yolo_model = _load_yolo(self._infer_device)
        self.reid_model = _ReIDBackbone().to(self._device).eval()
        w = MobileNet_V3_Small_Weights.IMAGENET1K_V1
        self._reid_tf = w.transforms()
        self.sam_model = None
        if config.ENABLE_SAM:
            self.sam_model = SAM(config.SAM_WEIGHTS)
            if self._infer_device == "cuda":
                self.sam_model.to("cuda")
        self._track_id: Optional[int] = None
        self._pick_track = True
        self._last_bbox: Optional[Tuple[int, int, int, int]] = None
        self._embed_gallery: List[np.ndarray] = []
        self._reid_frames = 0
        self._sam_frames = 0
        self._last_center: Optional[Tuple[int, int]] = None
        self._lost_frames = 0
        self._reid_mismatch_frames = 0
        self._aim_reset = False
        imgsz = config.YOLO_IMGSZ
        if self._infer_device.startswith("intel:"):
            imgsz = 640
        self._yolo_kw = {
            "task": "detect",
            "conf": config.YOLO_CONF,
            "classes": config.YOLO_CLASSES,
            "verbose": False,
            "device": self._infer_device,
            "imgsz": imgsz,
        }

    def get_aim_target(self) -> Optional[Tuple[int, int]]:
        if self.status in ("LOCKED", "LOST") and self._last_center is not None:
            return self._last_center
        return None

    def consume_aim_reset(self) -> bool:
        if self._aim_reset:
            self._aim_reset = False
            return True
        return False

    @staticmethod
    def _resolve_devices() -> Tuple[str, torch.device]:
        d = config.DEVICE.strip().lower()
        if d == "cuda":
            if torch.cuda.is_available():
                return "cuda", torch.device("cuda")
            return "cpu", torch.device("cpu")
        if d.startswith("intel:"):
            try:
                import openvino as ov

                ov_devs = ov.Core().available_devices
                want = d.split(":", 1)[1].upper()
                if want == "GPU" and not any("GPU" in x for x in ov_devs):
                    print(f"Intel GPU not found ({ov_devs}), using intel:cpu")
                    return "intel:cpu", torch.device("cpu")
            except Exception:
                return "intel:cpu", torch.device("cpu")
            return config.DEVICE.strip(), torch.device("cpu")
        return "cpu", torch.device("cpu")

    @staticmethod
    def _reid_bbox(bbox: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        x1, y1, x2, y2 = bbox
        bh = max(1, y2 - y1)
        return x1, y1, x2, y1 + max(1, int(bh * config.REID_UPPER_BODY_RATIO))

    @torch.inference_mode()
    def _embed_crop(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = _clamp_box(self._reid_bbox(bbox), w, h)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return np.zeros((config.REID_EMBED_SIZE,), dtype=np.float32)
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        t = self._reid_tf(T.functional.to_pil_image(rgb)).unsqueeze(0).to(self._device)
        e = torch.nn.functional.normalize(self.reid_model(t), dim=1)
        return e.squeeze(0).cpu().numpy().astype(np.float32)

    def _box_center(self, bb: Tuple[int, int, int, int]) -> Tuple[int, int]:
        return (bb[0] + bb[2]) // 2, (bb[1] + bb[3]) // 2

    def _center_dist(self, bb: Tuple[int, int, int, int]) -> float:
        if self._last_center is None:
            return 0.0
        cx, cy = self._box_center(bb)
        dx, dy = cx - self._last_center[0], cy - self._last_center[1]
        return float((dx * dx + dy * dy) ** 0.5)

    def _reacquire_radius(self) -> float:
        return config.REACQUIRE_SPATIAL_BASE_PX + self._lost_frames * config.REACQUIRE_SPATIAL_EXPAND_PX

    def _person_score(self, emb: np.ndarray) -> Tuple[float, float]:
        if self.target_embedding is None or not np.any(emb):
            return 0.0, 0.0
        anchor = float(np.dot(emb, self.target_embedding))
        gallery = anchor
        for e in self._embed_gallery:
            gallery = max(gallery, float(np.dot(emb, e)))
        return anchor, gallery

    def _accept_person(self, anchor: float, gallery: float) -> bool:
        if anchor >= config.REID_REACQUIRE_THRESHOLD:
            return True
        if gallery >= config.REID_REACQUIRE_THRESHOLD and anchor >= config.REID_ANCHOR_MIN_SIM:
            return True
        return False

    def _verify_identity(self, frame: np.ndarray, bb: Tuple[int, int, int, int]) -> bool:
        emb = self._embed_crop(frame, bb)
        anchor, gallery = self._person_score(emb)
        return gallery >= config.REID_LOCK_VERIFY_THRESHOLD and anchor >= config.REID_ANCHOR_MIN_SIM

    def _pick_track_index(
        self,
        frame: np.ndarray,
        boxes: List[Tuple[int, int, int, int]],
        ids: np.ndarray,
    ) -> Optional[int]:
        scored: List[Tuple[int, float, float, float]] = []
        for i, b in enumerate(boxes):
            iou = _iou(self._last_bbox, b) if self._last_bbox else 1.0
            emb = self._embed_crop(frame, b)
            anchor, gallery = self._person_score(emb)
            if gallery < config.REID_LOCK_VERIFY_THRESHOLD:
                continue
            if iou < config.REID_PICK_IOU_MIN and anchor < config.REID_REACQUIRE_THRESHOLD:
                continue
            scored.append((i, gallery + iou * 0.15, anchor, gallery))
        if not scored:
            return None
        scored.sort(key=lambda x: x[1], reverse=True)
        if len(scored) >= 2:
            if scored[0][3] - scored[1][3] < config.REID_MATCH_MARGIN:
                return None
        return int(ids[scored[0][0]])

    def _find_lost_match(
        self, frame: np.ndarray, boxes: List[Tuple[int, int, int, int]]
    ) -> Optional[Tuple[int, int, int, int]]:
        radius = self._reacquire_radius()
        scored: List[Tuple[Tuple[int, int, int, int], float, float]] = []
        for bb in boxes:
            if self._last_center is not None and self._center_dist(bb) > radius:
                continue
            emb = self._embed_crop(frame, bb)
            anchor, gallery = self._person_score(emb)
            if not self._accept_person(anchor, gallery):
                continue
            scored.append((bb, anchor, gallery))
        if not scored:
            return None
        scored.sort(key=lambda x: (x[2], x[1]), reverse=True)
        best_bb, best_a, best_g = scored[0]
        if len(scored) >= 2:
            _, sa, sg = scored[1]
            if best_g - sg < config.REID_MATCH_MARGIN and best_a - sa < config.REID_MATCH_MARGIN:
                return None
        return best_bb

    def _add_to_gallery(self, emb: np.ndarray) -> None:
        if not np.any(emb) or self.target_embedding is None:
            return
        if float(np.dot(emb, self.target_embedding)) < config.REID_GALLERY_MIN_SIM:
            return
        for e in self._embed_gallery:
            if float(np.dot(emb, e)) > 1.0 - config.REID_GALLERY_MIN_DIST:
                return
        self._embed_gallery.append(emb.copy())
        if len(self._embed_gallery) > config.REID_GALLERY_MAX:
            self._embed_gallery.pop(0)

    def _seed_gallery(self, frame: np.ndarray, bb: Tuple[int, int, int, int]) -> None:
        self._embed_gallery.clear()
        if self.target_embedding is not None:
            self._embed_gallery.append(self.target_embedding.copy())

    def _sam_centroid(
        self, frame: np.ndarray, bbox: Tuple[int, int, int, int]
    ) -> Tuple[Optional[np.ndarray], Tuple[int, int]]:
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = _clamp_box(bbox, w, h)
        cx, cy = int((x1 + x2) * 0.5), int((y1 + y2) * 0.5)
        try:
            r = self.sam_model.predict(
                source=frame,
                bboxes=[[float(x1), float(y1), float(x2), float(y2)]],
                verbose=False,
                device=self._infer_device,
            )
            if not r or r[0].masks is None:
                self.current_mask = None
                return None, (cx, cy)
            m0 = r[0].masks.data[0]
            mf = m0.float().sigmoid().cpu().numpy() > 0.5
            if mf.ndim == 3:
                mf = mf[0]
            if mf.shape[0] != h or mf.shape[1] != w:
                mf = cv2.resize(mf.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0
            ys, xs = np.where(mf)
            if len(xs) == 0:
                self.current_mask = None
                return None, (cx, cy)
            cx = max(0, min(w - 1, int(np.round(xs.mean()))))
            cy = max(0, min(h - 1, int(np.round(ys.mean()))))
            self.current_mask = (mf.astype(np.uint8) * 255)
            return self.current_mask, (cx, cy)
        except Exception:
            self.current_mask = None
            return None, (cx, cy)

    def _target_center(
        self, frame: np.ndarray, bbox: Tuple[int, int, int, int]
    ) -> Tuple[Optional[np.ndarray], Tuple[int, int]]:
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = _clamp_box(bbox, w, h)
        cx, cy = int((x1 + x2) * 0.5), int((y1 + y2) * 0.5)
        if self.sam_model is None:
            self.current_mask = None
            return None, (cx, cy)
        self._sam_frames += 1
        if self._sam_frames < config.SAM_INTERVAL:
            return self.current_mask, (cx, cy)
        self._sam_frames = 0
        return self._sam_centroid(frame, bbox)

    def set_target(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> None:
        h, w = frame.shape[:2]
        bb = _clamp_box(bbox, w, h)
        self.target_embedding = self._embed_crop(frame, bb)
        self._seed_gallery(frame, bb)
        self.status = "LOCKED"
        self._track_id = None
        self._pick_track = True
        self._last_bbox = bb
        self._reid_frames = 0
        self._lost_frames = 0
        self._reid_mismatch_frames = 0
        self._last_center = self._box_center(bb)
        self.current_mask = None
        self._aim_reset = True

    def set_target_from_click(self, frame: np.ndarray, x: int, y: int) -> bool:
        for box in self.last_boxes:
            x1, y1, x2, y2 = box
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.set_target(frame, box)
                return True
        return False

    def _boxes_from_result(self, res) -> Tuple[List[Tuple[int, int, int, int]], Optional[np.ndarray]]:
        boxes = res.boxes
        if boxes is None or len(boxes) == 0:
            return [], None
        xyxy = _to_numpy(boxes.xyxy)
        ids = None
        if boxes.id is not None:
            ids = _to_numpy(boxes.id).astype(np.int32)
        out: List[Tuple[int, int, int, int]] = []
        for row in xyxy:
            out.append(tuple(int(round(v)) for v in row))
        return out, ids

    @torch.inference_mode()
    def update(self, frame: np.ndarray) -> Optional[Tuple[int, int]]:
        self.last_frame = frame
        if self.status == "SEARCHING":
            r = self.yolo_model.predict(source=frame, **self._yolo_kw)[0]
            self.last_boxes, _ = self._boxes_from_result(r)
            return None
        if self.status == "LOCKED":
            r = self.yolo_model.track(
                source=frame, persist=True, tracker=config.YOLO_TRACKER, **self._yolo_kw
            )[0]
            self.last_boxes, ids = self._boxes_from_result(r)
            if not self.last_boxes or ids is None:
                self.status = "LOST"
                self._track_id = None
                self._pick_track = True
                self._lost_frames = 0
                return None
            if self._pick_track:
                pick = self._pick_track_index(frame, self.last_boxes, ids)
                if pick is None and self._last_bbox is not None:
                    best_i, best_iou = -1, 0.0
                    for i, b in enumerate(self.last_boxes):
                        v = _iou(self._last_bbox, b)
                        if v > best_iou:
                            best_iou, best_i = v, i
                    if best_i >= 0 and best_iou >= 0.2:
                        pick = int(ids[best_i])
                if pick is None:
                    if self._last_bbox is not None:
                        _, center = self._target_center(frame, self._last_bbox)
                        self._last_center = center
                        return center
                    self.status = "LOST"
                    self._track_id = None
                    self._pick_track = True
                    self._lost_frames = 0
                    self._reid_mismatch_frames = 0
                    return None
                self._track_id = pick
                self._pick_track = False
                self._reid_mismatch_frames = 0
            idx = next((i for i, tid in enumerate(ids) if int(tid) == self._track_id), -1)
            if idx < 0:
                self.status = "LOST"
                self._track_id = None
                self._pick_track = True
                self._lost_frames = 0
                self._reid_mismatch_frames = 0
                return None
            bb = self.last_boxes[idx]
            self._last_bbox = bb
            self._reid_frames += 1
            if self._reid_frames % config.REID_LOCK_VERIFY_INTERVAL == 0:
                if self._verify_identity(frame, bb):
                    self._reid_mismatch_frames = 0
                else:
                    self._reid_mismatch_frames += 1
                if self._reid_mismatch_frames >= config.REID_LOCK_MISMATCH_MAX:
                    self.status = "LOST"
                    self._track_id = None
                    self._pick_track = True
                    self._lost_frames = 0
                    self._reid_mismatch_frames = 0
                    return None
            if self._reid_frames >= config.REID_UPDATE_INTERVAL:
                self._add_to_gallery(self._embed_crop(frame, bb))
                self._reid_frames = 0
            _, center = self._target_center(frame, bb)
            self._last_center = center
            return center
        if self.status == "LOST":
            if self.target_embedding is None:
                self.status = "SEARCHING"
                return None
            self._lost_frames += 1
            r = self.yolo_model.predict(source=frame, **self._yolo_kw)[0]
            self.last_boxes, _ = self._boxes_from_result(r)
            if self._lost_frames % config.LOST_REID_INTERVAL != 0:
                return None
            best_box = self._find_lost_match(frame, self.last_boxes)
            if best_box is None:
                return None
            self.status = "LOCKED"
            self._last_bbox = best_box
            self._track_id = None
            self._pick_track = True
            self._reid_frames = 0
            self._lost_frames = 0
            self._reid_mismatch_frames = 0
            self._add_to_gallery(self._embed_crop(frame, best_box))
            _, center = self._target_center(frame, best_box)
            self._last_center = center
            return center
        return None

    def release_target(self) -> None:
        """Resets the tracking state and returns the tracker to searching mode."""
        self.status = "SEARCHING"
        self.target_embedding = None
        self._track_id = None
        self._pick_track = True
        self._last_bbox = None
        self._last_center = None
        self.current_mask = None
        self._embed_gallery.clear()
        self._lost_frames = 0
        self._reid_mismatch_frames = 0
        self._aim_reset = True
