"""Downstream 1D-CNN classifier (MechaForge SimpleCNN style, adapted to
3x2048 windows) and small VAE/GAN generative baselines for CPU training."""
import numpy as np
import torch
import torch.nn as nn


class SimpleCNN(nn.Module):
    def __init__(self, in_ch=3, num_classes=3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(in_ch, 16, 15, stride=2, padding=7), nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Conv1d(16, 32, 9, stride=2, padding=4), nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Conv1d(32, 64, 5, stride=2, padding=2), nn.ReLU(),
            nn.AdaptiveAvgPool1d(8))
        self.fc = nn.Linear(64 * 8, num_classes)

    def forward(self, x):
        return self.fc(self.net(x).flatten(1))


# ---------------- VAE baseline ----------------
class VAE1D(nn.Module):
    def __init__(self, in_ch=3, z=32):
        super().__init__()
        self.enc = nn.Sequential(
            nn.Conv1d(in_ch, 16, 15, 4, 7), nn.ReLU(),
            nn.Conv1d(16, 32, 9, 4, 4), nn.ReLU(),
            nn.Conv1d(32, 64, 5, 4, 2), nn.ReLU(), nn.Flatten())
        self.mu = nn.Linear(64 * 32, z)
        self.lv = nn.Linear(64 * 32, z)
        self.fc = nn.Linear(z, 64 * 32)
        self.dec = nn.Sequential(
            nn.ConvTranspose1d(64, 32, 8, 4, 2), nn.ReLU(),
            nn.ConvTranspose1d(32, 16, 8, 4, 2), nn.ReLU(),
            nn.ConvTranspose1d(16, in_ch, 8, 4, 2))

    def forward(self, x):
        h = self.enc(x)
        mu, lv = self.mu(h), self.lv(h)
        zs = mu + torch.exp(0.5 * lv) * torch.randn_like(mu)
        out = self.dec(self.fc(zs).view(-1, 64, 32))
        return out[..., :x.shape[-1]], mu, lv

    def sample(self, n, device="cpu"):
        zs = torch.randn(n, self.mu.out_features, device=device)
        return self.dec(self.fc(zs).view(-1, 64, 32))[..., :2048]


def train_vae_per_class(Xr, yr, n_gen, epochs=200, seed=0):
    """Train one small VAE per class on the few-shot real subset; sample."""
    torch.manual_seed(seed)
    outX, outY = [], []
    for ci in np.unique(yr):
        Xc = torch.tensor(Xr[yr == ci], dtype=torch.float32)
        m, s = Xc.mean((0, 2), keepdim=True), Xc.std((0, 2), keepdim=True)
        Xn = (Xc - m) / (s + 1e-8)
        vae = VAE1D()
        opt = torch.optim.Adam(vae.parameters(), lr=1e-3)
        for _ in range(epochs):
            rec, mu, lv = vae(Xn)
            loss = ((rec - Xn) ** 2).mean() + \
                1e-4 * (-0.5 * (1 + lv - mu ** 2 - lv.exp()).mean())
            opt.zero_grad(); loss.backward(); opt.step()
        with torch.no_grad():
            g = vae.sample(n_gen) * s + m
        outX.append(g.numpy()); outY.append(np.full(n_gen, ci))
    return np.concatenate(outX), np.concatenate(outY)


# ---------------- GAN baseline ----------------
class Gen1D(nn.Module):
    def __init__(self, z=64, in_ch=3):
        super().__init__()
        self.fc = nn.Linear(z, 64 * 32)
        self.net = nn.Sequential(
            nn.ConvTranspose1d(64, 32, 8, 4, 2), nn.ReLU(),
            nn.ConvTranspose1d(32, 16, 8, 4, 2), nn.ReLU(),
            nn.ConvTranspose1d(16, in_ch, 8, 4, 2))
        self.z = z

    def forward(self, zs):
        return self.net(self.fc(zs).view(-1, 64, 32))[..., :2048]


class Disc1D(nn.Module):
    def __init__(self, in_ch=3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(in_ch, 16, 15, 4, 7), nn.LeakyReLU(0.2),
            nn.Conv1d(16, 32, 9, 4, 4), nn.LeakyReLU(0.2),
            nn.Conv1d(32, 64, 5, 4, 2), nn.LeakyReLU(0.2),
            nn.Flatten(), nn.Linear(64 * 32, 1))

    def forward(self, x):
        return self.net(x)


def train_gan_per_class(Xr, yr, n_gen, epochs=300, seed=0):
    torch.manual_seed(seed)
    bce = nn.BCEWithLogitsLoss()
    outX, outY = [], []
    for ci in np.unique(yr):
        Xc = torch.tensor(Xr[yr == ci], dtype=torch.float32)
        m, s = Xc.mean((0, 2), keepdim=True), Xc.std((0, 2), keepdim=True)
        Xn = (Xc - m) / (s + 1e-8)
        G, D = Gen1D(), Disc1D()
        oG = torch.optim.Adam(G.parameters(), lr=2e-4, betas=(0.5, 0.999))
        oD = torch.optim.Adam(D.parameters(), lr=2e-4, betas=(0.5, 0.999))
        n = len(Xn)
        for _ in range(epochs):
            zs = torch.randn(n, G.z)
            fake = G(zs)
            lD = bce(D(Xn), torch.ones(n, 1)) + \
                bce(D(fake.detach()), torch.zeros(n, 1))
            oD.zero_grad(); lD.backward(); oD.step()
            lG = bce(D(fake), torch.ones(n, 1))
            oG.zero_grad(); lG.backward(); oG.step()
        with torch.no_grad():
            g = G(torch.randn(n_gen, G.z)) * s + m
        outX.append(g.numpy()); outY.append(np.full(n_gen, ci))
    return np.concatenate(outX), np.concatenate(outY)
