"""
Vision module for Minecraft AI with multiple detection backends.

This module provides visual perception capabilities by:
1. Capturing screenshots from the bot's first-person viewpoint
2. Using various detectors (YOLO, RT-DETR, VLM) to analyze the image
3. Formatting detection results for LLM context
4. Managing model download and availability

Supported detectors:
- yolo: YOLOv8-based detection (default: Minecraft player detection model)
- rtdetr: RT-DETR object detection
- vlm: Vision Language Model analysis (uses LLM API)
"""

import os
import sys
import io
import json
import shutil
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any, Protocol
from abc import ABC, abstractmethod
from enum import Enum

from utils import add_log, get_datetime_stamp, print_msg
from camera import Camera


# =============================================================================
# Detector Types
# =============================================================================

class DetectorType(Enum):
    """Available detector types."""
    YOLO = "yolo"
    RTDETR = "rtdetr"
    VLM = "vlm"


# =============================================================================
# Model Registry
# =============================================================================

# Default models for each detector type (URLs)
# YOLO uses pretrained YOLOv10 on COCO dataset - LLM translates labels to Minecraft context
DEFAULT_MODELS = {
    DetectorType.YOLO: "yolov10n.pt",  # Pretrained on COCO, ultralytics auto-downloads
    DetectorType.RTDETR: "https://github.com/ultralytics/assets/releases/download/v0.0.0/rtdetr-l.pt",
    DetectorType.VLM: None,  # VLM doesn't need a local model
}

# Local models directory
MODELS_DIR = "models"

# Known model sizes for display purposes (URL patterns -> size in MB)
KNOWN_MODEL_SIZES = {
    "rtdetr-l.pt": 64,
    "rtdetr-x.pt": 130,
    "rtdetr-m.pt": 40,
    "rtdetr-s.pt": 22,
    "best.pt": 15,  # Minecraft YOLOv5 model from CHATDOO
    "minecraft": 15,
    "yolo": 15,
}

# Legacy model sizes (kept for backward compatibility)
MODEL_SIZES = KNOWN_MODEL_SIZES

# Alternative models that users can specify
ALTERNATIVE_MODELS = {
    "minecraft_yolov5_chatdoo": {
        "url": "https://raw.githubusercontent.com/CHATDOO/Minecraft-YOLOv5/main/best.pt",
        "description": "Minecraft mobs & blocks (cow, creeper, pig, villager, sheep, house)",
        "size_mb": 15,
    },
    "minecraft_player_yolov8_styalai": {
        "url": "https://github.com/styalai/player-detection-on-Minecraft-with-YOLOv8/raw/main/player_detection%20on%20minecraft%2004%20(gpu).pt",
        "description": "Minecraft player detection only",
        "size_mb": 6,
    },
    "rtdetr_l": {
        "url": "https://github.com/ultralytics/assets/releases/download/v0.0.0/rtdetr-l.pt",
        "description": "RT-DETR Large - general object detection",
        "size_mb": 64,
    },
    "rtdetr_x": {
        "url": "https://github.com/ultralytics/assets/releases/download/v0.0.0/rtdetr-x.pt",
        "description": "RT-DETR Extra Large - general object detection",
        "size_mb": 130,
    },
}


# =============================================================================
# Detection Data Class
# =============================================================================

@dataclass
class Detection:
    """Single object detection result."""
    label: str
    confidence: float
    bbox: List[int]  # [x1, y1, x2, y2]
    center_x: int
    center_y: int


@dataclass
class VisionResult:
    """Complete vision analysis result."""
    detections: List[Detection]
    description: Optional[str] = None  # For VLM-generated descriptions
    raw_response: Optional[Dict[str, Any]] = None  # Raw API response for VLM


# =============================================================================
# Detector Protocol and Base Class
# =============================================================================

class BaseDetector(ABC):
    """Abstract base class for all detectors."""

    def __init__(self, agent, config: dict):
        """Initialize the detector.

        Args:
            agent: The Agent instance
            config: Vision configuration dict from profile
        """
        self.agent = agent
        self.config = config
        self.model = None
        self.model_available = False
        self.model_path = config.get("model")

    @abstractmethod
    def detect(self, image_path: str) -> List[Detection]:
        """Run detection on an image.

        Args:
            image_path: Path to the image file

        Returns:
            List of Detection objects
        """
        pass

    @abstractmethod
    def format_for_llm(self, detections: List[Detection]) -> str:
        """Format detection results for LLM context.

        Args:
            detections: List of Detection objects

        Returns:
            Formatted string for LLM prompt
        """
        pass

    def is_available(self) -> bool:
        """Check if the detector is available."""
        return self.model_available

    def _pack_message(self, message: str) -> str:
        """Pack message with agent name prefix."""
        return f"[Vision \"{self.agent.configs['username']}\"] {message}"


# =============================================================================
# YOLO Detector
# =============================================================================

class YOLODetector(BaseDetector):
    """YOLO-based detector using pretrained COCO model with LLM translation.

    Uses YOLOv10 pretrained on COCO dataset for general object detection.
    Raw COCO labels are passed to the LLM with a translation guide,
    allowing the LLM to interpret detections in Minecraft context.
    """

    # COCO dataset labels that commonly appear in Minecraft
    # These are raw labels from the model - LLM will translate them
    COCO_LABELS_HINTS = {
        "person": "player, villager, zombie, skeleton, or other humanoid mob",
        "cow": "Minecraft cow (passive mob)",
        "sheep": "Minecraft sheep (passive mob)",
        "pig": "Minecraft pig (passive mob)",
        "horse": "Minecraft horse or similar rideable mob",
        "bird": "chicken or parrot",
        "cat": "Minecraft cat or ocelot",
        "dog": "wolf or tamed dog",
        "potted plant": "flower, crop, or decorative plant block",
        "clock": "clock item or redstone component",
        "book": "bookshelf or enchanting table",
        "bottle": "potion bottle or glass bottle item",
        "cup": "potion or drink item",
        "chair": "stairs block used as seating",
        "bench": "stairs or slab blocks",
        "couch": "bed or stairs arrangement",
        "bed": "Minecraft bed block",
        "dining table": "crafting table, furnace, or similar utility block",
        "tv": "enchanting table or decorative block",
        "laptop": "crafting table or similar blocky interface",
        "cell phone": "held item or small block",
        "backpack": "shulker box or chest",
        "umbrella": "held item or decorative block",
        "handbag": "bundle or small storage item",
        "tie": "decorative banner or armor trim",
        "suitcase": "shulker box or ender chest",
        "frisbee": "held disc item or projectile",
        "skis": "held item or elongated block",
        "snowboard": "boat or held item",
        "sports ball": "slimeball, fireball, or round item",
        "kite": "elytra or banner",
        "baseball bat": "sword, axe, or held tool",
        "baseball glove": "held item or armor piece",
        "skateboard": "boat or minecart",
        "surfboard": "boat",
        "tennis racket": "hoe or held tool",
        "bottle": "potion or glass bottle",
        "wine glass": "potion bottle",
        "fork": "held item or tool",
        "knife": "sword or shears",
        "spoon": "held item or shovel",
        "bowl": "bowl item or stew",
        "banana": "held food item",
        "apple": "apple or golden apple",
        "sandwich": "bread or food item",
        "orange": "orange dye or held item",
        "broccoli": "crop or plant block",
        "carrot": "carrot crop or item",
        "hot dog": "food item",
        "pizza": "cake or food block",
        "donut": "cake or sweet item",
        "cake": "Minecraft cake block",
        "chair": "stairs block",
        "couch": "bed or stairs",
        "potted plant": "flower in pot",
        "bed": "bed block",
        "mirror": "glass or reflective block",
        "window": "glass pane or window",
        "door": "wooden or iron door",
        "fence": "fence or fence gate",
        "vase": "flower pot",
        "scissors": "shears",
        "teddy bear": "plush mob or decorative item",
        "hair drier": "held item",
        "toothbrush": "held item",
    }

    def __init__(self, agent, config: dict):
        super().__init__(agent, config)
        self.confidence_threshold = config.get("confidence_threshold", 0.3)
        self._init_model()

    def _init_model(self):
        """Initialize YOLO model."""
        # Get model source (URL or local path)
        if not self.model_path:
            self.model_path = DEFAULT_MODELS[DetectorType.YOLO]

        # Check if this is a simple ultralytics model name (e.g., "yolov10n.pt")
        # Ultralytics can auto-download these models
        is_ultralytics_pretrained = (
            not is_url(self.model_path) and
            not os.path.isabs(self.model_path) and
            not os.path.exists(self.model_path)
        )

        if is_ultralytics_pretrained:
            # Let ultralytics handle the download automatically
            try:
                from ultralytics import YOLO
                add_log(
                    title=self._pack_message("Loading YOLO model"),
                    content=f"Model: {self.model_path} (ultralytics auto-download)",
                    label="agent"
                )
                self.model = YOLO(self.model_path)
                self.model_available = True
                add_log(
                    title=self._pack_message("YOLO model loaded"),
                    content=f"Model: {self.model_path}",
                    label="success"
                )
                return
            except ImportError as e:
                print_msg(
                    title=self._pack_message("Vision dependencies not installed"),
                    content=f"Install with: uv add ultralytics torch Pillow\nError: {str(e)}",
                    label="warning"
                )
                self.model = None
                self.model_available = False
                return
            except Exception as e:
                print_msg(
                    title=self._pack_message("YOLO model initialization failed"),
                    content=f"Exception: {str(e)}",
                    label="warning"
                )
                self.model = None
                self.model_available = False
                return

        # For URLs or local paths, use existing logic
        local_path = get_model_full_path(self.model_path)

        if not local_path:
            print_msg(
                title=self._pack_message("YOLO model not found"),
                content=f"Model '{self.model_path}' is not downloaded. Vision is disabled for this session.\n"
                        f"To enable vision, restart the application and allow the model download.",
                label="warning"
            )
            self.model = None
            self.model_available = False
            return

        try:
            from ultralytics import YOLO
            self.model = YOLO(local_path)
            self.model_available = True
            add_log(
                title=self._pack_message("YOLO model loaded"),
                content=f"Model: {local_path}",
                label="success"
            )
        except ImportError as e:
            print_msg(
                title=self._pack_message("Vision dependencies not installed"),
                content=f"Install with: uv add ultralytics torch Pillow\nError: {str(e)}",
                label="warning"
            )
            self.model = None
            self.model_available = False
        except Exception as e:
            print_msg(
                title=self._pack_message("YOLO model initialization failed"),
                content=f"Exception: {str(e)}",
                label="warning"
            )
            self.model = None
            self.model_available = False

    def detect(self, image_path: str) -> List[Detection]:
        """Run YOLO detection on image."""
        if self.model is None or not os.path.exists(image_path):
            return []

        try:
            results = self.model(image_path, conf=self.confidence_threshold, verbose=False)
            detections = []

            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for i in range(len(boxes)):
                        box = boxes.xyxy[i].cpu().numpy()
                        conf = float(boxes.conf[i].cpu().numpy())
                        cls_id = int(boxes.cls[i].cpu().numpy())
                        label = result.names[cls_id]
                        # Keep raw COCO label - LLM will translate with context

                        x1, y1, x2, y2 = map(int, box)
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2

                        detection = Detection(
                            label=label,
                            confidence=conf,
                            bbox=[x1, y1, x2, y2],
                            center_x=center_x,
                            center_y=center_y
                        )
                        detections.append(detection)

            add_log(
                title=self._pack_message("YOLO detection complete"),
                content=f"Found {len(detections)} objects",
                label="agent",
                print=False
            )
            return detections

        except Exception as e:
            add_log(
                title=self._pack_message("YOLO detection error"),
                content=f"Exception: {str(e)}",
                label="warning"
            )
            return []

    def format_for_llm(self, detections: List[Detection]) -> str:
        """Format YOLO detections for LLM context with translation guide."""
        lines = [
            "## Visual Observation (YOLO Detection - COCO Dataset)",
            "",
            "You see the following objects through your vision system. ",
            "**Important:** This uses a general-purpose YOLOv10 model trained on real-world objects (COCO dataset). ",
            "The labels are real-world object names, NOT Minecraft-specific terms.",
            "",
            "### Translation Guide:",
            "In the blocky, pixelated world of Minecraft, COCO labels map roughly as follows:",
            "- 'person' → player, villager, zombie, skeleton, or other humanoid mob",
            "- 'cow', 'sheep', 'pig', 'horse' → corresponding passive Minecraft mobs",
            "- 'bird' → chicken or parrot",
            "- 'cat' → Minecraft cat or ocelot",
            "- 'dog' → wolf or tamed dog",
            "- 'potted plant' → flower, crop, or plant block",
            "- 'chair', 'bench', 'couch' → stairs or slabs used as furniture",
            "- 'bed' → Minecraft bed block",
            "- 'dining table' → crafting table, furnace, or utility block",
            "- 'backpack', 'suitcase' → shulker box, chest, or ender chest",
            "- 'bottle', 'wine glass', 'cup' → potion or drink item",
            "- Many other objects may represent blocks, items, or held objects",
            "",
            "Use your knowledge of recent events, nearby entities, inventory state, ",
            "and environmental context to interpret these detections appropriately.",
            "",
            "### Detected objects:"
        ]

        if not detections:
            lines.append("- No significant objects detected in current view.")
            return "\n".join(lines)

        # Group detections by label
        grouped = {}
        for det in detections:
            if det.label not in grouped:
                grouped[det.label] = []
            grouped[det.label].append(det)

        for label, dets in grouped.items():
            count = len(dets)
            avg_conf = sum(d.confidence for d in dets) / count * 100

            if count == 1:
                det = dets[0]
                position = VisionSystem._get_position_description_static(
                    det.center_x, det.center_y
                )
                lines.append(f"- {label} x1 ({position}, confidence: {avg_conf:.0f}%)")
            else:
                positions = [
                    VisionSystem._get_position_description_static(d.center_x, d.center_y)
                    for d in dets
                ]
                unique_positions = list(set(positions))
                pos_str = ", ".join(unique_positions) if len(unique_positions) <= 3 else "various positions"
                lines.append(f"- {label} x{count} (positions: {pos_str}, avg confidence: {avg_conf:.0f}%)")

        return "\n".join(lines)


# =============================================================================
# RT-DETR Detector
# =============================================================================

class RTDETRDetector(BaseDetector):
    """RT-DETR-based detector for general object detection."""

    def __init__(self, agent, config: dict):
        super().__init__(agent, config)
        self.confidence_threshold = config.get("confidence_threshold", 0.3)
        self._init_model()

    def _init_model(self):
        """Initialize RT-DETR model."""
        # Get model source (URL or local path)
        if not self.model_path:
            self.model_path = DEFAULT_MODELS[DetectorType.RTDETR]

        # Get local path (may need to download if URL)
        local_path = get_model_full_path(self.model_path)

        if not local_path:
            print_msg(
                title=self._pack_message("RT-DETR model not found"),
                content=f"Model '{self.model_path}' is not downloaded. Vision is disabled for this session.\n"
                        f"To enable vision, restart the application and allow the model download.",
                label="warning"
            )
            self.model = None
            self.model_available = False
            return

        try:
            from ultralytics import RTDETR
            self.model = RTDETR(local_path)
            self.model_available = True
            add_log(
                title=self._pack_message("RT-DETR model loaded"),
                content=f"Model: {local_path}",
                label="success"
            )
        except ImportError as e:
            print_msg(
                title=self._pack_message("Vision dependencies not installed"),
                content=f"Install with: uv add ultralytics torch Pillow\nError: {str(e)}",
                label="warning"
            )
            self.model = None
            self.model_available = False
        except Exception as e:
            print_msg(
                title=self._pack_message("RT-DETR model initialization failed"),
                content=f"Exception: {str(e)}",
                label="warning"
            )
            self.model = None
            self.model_available = False

    def detect(self, image_path: str) -> List[Detection]:
        """Run RT-DETR detection on image."""
        if self.model is None or not os.path.exists(image_path):
            return []

        try:
            results = self.model(image_path, conf=self.confidence_threshold, verbose=False)
            detections = []

            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for i in range(len(boxes)):
                        box = boxes.xyxy[i].cpu().numpy()
                        conf = float(boxes.conf[i].cpu().numpy())
                        cls_id = int(boxes.cls[i].cpu().numpy())
                        label = result.names[cls_id]

                        x1, y1, x2, y2 = map(int, box)
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2

                        detection = Detection(
                            label=label,
                            confidence=conf,
                            bbox=[x1, y1, x2, y2],
                            center_x=center_x,
                            center_y=center_y
                        )
                        detections.append(detection)

            add_log(
                title=self._pack_message("RT-DETR detection complete"),
                content=f"Found {len(detections)} objects",
                label="agent",
                print=False
            )
            return detections

        except Exception as e:
            add_log(
                title=self._pack_message("RT-DETR detection error"),
                content=f"Exception: {str(e)}",
                label="warning"
            )
            return []

    def format_for_llm(self, detections: List[Detection]) -> str:
        """Format RT-DETR detections for LLM context."""
        lines = [
            "## Visual Observation (RT-DETR Detection)",
            "",
            "You see the following objects through your vision system. ",
            "**Important:** This uses a general-purpose object detector (not Minecraft-specific). ",
            "Labels like 'person' may represent players or mobs, 'object' may be items or blocks. ",
            "Use your knowledge of the Minecraft world, combined with nearby entities, inventory, ",
            "and environmental context to interpret these detections appropriately.",
            "",
            "Detected objects:"
        ]

        if not detections:
            lines.append("- No significant objects detected in current view.")
            return "\n".join(lines)

        # Group detections by label
        grouped = {}
        for det in detections:
            if det.label not in grouped:
                grouped[det.label] = []
            grouped[det.label].append(det)

        for label, dets in grouped.items():
            count = len(dets)
            avg_conf = sum(d.confidence for d in dets) / count * 100

            if count == 1:
                det = dets[0]
                position = VisionSystem._get_position_description_static(
                    det.center_x, det.center_y
                )
                lines.append(f"- {label} x1 ({position}, confidence: {avg_conf:.0f}%)")
            else:
                positions = [
                    VisionSystem._get_position_description_static(d.center_x, d.center_y)
                    for d in dets
                ]
                unique_positions = list(set(positions))
                pos_str = ", ".join(unique_positions) if len(unique_positions) <= 3 else "various positions"
                lines.append(f"- {label} x{count} (positions: {pos_str}, avg confidence: {avg_conf:.0f}%)")

        return "\n".join(lines)


# =============================================================================
# VLM Detector
# =============================================================================

class VLMDetector(BaseDetector):
    """Vision Language Model detector for rich image understanding.

    Configuration:
    - model: API model name (e.g., "gpt-4o", "claude-3-opus-20240229")
    - vlm.base_url: API base URL (e.g., "https://api.openai.com/v1")
    - vlm.api_key: API key (supports "env:VAR_NAME" prefix)
    - vlm.prompt: Custom prompt for vision analysis
    """

    def __init__(self, agent, config: dict):
        super().__init__(agent, config)
        self.vlm_config = config.get("vlm", {})
        self._init_model()

    def _init_model(self):
        """Initialize VLM detector.

        The 'model' field in vision config is the API model name.
        The 'vlm' section contains base_url and api_key.
        Falls back to agent's LLM config if vlm section is not provided.
        """
        # Get API model name from vision.model field
        self.api_model = self.model_path  # In VLM context, model_path is the API model name

        # Get VLM-specific config or fall back to agent's LLM config
        if self.vlm_config:
            self.base_url = self.vlm_config.get("base_url", "")
            self.api_key = self._get_api_key(self.vlm_config)
            self.prompt = self.vlm_config.get("prompt")
        else:
            # Fall back to agent's LLM config
            llm_config = self.agent.configs.get("llm", {})
            self.base_url = llm_config.get("base_url", "")
            self.api_key = self._get_api_key(llm_config)
            self.prompt = None

        # If no API model specified, try to get from vlm config or use default
        if not self.api_model:
            self.api_model = self.vlm_config.get("model") or self.agent.configs.get("llm", {}).get("model", "gpt-4o")

        # Validate configuration
        if not self.base_url:
            add_log(
                title=self._pack_message("VLM detector misconfigured"),
                content="No base_url provided in vlm config or llm config",
                label="warning"
            )
            self.model_available = False
            return

        if not self.api_key:
            add_log(
                title=self._pack_message("VLM detector misconfigured"),
                content="No api_key provided in vlm config or llm config",
                label="warning"
            )
            self.model_available = False
            return

        self.model_available = True
        add_log(
            title=self._pack_message("VLM detector initialized"),
            content=f"Model: {self.api_model}, Base URL: {self.base_url}",
            label="success"
        )

    def detect(self, image_path: str) -> List[Detection]:
        """VLM doesn't return structured detections - use analyze instead."""
        return []

    def analyze(self, image_path: str) -> Optional[str]:
        """Analyze image using VLM and return description.

        Args:
            image_path: Path to the image file

        Returns:
            Description string or None on failure
        """
        if not self.model_available:
            return None

        if not os.path.exists(image_path):
            add_log(
                title=self._pack_message("VLM analysis failed"),
                content=f"Image not found: {image_path}",
                label="warning"
            )
            return None

        try:
            # Read image as base64
            import base64
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            # Determine image format
            ext = os.path.splitext(image_path)[1].lower()
            mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else f"image/{ext[1:]}"

            # Build request
            import requests
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # Use custom prompt or default
            prompt = self.prompt or (
                "You are a Minecraft bot analyzing what you see through your eyes. "
                "Describe the scene briefly (2-3 sentences), focusing on:\n"
                "1. Any players or mobs visible and their positions\n"
                "2. Notable blocks, structures, or terrain features\n"
                "3. Potential dangers or items of interest\n"
                "Be specific and concise. Use relative positions (left, right, center, far, near)."
            )

            payload = {
                "model": self.api_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 300
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                description = result["choices"][0]["message"]["content"]
                add_log(
                    title=self._pack_message("VLM analysis complete"),
                    content=description[:100] + "..." if len(description) > 100 else description,
                    label="agent",
                    print=False
                )
                return description
            else:
                add_log(
                    title=self._pack_message("VLM API error"),
                    content=f"Status: {response.status_code}, {response.text[:200]}",
                    label="warning"
                )
                return None

        except Exception as e:
            add_log(
                title=self._pack_message("VLM analysis error"),
                content=f"Exception: {str(e)}",
                label="warning"
            )
            return None

    def _get_api_key(self, config: dict) -> Optional[str]:
        """Get API key from config, handling env: prefix."""
        api_key = config.get("api_key", "")
        if api_key.startswith("env:"):
            env_var = api_key[4:]
            return os.environ.get(env_var)
        return api_key

    def format_for_llm(self, detections: List[Detection]) -> str:
        """VLM doesn't use detection-based formatting."""
        return ""


# =============================================================================
# Detector Factory
# =============================================================================

def create_detector(detector_type: str, agent, config: dict) -> BaseDetector:
    """Create a detector instance based on type.

    Args:
        detector_type: Type of detector ("yolo", "rtdetr", "vlm")
        agent: The Agent instance
        config: Vision configuration dict

    Returns:
        Detector instance
    """
    detectors = {
        "yolo": YOLODetector,
        "rtdetr": RTDETRDetector,
        "vlm": VLMDetector,
    }

    detector_class = detectors.get(detector_type.lower())
    if detector_class is None:
        add_log(
            title=f"[Vision] Unknown detector type: {detector_type}",
            content=f"Falling back to YOLO detector",
            label="warning"
        )
        detector_class = YOLODetector

    return detector_class(agent, config)


# =============================================================================
# Model Management Functions
# =============================================================================

def is_url(path: str) -> bool:
    """Check if the path is a URL."""
    return path.startswith("http://") or path.startswith("https://")


def get_filename_from_url(url: str) -> str:
    """Extract filename from URL."""
    from urllib.parse import urlparse, unquote
    parsed = urlparse(url)
    filename = os.path.basename(unquote(parsed.path))
    # If no extension, add .pt
    if not os.path.splitext(filename)[1]:
        filename += ".pt"
    return filename


def get_local_model_path(model_source: str) -> str:
    """Get the local path for a model source (URL or local path).

    Args:
        model_source: URL or local path to the model

    Returns:
        Local path where the model should be stored
    """
    if is_url(model_source):
        # URL: store in models directory with extracted filename
        filename = get_filename_from_url(model_source)
        return os.path.join(MODELS_DIR, filename)
    else:
        # Local path: use as-is
        return os.path.expanduser(model_source)


def is_valid_model(model_source: str) -> bool:
    """Check if the model source is valid (URL or existing local file)."""
    if is_url(model_source):
        return True
    return os.path.isfile(os.path.expanduser(model_source))


def get_model_paths(model_source: str) -> List[str]:
    """Get the possible paths for a model file.

    Args:
        model_source: URL or local path to the model

    Returns:
        List of possible paths where the model might be stored
    """
    if is_url(model_source):
        # For URLs, check the local cache
        local_path = get_local_model_path(model_source)
        return [local_path]
    else:
        # For local paths, check multiple locations
        expanded = os.path.expanduser(model_source)
        return [
            expanded,  # As provided
            os.path.join(MODELS_DIR, os.path.basename(expanded)),  # In models dir
            os.path.expanduser(f"~/.config/ultralytics/{os.path.basename(expanded)}"),
            os.path.expanduser(f"~/.config/ultralytics/weights/{os.path.basename(expanded)}"),
        ]


def is_model_downloaded(model_source: str, validate: bool = True) -> bool:
    """Check if the model file exists without triggering download.

    Args:
        model_source: URL or local path to the model
        validate: If True, also validate the model can be loaded

    Returns:
        True if model exists and is valid, False otherwise
    """
    model_path = None

    for path in get_model_paths(model_source):
        if os.path.isfile(path):
            model_path = path
            break

    if not model_path:
        return False

    if not validate:
        return True

    return _validate_model_file(model_path)


def _validate_model_file(model_path: str) -> bool:
    """Validate that a model file is not corrupted.

    Args:
        model_path: Full path to the model file

    Returns:
        True if model is valid, False if corrupted
    """
    # Minimum valid size (models should be at least 1MB)
    min_valid_size = 1 * 1024 * 1024

    try:
        actual_size = os.path.getsize(model_path)
        if actual_size < min_valid_size:
            add_log(
                title="[Vision] Model file appears corrupted",
                content=f"Model: {model_path}, Size: {actual_size // (1024*1024)}MB (too small)",
                label="warning"
            )
            return False
    except OSError:
        return False

    try:
        import torch
        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        if checkpoint is None:
            return False
        return True
    except ImportError:
        return True
    except Exception as e:
        add_log(
            title="[Vision] Model validation failed",
            content=f"Model: {model_path}, Error: {str(e)}",
            label="warning"
        )
        return False


def get_model_full_path(model_source: str) -> Optional[str]:
    """Get the full path to a downloaded model file.

    Args:
        model_source: URL or local path to the model

    Returns:
        Full path to the model file, or None if not found
    """
    for path in get_model_paths(model_source):
        if os.path.isfile(path):
            return path

    return None


def get_model_size_mb(model_source: str) -> int:
    """Get the estimated size of a model in MB.

    Args:
        model_source: URL or local path to the model

    Returns:
        Estimated size in MB
    """
    # If local file exists, get actual size
    local_path = get_model_full_path(model_source)
    if local_path:
        try:
            return os.path.getsize(local_path) // (1024 * 1024)
        except OSError:
            pass

    # Try to estimate from URL/filename
    filename = os.path.basename(model_source).lower()
    for pattern, size in KNOWN_MODEL_SIZES.items():
        if pattern in filename:
            return size

    # Default estimate
    return 64


def get_available_disk_space_mb(path: str = ".") -> int:
    """Get available disk space in MB."""
    try:
        stat = shutil.disk_usage(path)
        return stat.free // (1024 * 1024)
    except Exception:
        return -1


def download_model(model_source: str) -> Tuple[bool, str]:
    """Download the model from URL with a progress bar.

    Args:
        model_source: URL to download the model from

    Returns:
        Tuple of (success, message)
    """
    import requests

    if not is_url(model_source):
        # It's a local path, check if it exists
        local_path = os.path.expanduser(model_source)
        if os.path.isfile(local_path):
            return True, f"Using local model: {local_path}"
        return False, f"Local model file not found: {local_path}"

    local_path = get_local_model_path(model_source)
    filename = os.path.basename(local_path)

    try:
        # Ensure models directory exists
        os.makedirs(MODELS_DIR, exist_ok=True)

        add_log(
            title="[Vision] Starting model download",
            content=f"URL: {model_source}",
            label="agent"
        )

        # Try to connect with feedback
        try:
            sys.stdout.write(f"\r  Connecting to download server...")
            sys.stdout.flush()

            response = requests.get(model_source, stream=True, timeout=(10, 60))
            response.raise_for_status()
        except requests.exceptions.Timeout:
            sys.stdout.write(f"\r  Connection timeout after 10 seconds.\n")
            sys.stdout.flush()
            raise Exception("Connection timeout. Please check your network and try again.")
        except requests.exceptions.ConnectionError as e:
            sys.stdout.write(f"\r  Connection failed.\n")
            sys.stdout.flush()
            raise Exception(f"Connection error: {str(e)}. Please check your network.")
        except requests.exceptions.RequestException as e:
            sys.stdout.write(f"\r  Request failed.\n")
            sys.stdout.flush()
            raise Exception(f"Download failed: {str(e)}")

        total_size = int(response.headers.get('content-length', 0))
        if total_size > 0:
            sys.stdout.write(f"\r  Connected! Starting download ({total_size // (1024*1024)}MB)...\n")
        else:
            sys.stdout.write(f"\r  Connected! Starting download...\n")
        sys.stdout.flush()

        downloaded = 0
        start_time = time.time()

        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        bar_width = 30
                        filled = int(bar_width * downloaded / total_size)
                        bar = '█' * filled + '░' * (bar_width - filled)

                        elapsed = time.time() - start_time
                        speed = (downloaded / (1024 * 1024)) / elapsed if elapsed > 0 else 0

                        downloaded_mb = downloaded / (1024 * 1024)
                        total_mb = total_size / (1024 * 1024)

                        sys.stdout.write(f"\r  [{bar}] {percent:.1f}% | {downloaded_mb:.1f}MB/{total_mb:.1f}MB | {speed:.1f}MB/s")
                        sys.stdout.flush()

        print()

        if os.path.exists(local_path):
            add_log(
                title="[Vision] Model download complete",
                content=f"Model saved to: {local_path}",
                label="success"
            )
            return True, f"Successfully downloaded to {local_path}"
        else:
            return False, "Download completed but model file not found"

    except KeyboardInterrupt:
        print()
        print_msg(
            title="[Vision] Download cancelled",
            content="Download was interrupted by user.",
            label="warning"
        )

        if os.path.exists(local_path):
            try:
                os.remove(local_path)
                add_log(
                    title="[Vision] Partial file cleaned up",
                    content=f"Removed: {local_path}",
                    label="agent"
                )
            except OSError as e:
                add_log(
                    title="[Vision] Failed to clean up partial file",
                    content=f"Error: {str(e)}",
                    label="warning"
                )

        return False, "Download cancelled by user"

    except ImportError as e:
        return False, f"Requests not installed. Run: uv add requests. Error: {str(e)}"
    except Exception as e:
        print()
        return False, f"Download failed: {str(e)}"


def prompt_user(question: str) -> bool:
    """Prompt user for yes/no confirmation."""
    try:
        response = input(f"{question} [y/N]: ").strip().lower()
        return response in ['y', 'yes']
    except EOFError:
        return False
    except Exception:
        return False


def check_and_prepare_model(model_source: str, auto_download: bool = True) -> Tuple[bool, bool]:
    """Check if model is ready, and optionally handle download.

    Args:
        model_source: URL or local path to the model
        auto_download: Whether to prompt for download if not present

    Returns:
        Tuple of (model_ready, should_continue)
        - model_ready: True if model is available
        - should_continue: True if agent should start (even without model)
    """
    # Check if model exists and is valid locally
    if is_model_downloaded(model_source, validate=True):
        local_path = get_model_full_path(model_source)
        add_log(
            title="[Vision] Model found",
            content=f"Model: {local_path}",
            label="success"
        )
        return True, True

    # Check if model file exists but is corrupted
    local_path = get_model_full_path(model_source)
    if local_path and not _validate_model_file(local_path):
        add_log(
            title="[Vision] Corrupted model detected",
            content=f"Model: {local_path}",
            label="warning"
        )
        print_msg(
            title="[Vision] Corrupted model file found",
            content=f"The model file appears to be corrupted or incomplete.\n"
                    f"Location: {local_path}\n"
                    f"It will be deleted and re-downloaded.",
            label="warning"
        )
        try:
            os.remove(local_path)
            add_log(
                title="[Vision] Corrupted model deleted",
                content=f"Deleted: {local_path}",
                label="agent"
            )
        except OSError as e:
            add_log(
                title="[Vision] Failed to delete corrupted model",
                content=f"Error: {str(e)}",
                label="error"
            )

    # Check if it's a URL (can be downloaded) or local path
    if not is_url(model_source):
        # Local path that doesn't exist
        add_log(
            title="[Vision] Model file not found",
            content=f"Path: {model_source}",
            label="error"
        )
        print_msg(
            title="[Vision] Model file not found",
            content=f"The specified model file does not exist:\n"
                    f"  {model_source}\n\n"
                    f"Please provide a valid local path or URL to the model.",
            label="error"
        )

        if prompt_user("Start the agent without vision model?"):
            return False, True
        return False, False

    # It's a URL - model not found but can be downloaded
    model_size = get_model_size_mb(model_source)
    disk_space = get_available_disk_space_mb()

    add_log(
        title="[Vision] Model not found",
        content=f"URL: {model_source}, Estimated size: ~{model_size}MB",
        label="warning"
    )

    if not auto_download:
        return False, True

    # Check disk space
    if disk_space >= 0 and disk_space < model_size:
        add_log(
            title="[Vision] Insufficient disk space",
            content=f"Required: {model_size}MB, Available: {disk_space}MB",
            label="error"
        )
        print_msg(
            title="[Vision] Insufficient disk space",
            content=f"Cannot download model. Required: {model_size}MB, Available: {disk_space}MB",
            label="error"
        )

        if prompt_user("Start the agent without vision model?"):
            return False, True
        return False, False

    # Show reminder and ask for confirmation
    filename = get_filename_from_url(model_source)
    print_msg(
        title="[Vision] Model download required",
        content=f"\n"
                f"  Model: {filename}\n"
                f"  URL: {model_source}\n"
                f"  Size: ~{model_size} MB\n"
                f"  Available disk space: {disk_space} MB\n\n"
                f"  This model will be downloaded from the internet.\n"
                f"  The download may take a few minutes depending on your connection.",
        label="warning"
    )

    if prompt_user("Download the vision model?"):
        print_msg(
            title="[Vision] Downloading model...",
            content="Please wait, this may take a few minutes.",
            label="agent"
        )

        success, message = download_model(model_source)

        if success:
            print_msg(
                title="[Vision] Download complete",
                content=message,
                label="success"
            )
            return True, True
        else:
            print_msg(
                title="[Vision] Download failed",
                content=message,
                label="error"
            )

            if prompt_user("Start the agent without vision model?"):
                return False, True
            return False, False
    else:
        if prompt_user("Start the agent without vision model?"):
            return False, True
        return False, False


def check_vision_requirements(profiles: list) -> dict:
    """Check vision requirements for all profiles.

    Args:
        profiles: List of profile paths

    Returns:
        Dict mapping profile path to vision requirement status
    """
    results = {}

    for profile_path in profiles:
        try:
            with open(profile_path, 'r') as f:
                profile = json.load(f)

            vision_config = profile.get("vision", {})
            if vision_config.get("enabled", False):
                detector_type = vision_config.get("detector", "yolo")

                # Get model source (URL or local path)
                model_source = vision_config.get("model")
                if not model_source:
                    # Use default model for detector type
                    detector_enum = DetectorType(detector_type.lower())
                    model_source = DEFAULT_MODELS.get(detector_enum)

                # VLM doesn't need a local model
                needs_model = detector_type.lower() != "vlm"

                results[profile_path] = {
                    "enabled": True,
                    "detector": detector_type,
                    "model": model_source,
                    "model_ready": not needs_model or (model_source and is_model_downloaded(model_source))
                }
            else:
                results[profile_path] = {
                    "enabled": False,
                    "detector": None,
                    "model": None,
                    "model_ready": True
                }
        except Exception as e:
            add_log(
                title="[Vision] Error reading profile",
                content=f"Profile: {profile_path}, Error: {str(e)}",
                label="warning"
            )
            results[profile_path] = {
                "enabled": False,
                "detector": None,
                "model": None,
                "model_ready": True
            }

    return results


# =============================================================================
# Vision System Class
# =============================================================================

class VisionSystem:
    """Manages screenshot capture and object detection for Minecraft AI."""

    # Position descriptions based on screen regions
    POSITION_LEFT = "left"
    POSITION_CENTER = "center"
    POSITION_RIGHT = "right"
    POSITION_TOP = "top"
    POSITION_MIDDLE = "middle"
    POSITION_BOTTOM = "bottom"

    def __init__(self, agent, config: dict):
        """Initialize the vision system.

        Args:
            agent: The Agent instance
            config: Vision configuration dict from profile
        """
        self.agent = agent
        self.config = config
        self.detector = None
        self.camera = None

        # Screenshot storage path
        self.screenshot_dir = os.path.join("bots", agent.configs["username"], "screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)

        # Detection cache to avoid redundant captures
        self._detection_cache: Optional[List[Detection]] = None
        self._vlm_description_cache: Optional[str] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_ttl = config.get("cache_ttl_seconds", 2)

        # Configuration
        self.detector_type = config.get("detector", "yolo").lower()
        self.max_saved_screenshots = config.get("max_saved_screenshots", 10)

        # Initialize detector and camera
        self._init_detector()
        self._init_camera()

    def _init_detector(self):
        """Initialize the detector based on configuration."""
        try:
            self.detector = create_detector(self.detector_type, self.agent, self.config)
            add_log(
                title=self._pack_message(f"Detector initialized"),
                content=f"Type: {self.detector_type}",
                label="success"
            )
        except Exception as e:
            add_log(
                title=self._pack_message("Detector initialization failed"),
                content=f"Exception: {str(e)}",
                label="warning"
            )
            self.detector = None

    def _init_camera(self):
        """Initialize camera using Python camera module."""
        try:
            self.camera = Camera(
                self.agent.bot,
                self.screenshot_dir
            )
            if self.camera.is_ready():
                add_log(
                    title=self._pack_message("Camera ready"),
                    content="Camera initialized and ready for capture",
                    label="success"
                )
            else:
                add_log(
                    title=self._pack_message("Camera initializing"),
                    content="Waiting for bot to spawn...",
                    label="agent"
                )
        except Exception as e:
            add_log(
                title=self._pack_message("Camera initialization failed"),
                content=f"Exception: {str(e)}",
                label="warning"
            )
            self.camera = None

    def capture_screenshot(self) -> Optional[str]:
        """Capture screenshot from bot's first-person view."""
        if self.camera is None:
            add_log(
                title=self._pack_message("Screenshot failed"),
                content="Camera not initialized",
                label="warning"
            )
            return None

        if not self.camera.is_ready():
            add_log(
                title=self._pack_message("Screenshot failed"),
                content="Camera not ready yet",
                label="warning"
            )
            return None

        try:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.camera.capture()
                    )
                    filename = future.result()
            else:
                filename = loop.run_until_complete(self.camera.capture())

            if filename:
                filepath = os.path.join(self.screenshot_dir, f"{filename}.jpg")
                add_log(
                    title=self._pack_message("Screenshot captured"),
                    content=filepath,
                    label="agent",
                    print=False
                )
                return filepath
            else:
                add_log(
                    title=self._pack_message("Screenshot failed"),
                    content="Camera returned no filename",
                    label="warning"
                )
                return None
        except Exception as e:
            add_log(
                title=self._pack_message("Screenshot capture exception"),
                content=f"Exception: {str(e)}",
                label="error"
            )
            return None

    def _get_position_description(self, center_x: int, center_y: int, width: int = 800, height: int = 512) -> str:
        """Get human-readable position description based on screen coordinates."""
        return self._get_position_description_static(center_x, center_y, width, height)

    @staticmethod
    def _get_position_description_static(center_x: int, center_y: int, width: int = 800, height: int = 512) -> str:
        """Get human-readable position description based on screen coordinates."""
        # Horizontal position (3 regions)
        if center_x < width // 3:
            h_pos = VisionSystem.POSITION_LEFT
        elif center_x < 2 * width // 3:
            h_pos = VisionSystem.POSITION_CENTER
        else:
            h_pos = VisionSystem.POSITION_RIGHT

        # Vertical position (3 regions)
        if center_y < height // 3:
            v_pos = VisionSystem.POSITION_TOP
        elif center_y < 2 * height // 3:
            v_pos = VisionSystem.POSITION_MIDDLE
        else:
            v_pos = VisionSystem.POSITION_BOTTOM

        return f"{h_pos}-{v_pos}"

    def get_vision_context(self) -> Optional[str]:
        """Get complete vision context for LLM prompt.

        Handles caching to avoid redundant captures within TTL period.

        Returns:
            Formatted vision context string, or None if vision is unavailable
        """
        # Check if camera is ready
        camera_ready = self.camera is not None and self.camera.is_ready()
        if not camera_ready:
            return None

        # Log when camera first becomes ready
        if not hasattr(self, '_camera_ready_logged'):
            add_log(
                title=self._pack_message("Vision system active"),
                content="Camera ready, vision detection enabled",
                label="success"
            )
            self._camera_ready_logged = True

        # Check if detector is available
        if self.detector is None or not self.detector.is_available():
            if not hasattr(self, '_detector_unavailable_logged'):
                print_msg(
                    title=self._pack_message("Vision unavailable"),
                    content=f"Detector '{self.detector_type}' is not available. "
                            f"Restart the application to download the model.",
                    label="warning"
                )
                self._detector_unavailable_logged = True
            return None

        # Check cache
        current_time = time.time()
        if (self._cache_timestamp is not None and
            current_time - self._cache_timestamp < self._cache_ttl):
            add_log(
                title=self._pack_message("Using cached vision data"),
                content=f"Cache age: {current_time - self._cache_timestamp:.2f}s",
                label="agent",
                print=False
            )
            # Return cached result based on detector type
            if self.detector_type == "vlm" and self._vlm_description_cache:
                return self._format_vlm_result(self._vlm_description_cache)
            elif self._detection_cache is not None:
                return self.detector.format_for_llm(self._detection_cache)

        # Capture screenshot
        image_path = self.capture_screenshot()
        if image_path is None:
            return None

        # Clean up old screenshots
        self._cleanup_old_screenshots()

        # Run detection based on detector type
        if self.detector_type == "vlm":
            # VLM returns a description
            description = self.detector.analyze(image_path)
            self._vlm_description_cache = description
            self._detection_cache = []
            self._cache_timestamp = current_time

            if description:
                return self._format_vlm_result(description)
            return None
        else:
            # YOLO and RT-DETR return detections
            detections = self.detector.detect(image_path)
            self._detection_cache = detections
            self._vlm_description_cache = None
            self._cache_timestamp = current_time

            return self.detector.format_for_llm(detections)

    def _format_vlm_result(self, description: str) -> str:
        """Format VLM description for LLM context."""
        lines = [
            "## Visual Observation (VLM Analysis)",
            "",
            "Here is what you see through your vision system:",
            "",
            description
        ]
        return "\n".join(lines)

    def _pack_message(self, message: str) -> str:
        """Pack message with agent name prefix."""
        return f"[Vision \"{self.agent.configs['username']}\"] {message}"

    def _cleanup_old_screenshots(self):
        """Remove old screenshots to keep only the latest N."""
        try:
            if not os.path.exists(self.screenshot_dir):
                return

            files = [
                os.path.join(self.screenshot_dir, f)
                for f in os.listdir(self.screenshot_dir)
                if f.endswith('.jpg') and f.startswith('screenshot_')
            ]

            if len(files) == 0:
                return

            if self.max_saved_screenshots <= 0:
                files_to_remove = files
            elif len(files) <= self.max_saved_screenshots:
                return
            else:
                files.sort(key=lambda x: os.path.getmtime(x))
                files_to_remove = files[:-self.max_saved_screenshots]

            for filepath in files_to_remove:
                try:
                    os.remove(filepath)
                    add_log(
                        title=self._pack_message("Old screenshot removed"),
                        content=f"Removed: {os.path.basename(filepath)}",
                        label="agent",
                        print=False
                    )
                except OSError as e:
                    add_log(
                        title=self._pack_message("Failed to remove screenshot"),
                        content=f"Error: {str(e)}",
                        label="warning"
                    )

            if files_to_remove:
                kept_count = len(files) - len(files_to_remove)
                add_log(
                    title=self._pack_message("Screenshot cleanup"),
                    content=f"Removed {len(files_to_remove)} old screenshots, keeping {kept_count}",
                    label="agent",
                    print=False
                )

        except Exception as e:
            add_log(
                title=self._pack_message("Screenshot cleanup error"),
                content=f"Exception: {str(e)}",
                label="warning"
            )
