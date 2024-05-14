# Copyright 2024 The HuggingFace Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import torch


__all__ = ["axis_to_dim", "dtype_info", "group", "ungroup"]


def dtype_info(dtype):
    info = torch.finfo if dtype.is_floating_point else torch.iinfo
    return info(dtype)


def axis_to_dim(t, axis):
    dim = list(range(t.ndim))
    if axis == -1:
        dim = dim[:-1]
    else:
        dim.remove(axis)
    return dim


def group(base: torch.Tensor, axis: int, group_size: int):
    if axis not in (0, -1):
        raise ValueError("Axis must be 0 or -1 for group-wise quantization")
    # In standard per-axis quantization, we have one scale per axis dim
    axis_dim = base.shape[axis]
    # This scale is evaluated over axis_numel items for each feature along axis
    axis_numel = base.numel() // axis_dim
    if group_size > axis_numel or axis_numel % group_size != 0:
        raise ValueError(f"Group size ({group_size}) must be a divisor of ({axis_numel})")
    # Group-wise quantization further splits axis_numel into multiple groups per axis
    axis_groups = axis_numel // group_size
    if axis == 0:
        # Easy-peasy: we simply need to reshape to (axis_dim * axis_groups, group_size)
        return base.reshape([-1, group_size])
    # More difficult: reshape to (group_size, axis_dim * axis_groups)
    # First, split by groups, preserving the axis dimension
    grouped = base.reshape((axis_groups, group_size, axis_dim))
    # Permute to (group_size, axis_dim, axis_groups)
    grouped = grouped.permute(1, 2, 0)
    return grouped.reshape(group_size, axis_dim * axis_groups)


def ungroup(grouped: torch.Tensor, axis: int, orig_shape: torch.Size):
    if grouped.shape == orig_shape:
        return grouped
    if axis == 0:
        # No transposition required, just reshape
        return grouped.reshape(orig_shape)
    group_size = grouped.shape[0] if axis == -1 else grouped.shape[-1]
    axis_dim = orig_shape[axis]
    axis_groups = grouped.numel() // axis_dim // group_size
    ungrouped = grouped.reshape(group_size, axis_dim, axis_groups)
    # Permute to (axis_groups, group_size, axis_dim)
    ungrouped = ungrouped.permute(2, 0, 1)
    return ungrouped.reshape(orig_shape)
