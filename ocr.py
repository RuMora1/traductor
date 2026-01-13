import logging
from pathlib import Path
from typing import List, Tuple

from PyQt6.QtCore import QRunnable


class OCREngine:
    """Wrapper for RapidOCR. Lazily imports RapidOCR and exposes a simple API."""
    def __init__(self):
        self._engine = None

    def _ensure_engine(self):
        if self._engine is not None:
            return
        try:
            # RapidOCR typical import
            from rapidocr import RapidOCR

            # Instantiate with default config (ONNX models will be used if available)
            self._engine = RapidOCR()
        except Exception as e:
            logging.exception("Failed to initialize RapidOCR")
            raise

    def recognize(self, image) -> List[Tuple[str, float]]:
        """
        Recognize text from a BGR numpy image.
        Returns a list of tuples (text, confidence).
        """
        self._ensure_engine()
        # RapidOCR API may return different formats; try to normalize
        results = self._engine.ocr(image)
        normalized = []
        for item in results:
            # item might be dict or list/tuple
            if isinstance(item, dict):
                text = item.get('text') or item.get('label') or ''
                score = item.get('score', 0.0)
            elif isinstance(item, (list, tuple)):
                # common: [text, score, box]
                if len(item) >= 2 and isinstance(item[0], str):
                    text = item[0]
                    # try find a confidence float in remaining
                    score = 0.0
                    for v in item[1:]:
                        if isinstance(v, float):
                            score = v
                            break
                else:
                    text = str(item)
                    score = 0.0
            else:
                text = str(item)
                score = 0.0
            normalized.append((text, float(score)))
        return normalized


class OCRWorker(QRunnable):
    """Worker that runs OCR on a frame and writes a text file alongside the image."""
    def __init__(self, frame, out_folder: str = "screenshots"):
        super().__init__()
        self.frame = frame
        self.out_folder = Path(out_folder)

    def run(self):
        try:
            engine = OCREngine()
            results = engine.recognize(self.frame)
            texts = [t for t, _ in results if t]
            self.out_folder.mkdir(exist_ok=True)
            filename = self.out_folder / f"ocr_{__import__('datetime').datetime.now():%Y%m%d_%H%M%S}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                for t in texts:
                    f.write(t + "\n")
            logging.info(f"OCR results saved to {filename}")
        except Exception:
            logging.exception("OCRWorker failed")
