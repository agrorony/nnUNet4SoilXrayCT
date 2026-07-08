from micro_sam.util import get_sam_model
import numpy as np
pred = get_sam_model(model_type='vit_b')
img = (np.random.rand(64, 64, 3) * 255).astype(np.uint8)
pred.set_image(img)
print('original_size:', pred.original_size)
print('input_size:', pred.input_size)
print('features shape:', pred.features.shape)
print('is_image_set:', pred.is_image_set)
# test predict with box
box = np.array([[5, 5, 50, 50]], dtype=np.float32)
masks, scores, logits = pred.predict(box=box, multimask_output=False)
print('mask shape:', masks.shape, 'dtype:', masks.dtype)
