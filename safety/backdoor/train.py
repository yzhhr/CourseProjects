from typing import Optional
import torch
from torch.utils.data import Dataset, DataLoader
from torch.nn import Module
import torchvision
from transformers import ResNetConfig, ResNetModel
import datasets
import wandb
import hydra
from hydra.utils import get_original_cwd
from omegaconf import DictConfig, OmegaConf
import os
import logging
from tqdm.auto import tqdm, trange
from tqdm.contrib import tenumerate
log = logging.getLogger(__name__)

class AddMark(Module):
    def __init__(self, mask, pattern):
        super().__init__()
        self.mask = mask
        self.pattern = pattern

    def forward(self, x):
        return x * (1 - self.mask) + self.pattern * self.mask
        
def mnist_mask_fn(size=2):
    mask = torch.zeros(1, 28, 28)
    mask[:, 27-size:27, 27-size:27] = 1
    pattern = torch.ones(1, 28, 28)
    mask_fn = AddMark(mask, pattern)
    return mask_fn

class MarkedDataset(Dataset):
    def __init__(self, dataset, mark_fn: Module, damage_portion=0.01, target: Optional[int] = None):
        self.dataset = dataset
        self.mark_fn = mark_fn
        self.damage_portion = damage_portion
        self.target = target
        self.marked = torch.rand(len(dataset)) < damage_portion

    def __getitem__(self, index):
        data, target = self.dataset[index]
        if self.marked[index]:
            return self.mark_fn(data), self.target if self.target is not None else target
        return data, target

    def __len__(self):
        return len(self.dataset)

class MnistCNN(Module):
    def __init__(self):
        super().__init__()
        self.conv1 = torch.nn.Conv2d(1, 16, kernel_size=5, stride=1)
        self.pool1 = torch.nn.AvgPool2d(kernel_size=2, stride=2)
        self.conv2 = torch.nn.Conv2d(16, 32, kernel_size=5, stride=1)
        self.pool2 = torch.nn.AvgPool2d(kernel_size=2, stride=2)
        self.fc1 = torch.nn.Linear(32 * 4 * 4, 128)
        self.fc2 = torch.nn.Linear(128, 10)

    def forward(self, x):
        x = self.pool1(torch.relu(self.conv1(x)))
        x = self.pool2(torch.relu(self.conv2(x)))
        x = x.view(-1, 32 * 4 * 4)
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        return x

def train_loop(cfg: DictConfig, model: Module, trainset: Dataset, testset: Dataset, device: torch.device):
    fullcfg, cfg = cfg, cfg.train
    train_loader = DataLoader(trainset, batch_size=cfg.batch_size, shuffle=True,
                              num_workers=4, pin_memory=True)
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    criterion = torch.nn.CrossEntropyLoss()
    # normalize = torchvision.transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])

    for epoch in trange(cfg.num_epochs):
        for i, (images, labels) in tenumerate(train_loader):
            images = images.to(device)
            labels = labels.to(device)
            # images = normalize(images)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            accuracy = (outputs.argmax(1) == labels).float().mean()
            optimizer.step()
            wandb.log({"loss": loss.item(), "accuracy": accuracy.item(), "epoch": epoch, "step": i})
            # print(f"Epoch: {epoch}, Step: {i}, Loss: {loss.item()}")
        wandb.log({"test_accuracy": eval_accuracy(cfg, model, testset, device)})

def get_accuracy(model, loader, device: torch.device) -> float:
    correct, total = 0, 0
    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            labels = labels.to(device)
            outputs = model(images) 
            correct += (outputs.argmax(1) == labels).float().sum()
            total += len(labels)
    accuracy = correct / total
    return accuracy

def eval_accuracy(cfg: DictConfig, model, dataset, device: torch.device) -> float:
    test_loader = DataLoader(dataset, batch_size=cfg.batch_size, shuffle=False, num_workers=4, pin_memory=True)
    model.eval()
    accuracy = get_accuracy(model, test_loader, device)
    return accuracy

@hydra.main(config_path="configs/", config_name="train", version_base="1.3")
def train(cfg: DictConfig): # train with backdoor
    wandb.config = OmegaConf.to_container(
        cfg, resolve=True, throw_on_missing=True
    )
    wandb.init(project=cfg.wandb.project)

    device = torch.device(cfg.device)
    transform_data = torchvision.transforms.Compose([
        # torchvision.transforms.Resize((32, 32)),
        # torchvision.transforms.Resize((256, 256)),
        # torchvision.transforms.CenterCrop((224, 224)),
        torchvision.transforms.ToTensor(),
    ])
    
    # train_dataset = torchvision.datasets.GTSRB(root=get_original_cwd() +  "/data", split="train", download=True, transform=transform_data)
    trainset = torchvision.datasets.MNIST(root=get_original_cwd() +  "/data", train=True, download=True, transform=transform_data)
    testset = torchvision.datasets.MNIST(root=get_original_cwd() +  "/data", train=False, download=True, transform=transform_data)
    mask_fn = mnist_mask_fn()
    trainset_poisoned = MarkedDataset(trainset, mask_fn, cfg.poison.portion, target=cfg.poison.target)

    # model = torchvision.models.resnet18(weights='IMAGENET1K_V1')
    # model.fc = torch.nn.Linear(512, 43)
    model = MnistCNN()
    # print number of params for each layer
    for name, param in model.named_parameters():
        print(name, param.numel())
    log.info(f"{model}")
    
    wandb.init(project="safety", entity="safety", config=cfg) # type: ignore
    # training
    model.to(device)
    train_loop(cfg, model, trainset_poisoned, testset, device)
    model.cpu()
    
    wandb.finish()
    # save model
    os.makedirs("models", exist_ok=True)
    torch.save(model.state_dict(), f"models/backdoor_{cfg.poison.target}.pth")

if __name__ == "__main__":
    train()
