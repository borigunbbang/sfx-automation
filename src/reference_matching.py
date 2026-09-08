"""
M2: 효과 타입 분류 (참고 이미지 매칭, 단순 버전)

지금 단계는 정확도보다 "전체 파이프라인이 굴러가는 것"이 목표라서,
자막 영역을 정밀하게 자동으로 잘라내는 대신 고정 ROI를 그대로 사용하고,
perceptual hash(이미지 지문) 거리로 참고 이미지와 비교한다.
정확도는 이후 튜닝 대상 (TECH_SPEC.md 6번 리스크 참고).
"""
from __future__ import annotations
import os
import yaml
import imagehash
from PIL import Image

DEFAULT_ROI = (0, 650, 1920, 1080)  # M1과 동일한 ROI


class Reference:
    def __init__(self, id, effect_type, sfx_folder, image_path, hash_value):
        self.id = id
        self.effect_type = effect_type
        self.sfx_folder = sfx_folder
        self.image_path = image_path
        self.hash_value = hash_value


def load_references(yaml_path: str) -> list[Reference]:
    base_dir = os.path.dirname(yaml_path)
    with open(yaml_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    refs = []
    for entry in cfg["references"]:
        # 후보 프레임과 동일한 ROI로 비교해야 공정한 비교가 되므로,
        # tight crop이 아니라 전체 프레임을 같은 ROI로 잘라서 해시를 만든다.
        full_img_path = os.path.join(base_dir, entry.get("full_frame_reference", entry["image"]))
        img_path = os.path.join(base_dir, entry["image"])
        full_img = Image.open(full_img_path).convert("RGB")
        h = imagehash.phash(full_img.crop(DEFAULT_ROI), hash_size=16)
        sfx_folder = os.path.normpath(os.path.join(base_dir, entry["sfx_folder"]))
        refs.append(Reference(
            id=entry["id"],
            effect_type=entry["effect_type"],
            sfx_folder=sfx_folder,
            image_path=img_path,
            hash_value=h,
        ))
    return refs


def classify_frame(frame_image: Image.Image, references: list[Reference],
                    roi: tuple = DEFAULT_ROI, max_distance: int = 40):
    """대표 프레임을 ROI로 크롭해서 등록된 참고 이미지들과 비교.
    가장 가까운(distance가 가장 작은) 참고 이미지를 채택하되,
    max_distance보다 멀면 '미분류(unknown)'로 남긴다.
    """
    crop = frame_image.convert("RGB").crop(roi)
    frame_hash = imagehash.phash(crop, hash_size=16)

    best_ref = None
    best_dist = None
    for ref in references:
        dist = frame_hash - ref.hash_value  # 해밍 거리
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_ref = ref

    if best_ref is not None and best_dist <= max_distance:
        return best_ref.effect_type, best_dist, best_ref
    return "unknown", best_dist, None
