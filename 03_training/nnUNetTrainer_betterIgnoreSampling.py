import os
from typing import Union, Tuple

import numpy as np
import torch

from nnunetv2.training.dataloading.base_data_loader import nnUNetDataLoaderBase
from nnunetv2.training.dataloading.data_loader_2d import nnUNetDataLoader2D
from nnunetv2.training.dataloading.data_loader_3d import nnUNetDataLoader3D
from nnunetv2.training.loss.compound_losses import DC_and_CE_loss, DC_and_BCE_loss
from nnunetv2.training.loss.deep_supervision import DeepSupervisionWrapper
from nnunetv2.training.loss.dice import MemoryEfficientSoftDiceLoss
from nnunetv2.training.nnUNetTrainer.nnUNetTrainer import nnUNetTrainer
from nnunetv2.training.nnUNetTrainer.variants.data_augmentation.nnUNetTrainerDA5 import nnUNetTrainerDA5, nnUNetTrainerDA5ord0


class nnUNetDataLoaderBaseBetterIgnSampling(nnUNetDataLoaderBase):
    def get_bbox(self, data_shape: np.ndarray, force_fg: bool, class_locations: Union[dict, None],
                 overwrite_class: Union[int, Tuple[int, ...]] = None, verbose: bool = False):
        # in dataloader 2d we need to select the slice prior to this and also modify the class_locations to only have
        # locations for the given slice
        need_to_pad = self.need_to_pad.copy()
        dim = len(data_shape)

        for d in range(dim):
            # if case_all_data.shape + need_to_pad is still < patch size we need to pad more! We pad on both sides
            # always
            if need_to_pad[d] + data_shape[d] < self.patch_size[d]:
                need_to_pad[d] = self.patch_size[d] - data_shape[d]

        # we can now choose the bbox from -need_to_pad // 2 to shape - patch_size + need_to_pad // 2. Here we
        # define what the upper and lower bound can be to then sample form them with np.random.randint
        lbs = [- need_to_pad[i] // 2 for i in range(dim)]
        ubs = [data_shape[i] + need_to_pad[i] // 2 + need_to_pad[i] % 2 - self.patch_size[i] for i in range(dim)]

        # if not force_fg then we can just sample the bbox randomly from lb and ub. Else we need to make sure we get
        # at least one of the foreground classes in the patch
        if not force_fg and not self.has_ignore:
            bbox_lbs = [np.random.randint(lbs[i], ubs[i] + 1) for i in range(dim)]
            # print('I want a random location')
        else:
            if not force_fg and self.has_ignore:
                selected_class = self.annotated_classes_key
                # print(f'I have ignore labels and want to pick a labeled area. annotated_classes_key: {self.annotated_classes_key}')
            elif force_fg:
                assert class_locations is not None, 'if force_fg is set class_locations cannot be None'
                if overwrite_class is not None:
                    assert overwrite_class in class_locations.keys(), 'desired class ("overwrite_class") does not ' \
                                                                      'have class_locations (missing key)'
                # this saves us a np.unique. Preprocessing already did that for all cases. Neat.
                # class_locations keys can also be tuple
                eligible_classes_or_regions = [i for i in class_locations.keys() if len(class_locations[i]) > 0]

                # if we have annotated_classes_key locations and other classes are present, remove the annotated_classes_key from the list
                # strange formulation needed to circumvent
                # ValueError: The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()
                tmp = [i == self.annotated_classes_key if isinstance(i, tuple) else False for i in
                       eligible_classes_or_regions]
                if any(tmp):
                    if len(eligible_classes_or_regions) > 1:
                        eligible_classes_or_regions.pop(np.where(tmp)[0][0])

                if len(eligible_classes_or_regions) == 0:
                    # this only happens if some image does not contain foreground voxels at all
                    selected_class = None
                    if verbose:
                        print('case does not contain any foreground classes')
                else:
                    # I hate myself. Future me aint gonna be happy to read this
                    # 2022_11_25: had to read it today. Wasn't too bad
                    selected_class = eligible_classes_or_regions[np.random.choice(len(eligible_classes_or_regions))] if \
                        (overwrite_class is None or (
                                    overwrite_class not in eligible_classes_or_regions)) else overwrite_class
                # print(f'I want to have foreground, selected class: {selected_class}')
            else:
                raise RuntimeError('lol what!?')
            voxels_of_that_class = class_locations[selected_class] if selected_class is not None else None

            if voxels_of_that_class is not None:
                selected_voxel = voxels_of_that_class[np.random.choice(len(voxels_of_that_class))]
                #################################################################
                if self.has_ignore and not force_fg:
                    # # random offset for selected voxel
                    # orig = deepcopy(selected_voxel)
                    allowed_max_neg_offset = [min(s, p // 2) for s, p in zip(selected_voxel[1:], self.patch_size)]
                    allowed_max_pos_offset = [min(d - s, p // 2) for s, p, d in
                                              zip(selected_voxel[1:], self.patch_size, data_shape)]
                    for d in range(len(self.patch_size)):
                         selected_voxel[d + 1] += np.random.randint(-allowed_max_neg_offset[d], allowed_max_pos_offset[d])
                    # offset = deepcopy(selected_voxel)
                    # # make sure selected voxels are within image boundaries
                    # selected_voxel = [selected_voxel[0]] + [max(0, i) for i in selected_voxel[1:]]
                    # selected_voxel = [selected_voxel[0]] + [min(d, i) for d, i in zip(data_shape, selected_voxel[1:])]
                    # # corr = deepcopy(selected_voxel)
                    # print(f'orig {orig}, offset {offset}, corr {corr}, data shape {data_shape}')
                #################################################################

                # selected voxel is center voxel. Subtract half the patch size to get lower bbox voxel.
                # Make sure it is within the bounds of lb and ub
                # i + 1 because we have first dimension 0!
                bbox_lbs = [max(lbs[i], selected_voxel[i + 1] - self.patch_size[i] // 2) for i in range(dim)]
            else:
                # If the image does not contain any foreground classes, we fall back to random cropping
                bbox_lbs = [np.random.randint(lbs[i], ubs[i] + 1) for i in range(dim)]

        bbox_ubs = [bbox_lbs[i] + self.patch_size[i] for i in range(dim)]

        return bbox_lbs, bbox_ubs


# the following class is evil!
class nnUNetDataLoader2DBetterIgnSampling(nnUNetDataLoader2D):
    def get_bbox(self, data_shape: np.ndarray, force_fg: bool, class_locations: Union[dict, None],
                 overwrite_class: Union[int, Tuple[int, ...]] = None, verbose: bool = False):
        return nnUNetDataLoaderBaseBetterIgnSampling.get_bbox(self, data_shape, force_fg, class_locations,
                                                              overwrite_class, verbose)


# the following class is evil!
class nnUNetDataLoader3DBetterIgnSampling(nnUNetDataLoader3D):
    def get_bbox(self, data_shape: np.ndarray, force_fg: bool, class_locations: Union[dict, None],
                 overwrite_class: Union[int, Tuple[int, ...]] = None, verbose: bool = False):
        return nnUNetDataLoaderBaseBetterIgnSampling.get_bbox(self, data_shape, force_fg, class_locations,
                                                              overwrite_class, verbose)


class nnUNetTrainer_betterIgnoreSampling(nnUNetTrainer):
    def get_plain_dataloaders(self, initial_patch_size: Tuple[int, ...], dim: int):
        dataset_tr, dataset_val = self.get_tr_and_val_datasets()

        if dim == 2:
            dl_tr = nnUNetDataLoader2DBetterIgnSampling(dataset_tr,
                                                        self.batch_size,
                                                        initial_patch_size,
                                                        self.configuration_manager.patch_size,
                                                        self.label_manager,
                                                        oversample_foreground_percent=self.oversample_foreground_percent,
                                                        sampling_probabilities=None, pad_sides=None)
            dl_val = nnUNetDataLoader2DBetterIgnSampling(dataset_val,
                                                         self.batch_size,
                                                         self.configuration_manager.patch_size,
                                                         self.configuration_manager.patch_size,
                                                         self.label_manager,
                                                         oversample_foreground_percent=self.oversample_foreground_percent,
                                                         sampling_probabilities=None, pad_sides=None)
        else:
            dl_tr = nnUNetDataLoader3DBetterIgnSampling(dataset_tr,
                                                        self.batch_size,
                                                        initial_patch_size,
                                                        self.configuration_manager.patch_size,
                                                        self.label_manager,
                                                        oversample_foreground_percent=self.oversample_foreground_percent,
                                                        sampling_probabilities=None, pad_sides=None)
            dl_val = nnUNetDataLoader3DBetterIgnSampling(dataset_val,
                                                         self.batch_size,
                                                         self.configuration_manager.patch_size,
                                                         self.configuration_manager.patch_size,
                                                         self.label_manager,
                                                         oversample_foreground_percent=self.oversample_foreground_percent,
                                                         sampling_probabilities=None, pad_sides=None)
        return dl_tr, dl_val


class nnUNetTrainer_betterIgnoreSampling_noSmooth(nnUNetTrainer_betterIgnoreSampling):
    def _build_loss(self):
        # set smooth to 0
        if self.label_manager.has_regions:
            loss = DC_and_BCE_loss({},
                                   {'batch_dice': self.configuration_manager.batch_dice,
                                    'do_bg': True, 'smooth': 0, 'ddp': self.is_ddp},
                                   use_ignore_label=self.label_manager.ignore_label is not None,
                                   dice_class=MemoryEfficientSoftDiceLoss)
        else:
            loss = DC_and_CE_loss({'batch_dice': self.configuration_manager.batch_dice,
                                   'smooth': 0, 'do_bg': False, 'ddp': self.is_ddp}, {}, weight_ce=1, weight_dice=1,
                                  ignore_label=self.label_manager.ignore_label,
                                  dice_class=MemoryEfficientSoftDiceLoss)

        deep_supervision_scales = self._get_deep_supervision_scales()

        # we give each output a weight which decreases exponentially (division by 2) as the resolution decreases
        # this gives higher resolution outputs more weight in the loss
        weights = np.array([1 / (2 ** i) for i in range(len(deep_supervision_scales))])

        # we don't use the lowest 2 outputs. Normalize weights so that they sum to 1
        weights = weights / weights.sum()
        # now wrap the loss
        loss = DeepSupervisionWrapper(loss, weights)
        return loss


class nnUNetTrainerDA5_betterIgnoreSampling(nnUNetTrainerDA5):
    def get_plain_dataloaders(self, initial_patch_size: Tuple[int, ...], dim: int):
        dataset_tr, dataset_val = self.get_tr_and_val_datasets()

        if dim == 2:
            dl_tr = nnUNetDataLoader2DBetterIgnSampling(dataset_tr,
                                                        self.batch_size,
                                                        initial_patch_size,
                                                        self.configuration_manager.patch_size,
                                                        self.label_manager,
                                                        oversample_foreground_percent=self.oversample_foreground_percent,
                                                        sampling_probabilities=None, pad_sides=None)
            dl_val = nnUNetDataLoader2DBetterIgnSampling(dataset_val,
                                                         self.batch_size,
                                                         self.configuration_manager.patch_size,
                                                         self.configuration_manager.patch_size,
                                                         self.label_manager,
                                                         oversample_foreground_percent=self.oversample_foreground_percent,
                                                         sampling_probabilities=None, pad_sides=None)
        else:
            dl_tr = nnUNetDataLoader3DBetterIgnSampling(dataset_tr,
                                                        self.batch_size,
                                                        initial_patch_size,
                                                        self.configuration_manager.patch_size,
                                                        self.label_manager,
                                                        oversample_foreground_percent=self.oversample_foreground_percent,
                                                        sampling_probabilities=None, pad_sides=None)
            dl_val = nnUNetDataLoader3DBetterIgnSampling(dataset_val,
                                                         self.batch_size,
                                                         self.configuration_manager.patch_size,
                                                         self.configuration_manager.patch_size,
                                                         self.label_manager,
                                                         oversample_foreground_percent=self.oversample_foreground_percent,
                                                         sampling_probabilities=None, pad_sides=None)
        return dl_tr, dl_val


class nnUNetTrainerDA5ord0_betterIgnoreSampling(nnUNetTrainerDA5ord0):
    def get_plain_dataloaders(self, initial_patch_size: Tuple[int, ...], dim: int):
        dataset_tr, dataset_val = self.get_tr_and_val_datasets()

        if dim == 2:
            dl_tr = nnUNetDataLoader2DBetterIgnSampling(dataset_tr,
                                                        self.batch_size,
                                                        initial_patch_size,
                                                        self.configuration_manager.patch_size,
                                                        self.label_manager,
                                                        oversample_foreground_percent=self.oversample_foreground_percent,
                                                        sampling_probabilities=None, pad_sides=None)
            dl_val = nnUNetDataLoader2DBetterIgnSampling(dataset_val,
                                                         self.batch_size,
                                                         self.configuration_manager.patch_size,
                                                         self.configuration_manager.patch_size,
                                                         self.label_manager,
                                                         oversample_foreground_percent=self.oversample_foreground_percent,
                                                         sampling_probabilities=None, pad_sides=None)
        else:
            dl_tr = nnUNetDataLoader3DBetterIgnSampling(dataset_tr,
                                                        self.batch_size,
                                                        initial_patch_size,
                                                        self.configuration_manager.patch_size,
                                                        self.label_manager,
                                                        oversample_foreground_percent=self.oversample_foreground_percent,
                                                        sampling_probabilities=None, pad_sides=None)
            dl_val = nnUNetDataLoader3DBetterIgnSampling(dataset_val,
                                                         self.batch_size,
                                                         self.configuration_manager.patch_size,
                                                         self.configuration_manager.patch_size,
                                                         self.label_manager,
                                                         oversample_foreground_percent=self.oversample_foreground_percent,
                                                         sampling_probabilities=None, pad_sides=None)
        return dl_tr, dl_val


class nnUNetTrainer_betterIgnoreSampling_10epochs(nnUNetTrainer_betterIgnoreSampling):
    def __init__(self, plans: dict, configuration: str, fold: int, dataset_json: dict, unpack_dataset: bool = True,
                 device: torch.device = torch.device('cuda')):
        """used for debugging plans etc"""
        super().__init__(plans, configuration, fold, dataset_json, unpack_dataset, device)
        self.num_epochs = 10


class nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss(nnUNetTrainer_betterIgnoreSampling):
    def __init__(self, plans: dict, configuration: str, fold: int, dataset_json: dict, unpack_dataset: bool = True,
                 device: torch.device = torch.device('cuda')):
        super().__init__(plans, configuration, fold, dataset_json, unpack_dataset, device)
        self.early_stopping_enabled = self._parse_bool_env('NNUNET_EARLY_STOP_ENABLED', True)
        self.early_stopping_patience = self._parse_int_env('NNUNET_EARLY_STOP_PATIENCE', 20, min_value=1)
        self.early_stopping_min_delta = self._parse_float_env('NNUNET_EARLY_STOP_MIN_DELTA', 0.001, min_value=0.0)

        self._best_val_loss = None
        self._epochs_without_improvement = 0
        self._stop_training_early = False

    @staticmethod
    def _parse_bool_env(var_name: str, default_value: bool) -> bool:
        raw = os.environ.get(var_name)
        if raw is None:
            return default_value
        value = raw.strip().lower()
        if value in {'1', 'true', 'yes', 'y', 'on'}:
            return True
        if value in {'0', 'false', 'no', 'n', 'off'}:
            return False
        return default_value

    @staticmethod
    def _parse_int_env(var_name: str, default_value: int, min_value: int = None) -> int:
        raw = os.environ.get(var_name)
        if raw is None:
            return default_value
        try:
            parsed = int(raw)
        except ValueError:
            return default_value
        if min_value is not None:
            parsed = max(min_value, parsed)
        return parsed

    @staticmethod
    def _parse_float_env(var_name: str, default_value: float, min_value: float = None) -> float:
        raw = os.environ.get(var_name)
        if raw is None:
            return default_value
        try:
            parsed = float(raw)
        except ValueError:
            return default_value
        if min_value is not None:
            parsed = max(min_value, parsed)
        return parsed

    def on_train_start(self):
        super().on_train_start()
        self.print_to_log_file(
            f'Early stopping config | enabled={self.early_stopping_enabled} | '
            f'patience={self.early_stopping_patience} | min_delta={self.early_stopping_min_delta}'
        )

    def on_epoch_end(self):
        super().on_epoch_end()

        if not self.early_stopping_enabled:
            return

        current_val_loss = float(self.logger.my_fantastic_logging['val_losses'][-1])

        if self._best_val_loss is None:
            self._best_val_loss = current_val_loss
            self._epochs_without_improvement = 0
            self.print_to_log_file(
                f'Early stopping: baseline val_loss={np.round(current_val_loss, decimals=6)}'
            )
            return

        improvement = self._best_val_loss - current_val_loss
        if improvement > self.early_stopping_min_delta:
            self._best_val_loss = current_val_loss
            self._epochs_without_improvement = 0
            self.print_to_log_file(
                f'Early stopping: improvement detected | '
                f'val_loss={np.round(current_val_loss, decimals=6)} | '
                f'delta={np.round(improvement, decimals=6)}'
            )
            return

        self._epochs_without_improvement += 1
        self.print_to_log_file(
            f'Early stopping: no significant improvement | '
            f'val_loss={np.round(current_val_loss, decimals=6)} | '
            f'best_val_loss={np.round(self._best_val_loss, decimals=6)} | '
            f'delta={np.round(improvement, decimals=6)} | '
            f'wait={self._epochs_without_improvement}/{self.early_stopping_patience}'
        )

        if self._epochs_without_improvement >= self.early_stopping_patience:
            self._stop_training_early = True
            self.print_to_log_file(
                f'Early stopping triggered at epoch {self.current_epoch} | '
                f'best_val_loss={np.round(self._best_val_loss, decimals=6)}'
            )

    def run_training(self):
        self.on_train_start()

        for epoch in range(self.current_epoch, self.num_epochs):
            self.on_epoch_start()

            self.on_train_epoch_start()
            train_outputs = []
            for batch_id in range(self.num_iterations_per_epoch):
                train_outputs.append(self.train_step(next(self.dataloader_train)))
            self.on_train_epoch_end(train_outputs)

            with torch.no_grad():
                self.on_validation_epoch_start()
                val_outputs = []
                for batch_id in range(self.num_val_iterations_per_epoch):
                    val_outputs.append(self.validation_step(next(self.dataloader_val)))
                self.on_validation_epoch_end(val_outputs)

            self.on_epoch_end()
            if self._stop_training_early:
                break

        self.on_train_end()


class nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr(
        nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss):
    """
    Fine-tuning variant with lower initial LR and explicit per-epoch mean Dice logging.

    LR change:
      Original (nnUNet default):  initial_lr = 1e-2
      This class:                 initial_lr = 2e-3  (5x reduction)

    Dice logging fix:
      Base class logs 'Pseudo dice [per-class list]' every epoch but the
      'Yayy! New best EMA pseudo Dice' summary only appears on improvement epochs.
      This class additionally logs 'mean_dice_computed <float>' every epoch,
      computed as the mean of non-NaN values in the per-class list.
    """

    def __init__(self, plans: dict, configuration: str, fold: int,
                 dataset_json: dict, unpack_dataset: bool = True,
                 device: torch.device = torch.device('cuda')):
        super().__init__(plans, configuration, fold, dataset_json,
                         unpack_dataset, device)
        # Original LR: 1e-2 (nnUNet default for nnUNetTrainer)
        # New LR: 2e-3 (5x reduction for continued fine-tuning stability)
        self.initial_lr = 2e-3

    def on_epoch_end(self):
        super().on_epoch_end()
        try:
            pseudo_dice_history = self.logger.my_fantastic_logging.get('pseudo_dice', [])
            if pseudo_dice_history:
                arr = np.array(pseudo_dice_history[-1], dtype=float)
                valid = arr[~np.isnan(arr)]
                mean_d = float(np.mean(valid)) if len(valid) > 0 else float('nan')
            else:
                mean_d = float('nan')
            self.print_to_log_file(f'mean_dice_computed {mean_d:.6f}')
        except Exception as e:
            self.print_to_log_file(f'mean_dice_computed ERROR: {e}')
