# Third-Party Notices — FutBotMX / StreetVisionFC

This project depends on third-party software. The following notices are provided
for compliance with their respective licenses.

---

## SAM 3 (Segment Anything Model 3)

- **Repository:** https://github.com/facebookresearch/sam3
- **License:** SAM License
- **Copyright:** Copyright (c) Meta Platforms, Inc. and affiliates.
- **Usage:** Core segmentation model. Installed as editable dependency from git.
- **Note:** SAM 3 checkpoint weights must be downloaded separately from the
  official release. They are NOT included in this repository. By installing SAM 3
  from the official repository, users must review and comply with the SAM License
  distributed with that release.

---

## PyTorch

- **Package:** `torch`, `torchvision`
- **Version used:** torch==2.12.0+cu130, torchvision==0.27.0
- **License:** BSD 3-Clause License
- **Copyright:** Copyright (c) Facebook, Inc. (now Meta Platforms, Inc.)
- **URL:** https://github.com/pytorch/pytorch

---

## OpenCV

- **Package:** `opencv-python`
- **Version used:** 4.11.0.86
- **License:** Apache License 2.0
- **URL:** https://github.com/opencv/opencv

---

## supervision

- **Package:** `supervision`
- **Version used:** 0.28.0
- **License:** MIT License
- **Copyright:** Copyright (c) 2023 Roboflow
- **URL:** https://github.com/roboflow/supervision

---

## ByteTrack

- **Usage:** Multi-object tracking algorithm. Integrated via supervision or
  direct implementation in `src/futbotmx/tracking/bytetrack.py`.
- **License:** MIT License
- **Reference:** https://github.com/ifzhang/ByteTrack

---

## NumPy

- **Package:** `numpy`
- **Version used:** 1.26.4
- **License:** BSD 3-Clause License
- **URL:** https://github.com/numpy/numpy

---

## pandas

- **Package:** `pandas`
- **Version used:** 2.3.3
- **License:** BSD 3-Clause License
- **URL:** https://github.com/pandas-dev/pandas

---

## matplotlib

- **Package:** `matplotlib`
- **Version used:** 3.10.9
- **License:** Python Software Foundation License (PSF) / BSD-style
- **URL:** https://github.com/matplotlib/matplotlib

---

## Pillow

- **Package:** `pillow`
- **Version used:** 12.2.0
- **License:** Historical Permission Notice and Disclaimer (HPND)
- **URL:** https://github.com/python-pillow/Pillow

---

## pycocotools

- **Package:** `pycocotools`
- **Version used:** 2.0.11
- **License:** BSD 2-Clause License
- **URL:** https://github.com/cocodataset/cocoapi

---

## einops

- **Package:** `einops`
- **Version used:** 0.8.2
- **License:** MIT License
- **URL:** https://github.com/arogozhnikov/einops

---

## scipy

- **Package:** `scipy`
- **Version used:** 1.17.1
- **License:** BSD 3-Clause License
- **URL:** https://github.com/scipy/scipy

---

## psutil

- **Package:** `psutil`
- **Version used:** 7.2.2
- **License:** BSD 3-Clause License
- **URL:** https://github.com/giampaolo/psutil

---

## timm

- **Package:** `timm`
- **Version used:** 1.0.27
- **License:** Apache License 2.0
- **URL:** https://github.com/huggingface/pytorch-image-models

---

## PyYAML

- **Package:** `pyyaml`
- **Version used:** 6.0.3
- **License:** MIT License
- **URL:** https://github.com/yaml/pyyaml

---

## tqdm

- **Package:** `tqdm`
- **Version used:** 4.67.3
- **License:** MIT License / MPLv2.0
- **URL:** https://github.com/tqdm/tqdm

---

*For the pinned evaluation environment, see `requirements-gpu.txt`.*
