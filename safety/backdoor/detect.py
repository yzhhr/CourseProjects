from typing import Optional
import torch
from torch.utils.data import Dataset, DataLoader
from torch.nn import Module
import torchvision
import wandb
import hydra
from hydra.utils import get_original_cwd, to_absolute_path
from omegaconf import DictConfig, OmegaConf
import os
import logging
from tqdm.auto import tqdm, trange
from tqdm.contrib import tenumerate
from train import MnistCNN, add_mark
log = logging.getLogger(__name__)

def find_mask(cfg: DictConfig, model, trainset, target, device: torch.device): # poisoned trainset
    poison_mask = torch.rand(list(cfg.data.image.shape), device=device, requires_grad=True)
    poison_pattern = torch.rand(list(cfg.data.image.shape), device=device, requires_grad=True)

    criterion = torch.nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam([poison_mask, poison_pattern], lr=cfg.detect.lr)
    train_loader = DataLoader(trainset, batch_size=cfg.detect.batch_size, shuffle=True,
                              num_workers=4, pin_memory=True)
    
    wandb.init(project="find_mask")
    model.eval()
    for epoch in trange(cfg.detect.num_epochs):
        for i, (images, _) in enumerate(train_loader):
            images = images.to(device)
            optimizer.zero_grad()
            marked_images = add_mark(poison_mask, poison_pattern, images)
            outputs = model(marked_images)
            labels = torch.full((images.shape[0],), target, dtype=torch.long, device=device)
            loss_pred = criterion(outputs, labels)
            loss_reg = torch.norm(poison_mask, p=1)
            loss = loss_pred + cfg.detect.coef_reg * loss_reg
            loss.backward()
            optimizer.step()
            with torch.no_grad():
                poison_mask.clamp_(0, 1)
                poison_pattern.clamp_(0, 1)
            wandb.log({"loss_pred": loss_pred.item(), "loss_reg": loss_reg.item(),
                "loss": loss.item(), "epoch": epoch, "step": i,
                "poison_mask": poison_mask, "poison_pattern": poison_pattern,
                })
            # print(f"Epoch: {epoch}, Step: {i}, Loss: {loss.item()}")
    wandb.finish()
    return poison_mask.detach().cpu(), poison_pattern.detach().cpu()

@hydra.main(config_path="configs/", config_name="train", version_base="1.3")
def train(cfg: DictConfig): # train with backdoor
    trainset = torchvision.datasets.MNIST(get_original_cwd() + "/data", train=True, download=True, transform=torchvision.transforms.ToTensor())
    device = torch.device(cfg.device)
    model = MnistCNN()
    model.to(device)
    model.load_state_dict(torch.load(to_absolute_path(cfg.poison.model_path)))
    mask_norms = {}
    for target in trange(cfg.data.num_classes):
        mask, pattern = find_mask(cfg, model, trainset, target, device)
        mask_norms[target] = torch.norm(mask, p=1).item()
        log.info(f"Target {target}: L1 norm of mask: {mask_norms[target]}")
        # save mask, pattern
        from torchvision.transforms import ToPILImage
        os.makedirs("mask", exist_ok=True)
        mask_img = ToPILImage()(mask)
        mask_img.save(f"mask/mask_{target}.png")
        pattern_img = ToPILImage()(pattern)
        pattern_img.save(f"mask/pattern_{target}.png")
        product_img = ToPILImage()(mask * pattern)
        product_img.save(f"mask/product_{target}.png")
    log.info(mask_norms)
    import json
    json.dump(mask_norms, open("mask_norms.json", "w", encoding="utf-8"))


if __name__ == "__main__":
    train()
