import math
import torch
import torch.nn as nn
from einops import rearrange
import torch.nn.functional as F


def calculate_shift(
    image_seq_len,
    base_seq_len: int = 256,
    max_seq_len: int = 4096,
    base_shift: float = 0.5,
    max_shift: float = 1.15,
):
    m = (max_shift - base_shift) / (max_seq_len - base_seq_len)
    b = base_shift - m * base_seq_len
    shift_constant = image_seq_len * m + b
    return shift_constant


def time_shift(shift_constant: float, timesteps: torch.Tensor, sigma: float = 1):
    return math.exp(shift_constant) / (
        math.exp(shift_constant) + (1 / timesteps - 1) ** sigma
    )


def vae_flatten(latents, patch_size=2):
    # nchw to nhwc then pixel shuffle 2 then flatten
    # n c h w -> n h w c
    # n (h dh) (w dw) c -> n h w (c dh dw)
    # n h w c -> n (h w) c
    # n, c, h, w = latents.shape
    return (
        rearrange(latents, "n c (h dh) (w dw) -> n (h w) (c dh dw)", dh=patch_size, dw=patch_size),
        latents.shape,
    )


def vae_unflatten(latents, shape, patch_size=2):
    # reverse of that operator above
    n, c, h, w = shape
    return rearrange(
        latents,
        "n (h w) (c dh dw) -> n c (h dh) (w dw)",
        dh=patch_size,
        dw=patch_size,
        c=c,
        h=h // patch_size,
        w=w // patch_size,
    )


def prepare_latent_image_ids(batch_size, height, width, patch_size=2):
    # pos embedding for rope, 2d pos embedding, corner embedding and not center based
    latent_image_ids = torch.zeros(height // patch_size, width // patch_size, 3)
    latent_image_ids[..., 1] = (
        latent_image_ids[..., 1] + torch.arange(height // patch_size)[:, None]
    )
    latent_image_ids[..., 2] = (
        latent_image_ids[..., 2] + torch.arange(width // patch_size)[None, :]
    )

    (
        latent_image_id_height,
        latent_image_id_width,
        latent_image_id_channels,
    ) = latent_image_ids.shape

    latent_image_ids = latent_image_ids[None, :].repeat(batch_size, 1, 1, 1)
    latent_image_ids = latent_image_ids.reshape(
        batch_size,
        latent_image_id_height * latent_image_id_width,
        latent_image_id_channels,
    )

    return latent_image_ids
