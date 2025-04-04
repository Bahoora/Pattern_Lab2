# -*- coding: utf-8 -*-
"""Pattern_Lab2_Trial2.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1iO68pM9lfjc6198tAHIuzHaJ7aVun8eO
"""

import kagglehub

# Download latest version
path = kagglehub.dataset_download("surajghuwalewala/ham1000-segmentation-and-classification")

print("Path to dataset files:", path)

import os
import pandas as pd
import shutil
from sklearn.model_selection import train_test_split


dataset_path = "/root/.cache/kagglehub/datasets/surajghuwalewala/ham1000-segmentation-and-classification/versions/2"

# List files in the dataset directory
print("Dataset contents:", os.listdir(dataset_path))

# Define dataset path (after downloading)
dataset_path = "/root/.cache/kagglehub/datasets/surajghuwalewala/ham1000-segmentation-and-classification/versions/2"

# Load the metadata file (assumed to be in CSV format)
metadata_path = os.path.join(dataset_path, "GroundTruth.csv")  # Adjust filename if needed
df = pd.read_csv(metadata_path)

# Ensure you have the required columns
print(df.head())

# Convert one-hot encoding to single class column
df['dx'] = df[['MEL', 'NV', 'BCC', 'AKIEC', 'BKL', 'DF', 'VASC']].idxmax(axis=1)

# Now apply label mapping
label_mapping = {"MEL": 0, "NV": 1, "BCC": 2, "AKIEC": 3, "BKL": 4, "DF": 5, "VASC": 6}
df['label'] = df['dx'].map(label_mapping)
df = df.dropna(subset=['label'])  # Remove rows with missing labels

# Define the image directory
image_dir = os.path.join(dataset_path, "images")  # Adjust if needed

# Splitting Data Stratified
train_df, test_df = train_test_split(df, test_size=0.2, stratify=df['dx'], random_state=42)
train_df, val_df = train_test_split(train_df, test_size=0.1, stratify=train_df['dx'], random_state=42)

# Function to move images to appropriate folders
def move_images(df, source_dir, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    for img_name in df['image']:
        src = os.path.join(source_dir, img_name + ".jpg")  # Adjust extension if needed
        dest = os.path.join(dest_dir, img_name + ".jpg")
        if os.path.exists(src):
            shutil.copy(src, dest)

# Create directories
move_images(train_df, image_dir, "dataset/train")
move_images(val_df, image_dir, "dataset/val")
move_images(test_df, image_dir, "dataset/test")

print(f"Train size: {len(train_df)}, Val size: {len(val_df)}, Test size: {len(test_df)}")

# Remove leakage by image ID
def remove_duplicates(df1, df2, key='image'):
    common = set(df1[key]).intersection(set(df2[key]))
    return df2[~df2[key].isin(common)]

test_df = remove_duplicates(train_df, test_df)
val_df = remove_duplicates(train_df, val_df)
test_df = remove_duplicates(val_df, test_df)

# Patient-level leakage removal
if 'patient_id' in df.columns:
    train_patients = set(train_df['patient_id'])
    val_df = val_df[~val_df['patient_id'].isin(train_patients)]
    test_df = test_df[~test_df['patient_id'].isin(train_patients)]
    test_df = test_df[~test_df['patient_id'].isin(set(val_df['patient_id']))]

# Create directories
def create_dirs(base='dataset'):
    for split in ['train', 'val', 'test']:
        for cls in label_mapping:
            path = os.path.join(base, split, cls)
            os.makedirs(path, exist_ok=True)

create_dirs()

# Move and check images
corrupt_images = []

def move_and_check(df, split, source_dir, dest_base):
    for _, row in df.iterrows():
        img_name = row['image'] + ".jpg"
        label = row['dx']
        src = os.path.join(source_dir, img_name)
        dest = os.path.join(dest_base, split, label, img_name)
        try:
            # Validate image
            with Image.open(src) as img:
                img.verify()  # Will raise error if corrupt
            shutil.copy(src, dest)
        except Exception as e:
            corrupt_images.append(img_name)

move_and_check(train_df, 'train', image_dir, 'dataset')
move_and_check(val_df, 'val', image_dir, 'dataset')
move_and_check(test_df, 'test', image_dir, 'dataset')

print(f"Total corrupt images found and skipped: {len(corrupt_images)}")

import random
from PIL import Image
import os

# Image augmentation functions
def random_rotation(image):
    return image.rotate(random.uniform(-30, 30))

def random_flip(image):
    if random.random() > 0.5:
        return image.transpose(Image.FLIP_LEFT_RIGHT)
    return image

def random_crop(image, output_size=(224, 224)):
    width, height = image.size
    left = random.randint(0, width // 4)
    top = random.randint(0, height // 4)
    right = width - random.randint(0, width // 4)
    bottom = height - random.randint(0, height // 4)
    return image.crop((left, top, right, bottom)).resize(output_size)


def preprocess_and_save(df, source_dir, dest_dir, image_column, label_column):
    processed_count = 0
    missing_count = 0
    error_count = 0

    for _, row in df.iterrows():
        img_name = row[image_column]
        label = str(row[label_column])  # e.g. '0', '1', ..., '6'
        class_dir = os.path.join(dest_dir, label)
        os.makedirs(class_dir, exist_ok=True)

        src = os.path.join(source_dir, img_name)
        dest = os.path.join(class_dir, img_name)

        # Check if file exists with extensions
        if not os.path.exists(src):
            if os.path.exists(src + ".jpg"):
                src += ".jpg"
                dest += ".jpg"
            elif os.path.exists(src + ".png"):
                src += ".png"
                dest += ".png"
            else:
                print(f"❌ Missing during preprocessing: {src}")
                missing_count += 1
                continue

        try:
            with Image.open(src) as img:
                img = img.convert("RGB")
                img.save(dest)
                processed_count += 1
        except Exception as e:
            print(f"❌ Error processing {src}: {e}")
            error_count += 1

    print(f"✅ Processed images: {processed_count}")
    print(f"❌ Missing images: {missing_count}")
    print(f"❌ Errors during processing: {error_count}")

# Re-run for the test set
preprocess_and_save(test_df, "dataset/test", "dataset/preprocessed_test", "image", "label")


# Apply preprocessing
preprocess_and_save(train_df, "dataset/train", "dataset/preprocessed_train", "image","label" )
preprocess_and_save(test_df, "dataset/test", "dataset/preprocessed_test", "image","label")
preprocess_and_save(val_df, "dataset/val", "dataset/preprocessed_val", "image","label")

print("Preprocessing complete.")

from torchvision import transforms
from torch.utils.data import Dataset
from PIL import Image
import os

class SegmentationDataset(Dataset):
    def __init__(self, image_dir, mask_dir, transform=None):
        self.image_dir = image_dir
        self.mask_dir = mask_dir
        self.image_names = os.listdir(image_dir)
        self.transform = transform

    def __getitem__(self, idx):
        img_path = os.path.join(self.image_dir, self.image_names[idx])
        mask_path = os.path.join(self.mask_dir, self.image_names[idx])

        image = Image.open(img_path).convert("RGB")
        mask = Image.open(mask_path).convert("L")  # single channel for binary

        if self.transform:
            # Apply joint transformations here using libraries like Albumentations
            augmented = self.transform(image=np.array(image), mask=np.array(mask))
            image = transforms.ToTensor()(augmented['image'])
            mask = torch.tensor(augmented['mask'], dtype=torch.float).unsqueeze(0) / 255.0
        else:
            image = transforms.ToTensor()(image)
            mask = transforms.ToTensor()(mask)

        return image, mask

    def __len__(self):
        return len(self.image_names)

import os
from collections import Counter

def count_images_per_class(base_dir):
    counts = {}
    for class_name in os.listdir(base_dir):
        class_dir = os.path.join(base_dir, class_name)
        if os.path.isdir(class_dir):
            counts[class_name] = len(os.listdir(class_dir))
    return counts

print(count_images_per_class("dataset/preprocessed_train"))

import torch
import torch.nn as nn
import torchvision.models as models

# Load pre-trained ResNet18 (only ~11.7 million parameters)
def build_model(num_classes):
    model = models.resnet18(pretrained=True)

    # Replace the final classification layer to match HAM10000 classes
    model.fc = nn.Linear(model.fc.in_features, num_classes)

    return model

# Count total trainable parameters
def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

# Set device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Build model
num_classes = 7  # MEL, NV, BCC, AKIEC, BKL, DF, VASC
model = build_model(num_classes).to(device)

# Print model summary
total_params = count_parameters(model)
print(f"✅ Total trainable parameters: {total_params:,}")

import torch
import torch.nn.functional as F
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Evaluation function
def evaluate_model(model, dataloader, class_names):
    model.eval()
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for images, labels in dataloader:
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)
            _, preds = torch.max(outputs, 1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    # Overall Accuracy
    acc = accuracy_score(all_labels, all_preds)
    print(f"\n✅ Test Accuracy: {acc:.4f}\n")

    # Classification Report (Precision, Recall, F1 per class)
    print("🔍 Classification Report:")
    print(classification_report(all_labels, all_preds, target_names=class_names))

    # Confusion Matrix
    cm = confusion_matrix(all_labels, all_preds)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=class_names, yticklabels=class_names)
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.title("📊 Confusion Matrix")
    plt.tight_layout()
    plt.show()

from torchvision import transforms
from torchvision.datasets import ImageFolder
from torch.utils.data import DataLoader

# Replace with your model's expected normalization values if different
test_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],  # ImageNet means
                         std=[0.229, 0.224, 0.225])   # ImageNet stds
])

# Your DataLoader for the preprocessed test set
# Example: test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)
test_dataset = ImageFolder(root='dataset/preprocessed_test', transform=test_transforms)
test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False, num_workers=4)

# Define class labels (match your label mapping)
class_names = ["MEL", "NV", "BCC", "AKIEC", "BKL", "DF", "VASC"]

# Evaluate the model
evaluate_model(model, test_loader, class_names)

#THIS IS WITHOUT BONUS
import torch
import torch.nn as nn
import torch.nn.functional as F

class UNet(nn.Module):
    def __init__(self, in_channels=3, out_channels=1):
        super(UNet, self).__init__()

        def conv_block(in_c, out_c):
            return nn.Sequential(
                nn.Conv2d(in_c, out_c, kernel_size=3, padding=1),
                nn.BatchNorm2d(out_c),
                nn.ReLU(inplace=True),
                nn.Conv2d(out_c, out_c, kernel_size=3, padding=1),
                nn.BatchNorm2d(out_c),
                nn.ReLU(inplace=True),
            )

        self.enc1 = conv_block(in_channels, 64)
        self.enc2 = conv_block(64, 128)
        self.enc3 = conv_block(128, 256)
        self.enc4 = conv_block(256, 512)

        self.pool = nn.MaxPool2d(2)

        self.bottleneck = conv_block(512, 1024)

        self.upconv4 = nn.ConvTranspose2d(1024, 512, kernel_size=2, stride=2)
        self.dec4 = conv_block(1024, 512)

        self.upconv3 = nn.ConvTranspose2d(512, 256, kernel_size=2, stride=2)
        self.dec3 = conv_block(512, 256)

        self.upconv2 = nn.ConvTranspose2d(256, 128, kernel_size=2, stride=2)
        self.dec2 = conv_block(256, 128)

        self.upconv1 = nn.ConvTranspose2d(128, 64, kernel_size=2, stride=2)
        self.dec1 = conv_block(128, 64)

        self.out_conv = nn.Conv2d(64, out_channels, kernel_size=1)

    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        e4 = self.enc4(self.pool(e3))

        b = self.bottleneck(self.pool(e4))

        d4 = self.upconv4(b)
        d4 = torch.cat((e4, d4), dim=1)
        d4 = self.dec4(d4)

        d3 = self.upconv3(d4)
        d3 = torch.cat((e3, d3), dim=1)
        d3 = self.dec3(d3)

        d2 = self.upconv2(d3)
        d2 = torch.cat((e2, d2), dim=1)
        d2 = self.dec2(d2)

        d1 = self.upconv1(d2)
        d1 = torch.cat((e1, d1), dim=1)
        d1 = self.dec1(d1)

        return torch.sigmoid(self.out_conv(d1))

# outputs_class, outputs_mask = model(images)

# # Classification loss
# loss_cls = criterion_class(outputs_class, labels)

# # Segmentation loss
# loss_seg = criterion_seg(outputs_mask, masks)

# # Total loss (you can tune the weights)
# loss = loss_cls + loss_seg

from torch.utils.data import Dataset
from PIL import Image
import os

class SegmentationDataset(Dataset):
    def __init__(self, image_dir, mask_dir, transform=None):
        self.image_dir = image_dir
        self.mask_dir = mask_dir
        self.transform = transform
        self.image_names = os.listdir(image_dir)

    def __len__(self):
        return len(self.image_names)

    def __getitem__(self, idx):
        img_path = os.path.join(self.image_dir, self.image_names[idx])
        mask_path = os.path.join(self.mask_dir, self.image_names[idx].replace(".jpg", "_mask.png"))  # adjust as needed

        image = Image.open(img_path).convert("RGB")
        mask = Image.open(mask_path).convert("L")  # binary mask

        if self.transform:
            augmented = self.transform(image=np.array(image), mask=np.array(mask))
            image = augmented['image']
            mask = augmented['mask']

        return image, mask

import torch
import numpy as np

# Dice Coefficient: 2 * |A ∩ B| / (|A| + |B|)
def dice_score(pred, target, smooth=1e-6):
    pred = pred.view(-1)
    target = target.view(-1)
    intersection = (pred * target).sum()
    return (2. * intersection + smooth) / (pred.sum() + target.sum() + smooth)

# IoU: |A ∩ B| / |A ∪ B|
def iou_score(pred, target, smooth=1e-6):
    pred = pred.view(-1)
    target = target.view(-1)
    intersection = (pred * target).sum()
    union = pred.sum() + target.sum() - intersection
    return (intersection + smooth) / (union + smooth)

def evaluate_model(model, dataloader, device):
    model.eval()
    dice_scores = []
    iou_scores = []

    with torch.no_grad():
        for images, masks in dataloader:
            images = images.to(device)
            masks = masks.to(device)

            outputs = model(images)
            preds = (outputs > 0.5).float()  # Threshold for binary masks
            #print(preds.unique(), true.unique())
            for pred, true in zip(preds, masks):
                pred = pred.view(-1)
                true = true.view(-1)
                # Normalize to float32 binary masks
                pred = pred.float()
                true = (true > 0.5).float()

                dice = dice_score(pred, true)
                iou = iou_score(pred, true)
                dice_scores.append(dice.item())
                iou_scores.append(iou.item())

    avg_dice = np.mean(dice_scores)
    avg_iou = np.mean(iou_scores)

    print(f"\n✅ Test Dice Coefficient: {avg_dice:.4f}")
    print(f"✅ Test IoU Score: {avg_iou:.4f}")
    return avg_dice, avg_iou
dice, iou = evaluate_model(model, test_loader, device)

#dice score is low, >0.7 is good, IoU score was too high,should be from 0-1, >0.5 is ok,, >0.8 is good