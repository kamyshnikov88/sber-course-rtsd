import io
import ssl

import torch
from torch import nn
import torchvision
import torchvision.transforms as transforms
from torchvision.models.detection import fasterrcnn_mobilenet_v3_large_fpn
from PIL import Image
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
import torch.nn.functional as functional


def create_https_context() -> None:
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context


CLASS_DICT = {"2_1": 1, "1_23": 2, "1_17": 3, "3_24": 4, "8_2_1": 5, "5_20": 6,
              "5_19_1": 7, "5_16": 8, "3_25": 9, "6_16": 10, "7_15": 11,
              "2_2": 12, "2_4": 13, "8_13_1": 14, "4_2_1": 15, "1_20_3": 16,
              "1_25": 17, "3_4": 18, "8_3_2": 19, "3_4_1": 20, "4_1_6": 21,
              "4_2_3": 22, "4_1_1": 23, "1_33": 24, "5_15_5": 25, "3_27": 26,
              "1_15": 27, "4_1_2_1": 28, "6_3_1": 29, "8_1_1": 30, "6_7": 31,
              "5_15_3": 32, "7_3": 33, "1_19": 34, "6_4": 35, "8_1_4": 36,
              "8_8": 37, "1_16": 38, "1_11_1": 39, "6_6": 40, "5_15_1": 41,
              "7_2": 42, "5_15_2": 43, "7_12": 44, "3_18": 45, "5_6": 46,
              "5_5": 47, "7_4": 48, "4_1_2": 49, "8_2_2": 50, "7_11": 51,
              "1_22": 52, "1_27": 53, "2_3_2": 54, "5_15_2_2": 55, "1_8": 56,
              "3_13": 57, "2_3": 58, "8_3_3": 59, "2_3_3": 60, "7_7": 61,
              "1_11": 62, "8_13": 63, "1_12_2": 64, "1_20": 65, "1_12": 66,
              "3_32": 67, "2_5": 68, "3_1": 69, "4_8_2": 70, "3_20": 71,
              "3_2": 72, "2_3_6": 73, "5_22": 74, "5_18": 75, "2_3_5": 76,
              "7_5": 77, "8_4_1": 78, "3_14": 79, "1_2": 80, "1_20_2": 81,
              "4_1_4": 82, "7_6": 83, "8_1_3": 84, "8_3_1": 85, "4_3": 86,
              "4_1_5": 87, "8_2_3": 88, "8_2_4": 89, "1_31": 90, "3_10": 91,
              "4_2_2": 92, "7_1": 93, "3_28": 94, "4_1_3": 95, "5_4": 96,
              "5_3": 97, "6_8_2": 98, "3_31": 99, "6_2": 100, "1_21": 101,
              "3_21": 102, "1_13": 103, "1_14": 104, "2_3_4": 105,
              "4_8_3": 106, "6_15_2": 107, "2_6": 108, "3_18_2": 109,
              "4_1_2_2": 110, "1_7": 111, "3_19": 112, "1_18": 113,
              "2_7": 114, "8_5_4": 115, "5_15_7": 116, "5_14": 117,
              "5_21": 118, "1_1": 119, "6_15_1": 120, "8_6_4": 121,
              "8_15": 122, "4_5": 123, "3_11": 124, "8_18": 125,
              "8_4_4": 126, "3_30": 127, "5_7_1": 128, "5_7_2": 129,
              "1_5": 130, "3_29": 131, "6_15_3": 132, "5_12": 133,
              "3_16": 134, "1_30": 135, "5_11": 136, "1_6": 137,
              "8_6_2": 138, "6_8_3": 139, "3_12": 140, "3_33": 141,
              "8_4_3": 142, "5_8": 143, "8_14": 144, "8_17": 145,
              "3_6": 146, "1_26": 147, "8_5_2": 148, "6_8_1": 149,
              "5_17": 150, "1_10": 151, "8_16": 152, "7_18": 153,
              "7_14": 154, "8_23": 155}
CLASS_DICT = {v: k for k, v in CLASS_DICT.items()}


class Model(nn.Module):
    def __init__(self):
        super(Model, self).__init__()
        detector = fasterrcnn_mobilenet_v3_large_fpn(pretrained=True)
        num_classes = 2  # 1 class (sign) + background
        in_features = detector.roi_heads.box_predictor.cls_score.in_features
        detector.roi_heads.box_predictor = FastRCNNPredictor(in_features,
                                                             num_classes)
        for p in detector.parameters():
            p.requires_grad = False
        detector.load_state_dict(
            torch.load(
                'detector_weights.pth',
                map_location=torch.device('cpu')
            )
        )
        detector.eval()
        self.detector = detector

        classifier = torchvision.models.inception_v3(pretrained=True)
        classifier.fc = nn.Linear(2048, 156)
        classifier.load_state_dict(
            torch.load(
                'classifier_weights.pth',
                map_location=torch.device('cpu')
            )
        )
        for param in classifier.parameters():
            param.requires_grad = False
        classifier.eval()
        self.classifier = classifier

    def forward(self, x):
        detector_output = self.detector(x)
        boxes = detector_output[0]['boxes'].tolist()
        scores = detector_output[0]['scores'].tolist()
        boxes = list(filter(lambda i: i[1] > 0.4, zip(boxes, scores)))
        boxes, _ = zip(*boxes)
        int_boxes = list(map(lambda box: list(map(int, box)), boxes))
        crops = list(map(
            lambda box: (
                x[:, :, box[0]:box[2], box[1]:box[3]] if
                box[2] <= x.shape[2] else
                x[:, :, box[1]:box[3], box[0]:box[2]]
            ),
            int_boxes
        ))
        resized_crops = list(map(
            lambda crop: functional.interpolate(crop, size=299),
            crops
        ))
        probabilities = list(map(
            lambda crop: self.classifier(crop), resized_crops
        ))
        all_predictions = list(map(
            lambda p: torch.max(p, -1)[1].view(-1), probabilities
        ))
        class_predictions = filter(lambda p: p != 0, all_predictions)
        signs_predictions = list(map(
            lambda p: CLASS_DICT[p.item()], class_predictions
        ))
        return signs_predictions


create_https_context()
model = Model()


def transform_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    img = transforms.ToTensor()(img).float()
    return img.unsqueeze(0)


def get_prediction(image_tensor):
    # print(image_tensor.shape)
    return model(image_tensor)





