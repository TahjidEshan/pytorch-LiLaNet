import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils import model_zoo


def lilanet(num_classes=13, pretrained=False):
    model = LiLaNet(num_classes)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(''))
    return model


class LiLaNet(nn.Module):
    """
        Implementation of "Boosting LiDAR-based Semantic Labeling by Cross-Modal Training Data Generation"
            <https://arxiv.org/pdf/1804.09915.pdf>
    """

    def __init__(self, num_classes=13):
        super(LiLaNet, self).__init__()

        self.lila1 = LiLaBlock(2, 96)
        self.lila2 = LiLaBlock(96, 128)
        self.lila3 = LiLaBlock(128, 256)
        self.lila4 = LiLaBlock(256, 256)
        self.lila5 = LiLaBlock(256, 128)
        self.classifier = nn.Conv2d(128, num_classes, kernel_size=1)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def forward(self, distance, reflectivity):
        x = torch.cat([distance, reflectivity], 1)
        x = self.lila1(x)
        x = self.lila2(x)
        x = self.lila3(x)
        x = self.lila4(x)
        x = self.lila5(x)

        x = self.classifier(x)

        return x


class LiLaBlock(nn.Module):

    def __init__(self, in_channels, n):
        super(LiLaBlock, self).__init__()

        self.branch1 = BasicConv2d(in_channels, n, kernel_size=(7, 3), padding=(2, 0))
        self.branch2 = BasicConv2d(in_channels, n, kernel_size=3)
        self.branch3 = BasicConv2d(in_channels, n, kernel_size=(3, 7), padding=(0, 2))
        self.conv = BasicConv2d(n * 3, n, kernel_size=1, padding=1)

    def forward(self, x):
        branch1 = self.branch1(x)
        branch2 = self.branch2(x)
        branch3 = self.branch3(x)

        output = torch.cat([branch1, branch2, branch3], 1)
        output = self.conv(output)

        return output


class BasicConv2d(nn.Module):

    def __init__(self, in_channels, out_channels, **kwargs):
        super(BasicConv2d, self).__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, bias=False, **kwargs)
        self.bn = nn.BatchNorm2d(out_channels)

    def forward(self, x):
        x = self.conv(x)
        x = self.bn(x)
        return F.relu(x, inplace=True)


if __name__ == '__main__':
    num_classes, height, width = 13, 64, 512

    model = LiLaNet(num_classes).to('cuda')
    inp = torch.randn(1, 1, height, width).to('cuda')

    out = model(inp, inp)
    assert out.size() == torch.Size([1, num_classes, height, width])

    print('Pass size check.')
