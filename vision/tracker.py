from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
import torch
import torch.nn as nn
import torchvision.transforms as T
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small
from ultralytics import YOLO

import config


# מחשבת IoU (חפיפה בין מלבנים) — מודדת עד כמה שני bounding box חופפים (0=אין, 1=זהים)
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


# מגבילה bounding box לגבולות התמונה ומוודאת שהוא תקין
def _clamp_box(
    bbox: Tuple[int, int, int, int], w: int, h: int
) -> Tuple[int, int, int, int]:
    x1, y1, x2, y2 = bbox
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w - 1, x2), min(h - 1, y2)
    if x2 <= x1 or y2 <= y1:
        return 0, 0, max(1, w - 1), max(1, h - 1)
    return x1, y1, x2, y2


# ממירה טנסור PyTorch למערך NumPy
def _to_numpy(x) -> np.ndarray:
    if hasattr(x, "cpu"):
        return x.cpu().numpy()
    return np.asarray(x)


# מוצאת את תיקיית מודל OpenVINO שנוצרה מ-YOLO
def _openvino_dir(weights: Path) -> Path:
    direct = weights.parent / f"{weights.stem}_openvino_model"
    if direct.is_dir():
        return direct
    for p in weights.parent.glob(f"{weights.stem}*_openvino_model"):
        if p.is_dir():
            return p
    return direct


# טוענת את מודל YOLO — PyTorch רגיל או OpenVINO לפי הגדרת DEVICE
def _load_yolo(infer_device: str) -> YOLO:
    weights = Path(config.YOLO_WEIGHTS)
    if not infer_device.startswith("intel:"):
        model = YOLO(str(weights))
        if infer_device != "cpu":
            model.to(infer_device)
        return model
    ov_dir = _openvino_dir(weights)
    if not ov_dir.is_dir():
        print("Exporting YOLO to OpenVINO (one-time)...")
        YOLO(str(weights)).export(format="openvino")
        ov_dir = _openvino_dir(weights)
    if not ov_dir.is_dir():
        raise RuntimeError("OpenVINO export failed — try DEVICE = 'cpu'")
    return YOLO(str(ov_dir))


# רשת MobileNet לחילוץ וקטור ייחוד (ReID) מתוך חיתוך תמונה
class _ReIDBackbone(nn.Module):
    # מאתחלת את MobileNet V3 Small עם משקולות ImageNet
    def __init__(self) -> None:
        super().__init__()
        m = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
        self.feat = m.features
        self.pool = m.avgpool

    # מעבירה תמונה דרך הרשת ומחזירה וקטור תכונה שטוח
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.feat(x)
        x = self.pool(x)
        return torch.flatten(x, 1)


# עוקב אחרי מטרה: זיהוי YOLO, מעקב ByteTrack, ReID לשחזור, ו-SAM אופציונלי למרכז
class SentryTracker:
    # טוען מודלים (YOLO, ReID, SAM) ומאתחל מצב מעקב
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
            try:
                from ultralytics import SAM

                sm = SAM(config.SAM_WEIGHTS)
                if hasattr(sm, "to") and not self._infer_device.startswith("intel:"):
                    sm.to(self._infer_device if self._infer_device != "cpu" else "cpu")
                self.sam_model = sm
            except Exception:
                self.sam_model = None
        self._track_id: Optional[int] = None
        self._pick_track = True
        self._last_bbox: Optional[Tuple[int, int, int, int]] = None

    # קובעת מכשיר inference (CUDA, CPU או Intel OpenVINO) לפי config.DEVICE
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

    # מחלצת וקטור ReID מנורמל מתוך אזור bounding box בפריים
    @torch.inference_mode()
    def _embed_crop(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = _clamp_box(bbox, w, h)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return np.zeros((config.REID_EMBED_SIZE,), dtype=np.float32)
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        pil = T.functional.to_pil_image(rgb)
        t = self._reid_tf(pil).unsqueeze(0).to(self._device)
        e = self.reid_model(t)
        e = torch.nn.functional.normalize(e, dim=1)
        return e.squeeze(0).detach().cpu().numpy().astype(np.float32)

    # מפעילה SAM על המלבן ומחזירה מסכה + מרכז המטרה (centroid)
    def _sam_centroid_mask(
        self, frame: np.ndarray, bbox: Tuple[int, int, int, int]
    ) -> Tuple[Optional[np.ndarray], Tuple[int, int]]:
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = _clamp_box(bbox, w, h)
        if self.sam_model is None:
            self.current_mask = None
            return None, (int((x1 + x2) * 0.5), int((y1 + y2) * 0.5))
        try:
            r = self.sam_model.predict(
                source=frame,
                bboxes=[[float(x1), float(y1), float(x2), float(y2)]],
                verbose=False,
                device=self._infer_device,
            )
            if not r or r[0].masks is None:
                self.current_mask = None
                return None, (int((x1 + x2) * 0.5), int((y1 + y2) * 0.5))
            mdata = r[0].masks.data
            if mdata is None or mdata.shape[0] == 0:
                self.current_mask = None
                return None, (int((x1 + x2) * 0.5), int((y1 + y2) * 0.5))
            m0 = mdata[0]
            mf = (m0.float().sigmoid().cpu().numpy() > 0.5)
            if mf.ndim == 3:
                mf = mf[0]
            if mf.shape[0] != h or mf.shape[1] != w:
                mf = cv2.resize(mf.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0
            else:
                mf = mf > 0
            ys, xs = np.where(mf)
            if len(xs) == 0:
                self.current_mask = None
                return None, (int((x1 + x2) * 0.5), int((y1 + y2) * 0.5))
            cx, cy = int(np.round(xs.mean())), int(np.round(ys.mean()))
            cx = max(0, min(w - 1, cx))
            cy = max(0, min(h - 1, cy))
            self.current_mask = (mf.astype(np.uint8) * 255)
            return self.current_mask, (cx, cy)
        except Exception:
            self.current_mask = None
            return None, (int((x1 + x2) * 0.5), int((y1 + y2) * 0.5))

    # נועלת מטרה: שומרת embedding ומעבר למצב LOCKED
    def set_target(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> None:
        self.last_frame = frame.copy()
        h, w = frame.shape[:2]
        bb = _clamp_box(bbox, w, h)
        self.target_embedding = self._embed_crop(frame, bb)
        self.status = "LOCKED"
        self._track_id = None
        self._pick_track = True
        self._last_bbox = bb

    # בוחרת מטרה לפי לחיצת עכבר — אם הנקודה בתוך מלבן מזוהה
    def set_target_from_click(self, frame: np.ndarray, x: int, y: int) -> bool:
        for box in self.last_boxes:
            x1, y1, x2, y2 = box
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.set_target(frame, box)
                return True
        return False

    # מחלצת רשימת bounding boxes ו-track IDs מתוצאת YOLO
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
            x1, y1, x2, y2 = [int(round(v)) for v in row]
            out.append((x1, y1, x2, y2))
        return out, ids

    # מעדכנת מעקב בפריים: SEARCHING / LOCKED / LOST — מחזירה מרכז מטרה או None
    @torch.inference_mode()
    def update(self, frame: np.ndarray) -> Optional[Tuple[int, int]]:
        self.last_frame = frame.copy()
        self.current_mask = None
        h, w = frame.shape[:2]
        if self.status == "SEARCHING":
            r = self.yolo_model.predict(
                source=frame,
                conf=config.YOLO_CONF,
                verbose=False,
                device=self._infer_device,
            )[0]
            self.last_boxes, _ = self._boxes_from_result(r)
            return None
        if self.status == "LOCKED":
            r = self.yolo_model.track(
                source=frame,
                conf=config.YOLO_CONF,
                persist=True,
                tracker=config.YOLO_TRACKER,
                verbose=False,
                device=self._infer_device,
            )[0]
            self.last_boxes, ids = self._boxes_from_result(r)
            if not self.last_boxes or ids is None or len(ids) != len(self.last_boxes):
                self.status = "LOST"
                self._track_id = None
                self._pick_track = True
                return None
            if self._pick_track and self._last_bbox is not None:
                best_i, best_iou = -1, 0.0
                for i, b in enumerate(self.last_boxes):
                    v = _iou(self._last_bbox, b)
                    if v > best_iou:
                        best_iou, best_i = v, i
                if best_i >= 0 and best_iou >= config.YOLO_IOU_MATCH:
                    self._track_id = int(ids[best_i])
                    self._pick_track = False
                else:
                    self.status = "LOST"
                    self._track_id = None
                    self._pick_track = True
                    return None
            if self._track_id is None:
                self.status = "LOST"
                return None
            idx = next((i for i, tid in enumerate(ids) if int(tid) == self._track_id), -1)
            if idx < 0:
                self.status = "LOST"
                self._track_id = None
                self._pick_track = True
                return None
            bb = self.last_boxes[idx]
            self._last_bbox = bb
            _, center = self._sam_centroid_mask(frame, bb)
            return center
        if self.status == "LOST":
            if self.target_embedding is None:
                self.status = "SEARCHING"
                return None
            r = self.yolo_model.predict(
                source=frame,
                conf=config.YOLO_CONF,
                verbose=False,
                device=self._infer_device,
            )[0]
            self.last_boxes, _ = self._boxes_from_result(r)
            te = self.target_embedding
            best_box: Optional[Tuple[int, int, int, int]] = None
            best_sim = config.REID_SIM_THRESHOLD
            for bb in self.last_boxes:
                emb = self._embed_crop(frame, bb)
                sim = float(np.dot(te, emb))
                if sim >= best_sim:
                    best_sim, best_box = sim, bb
            if best_box is None:
                return None
            self.status = "LOCKED"
            self._last_bbox = best_box
            self._track_id = None
            self._pick_track = True
            _, center = self._sam_centroid_mask(frame, best_box)
            return center
        return None
