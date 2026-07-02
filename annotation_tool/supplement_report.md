# Supplementary Methods: U-Net Segmentation of Cardiac Organoids

## S1. Dataset Preparation

Video recordings of beating cardiac organoids were acquired under phase-contrast microscopy.
A total of **82 representative frames** were extracted from the video dataset
(`raw_1.png` – `raw_82.png`).

Initial binary segmentation masks were generated using a MATLAB-based U-Net pipeline
(`prepare_masks.m`), producing one mask per frame in which white pixels (255) denote
organoid foreground and black pixels (0) denote background.

All 82 initial masks were subsequently reviewed and manually corrected using a custom
freehand lasso annotation tool (`annotate.py`) built with OpenCV. Each mask was refined
by the annotator using left-button drag (add foreground) and right-button drag (remove
foreground) gestures. Nine frames were flagged and excluded due to poor image quality,
motion blur, or ambiguous organoid boundaries, yielding a final dataset of
**73 annotated image–mask pairs**.

---

## S2. Model Architecture

Segmentation was performed using a **U-Net** architecture
(Ronneberger et al., 2015) with a **ResNet-34 encoder pre-trained on ImageNet**
(TernausNet paradigm; Iglovikov & Shvets, 2018).

| Component | Configuration |
|---|---|
| Framework | `segmentation-models-pytorch` v0.5.0 |
| Encoder | ResNet-34 (ImageNet pre-trained) |
| Decoder | Standard U-Net decoder, 4 upsampling blocks |
| Input channels | 3 (RGB) |
| Output | 1 channel, binary mask via sigmoid |
| Input resolution | 512 × 512 pixels |

Transfer learning from ImageNet was applied to the full network (encoder not frozen),
as phase-contrast microscopy images differ substantially in appearance from natural images,
requiring full fine-tuning to adapt learned features.

---

## S3. Training Protocol

### 3.1 Data Augmentation

Augmentation was applied exclusively to the training split. Validation and test splits
received only resizing and normalization.

| Transform | Parameters | Probability |
|---|---|---|
| Horizontal flip | — | 0.5 |
| Vertical flip | — | 0.5 |
| Random rotation | ±15° | 0.5 |
| Brightness / Contrast jitter | ±20% | 0.5 |
| Gaussian noise | σ ∈ [0.01, 0.05] | 0.3 |
| Resize | 512 × 512 | 1.0 |
| Normalize | mean = (0.485, 0.456, 0.406), std = (0.229, 0.224, 0.225) | 1.0 |

ImageNet mean and standard deviation were used for normalization, consistent with the
pre-trained encoder's training distribution.

### 3.2 Loss Function

Training minimized a composite loss combining Binary Cross-Entropy (BCE) and Dice loss
with equal weighting:

$$\mathcal{L} = 0.5 \cdot \mathcal{L}_{\text{BCE}} + 0.5 \cdot \mathcal{L}_{\text{Dice}}$$

BCE provides stable pixel-wise gradients during early training and addresses
foreground–background imbalance; Dice loss is region-based and improves boundary
delineation. Their combination has been shown to achieve both fast convergence and
accurate segmentation in medical imaging contexts.

### 3.3 Optimizer and Scheduler

| Hyperparameter | Value |
|---|---|
| Optimizer | Adam |
| Learning rate | 1 × 10⁻⁴ |
| LR scheduler | ReduceLROnPlateau (patience = 5, factor = 0.5) |
| Batch size | 4 (GPU) |
| Max epochs | 100 |
| Early stopping patience | 15 epochs |
| Best model criterion | Lowest validation loss |

### 3.4 Reproducibility

All random states were fixed prior to training:
`random.seed(42)`, `numpy.random.seed(42)`, `torch.manual_seed(42)`,
`torch.cuda.manual_seed_all(42)`, `torch.backends.cudnn.deterministic = True`,
`torch.backends.cudnn.benchmark = False`.

---

## S4. Evaluation Methodology

Given the limited dataset size (n = 73), model performance was evaluated using
**5-fold cross-validation** (sklearn `KFold`, `shuffle=True`, `random_state=42`)
rather than a single held-out test split, to ensure all samples contribute to evaluation
and to obtain stable performance estimates.

In each fold, the model was trained on approximately 58 samples and evaluated on
approximately 15 held-out samples. The five folds together cover all 73 samples exactly once.

### 4.1 Metrics

Pixel-level accuracy was intentionally excluded from reported metrics.
Because organoid foreground occupies a small fraction of each image
(background-dominant images), a model predicting all-background would achieve
>97% pixel accuracy, rendering this metric uninformative.
The following foreground-sensitive metrics were computed per sample
(TP, FP, FN accumulated individually) and reported as mean ± SD:

| Metric | Formula |
|---|---|
| Dice Similarity Coefficient (DSC) | 2TP / (2TP + FP + FN) |
| Intersection over Union (IoU / Jaccard) | TP / (TP + FP + FN) |
| Sensitivity (Recall) | TP / (TP + FN) |
| Precision | TP / (TP + FP) |

All metrics were computed at a binarization threshold of 0.5 on the sigmoid output.

---

## S5. Results

### 5.1 Per-Fold Performance

| Fold | n (val) | DSC | IoU | Sensitivity | Precision |
|---|---|---|---|---|---|
| 1 | 15 | 0.9331 ± 0.0284 | 0.8758 ± 0.0475 | 0.9248 ± 0.0406 | 0.9426 ± 0.0318 |
| 2 | 15 | 0.9139 ± 0.0734 | 0.8488 ± 0.1094 | 0.9067 ± 0.0728 | 0.9245 ± 0.0859 |
| 3 | 15 | 0.9325 ± 0.0329 | 0.8753 ± 0.0563 | 0.9179 ± 0.0658 | 0.9511 ± 0.0199 |
| 4 | 14 | 0.9296 ± 0.0326 | 0.8702 ± 0.0554 | 0.9281 ± 0.0451 | 0.9336 ± 0.0463 |
| 5 | 14 | 0.9285 ± 0.0474 | 0.8700 ± 0.0771 | 0.9376 ± 0.0487 | 0.9257 ± 0.0785 |

### 5.2 Overall 5-Fold CV Performance (n = 73)

| Metric | Mean ± SD |
|---|---|
| **DSC** | **0.9275 ± 0.0467** |
| **IoU** | **0.8680 ± 0.0735** |
| **Sensitivity** | **0.9227 ± 0.0572** |
| **Precision** | **0.9357 ± 0.0592** |

The high Sensitivity (0.923) confirms that the model consistently detects organoid
regions rather than defaulting to background prediction.
The slightly higher Precision (0.936) indicates that predicted foreground regions
are accurate with minimal false positives.

---

## S6. Implementation Environment

| Component | Version |
|---|---|
| Python | 3.13 |
| PyTorch | 2.11.0+cu128 |
| segmentation-models-pytorch | 0.5.0 |
| albumentations | 2.0.8 |
| scikit-learn | 1.9.0 |
| GPU | NVIDIA GeForce RTX 5060 Laptop GPU (8 GB VRAM) |
| CUDA | 12.8 |
| Training time (5-fold) | ~73 minutes |

---

## References

- Ronneberger, O., Fischer, P., & Brox, T. (2015). U-Net: Convolutional networks for
  biomedical image segmentation. *MICCAI*, 234–241.

- Iglovikov, V., & Shvets, A. (2018). TernausNet: U-Net with VGG11 encoder pre-trained
  on ImageNet for image segmentation. *arXiv:1801.05746*.

- Yakubovskiy, P. (2019). Segmentation Models PyTorch.
  https://github.com/qubvel/segmentation_models.pytorch
