import torch
import numpy as np
from tqdm import tqdm
from mediainfo import load_image
from transformers import CLIPModel, CLIPProcessor
from config import CLIP_BATCH_SIZE, CLIP_LABELS, CLIP_MODEL, CLIP_THRESHOLD

def classify_images(paths):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = CLIPModel.from_pretrained(CLIP_MODEL).to(device).eval()
    processor = CLIPProcessor.from_pretrained(CLIP_MODEL)
    labels = list(CLIP_LABELS)
    reasons = []
    embeddings = []

    for start in tqdm(range(0, len(paths), CLIP_BATCH_SIZE), desc="Classifying images"):
        images = [load_image(path, 256) for path in paths[start:start + CLIP_BATCH_SIZE]]
        inputs = processor(text=labels, images=images, return_tensors="pt", padding=True)
        with torch.no_grad():
            outputs = model(**inputs.to(device))
        scores, tops = outputs.logits_per_image.softmax(dim=1).max(dim=1)
        for score, top in zip(scores.tolist(), tops.tolist()):
            reasons.append(CLIP_LABELS[labels[top]] if score >= CLIP_THRESHOLD else None)
        embeddings.append(outputs.image_embeds.cpu().numpy())

    return reasons, np.concatenate(embeddings)
