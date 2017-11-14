import SimpleITK as sitk
import tensorflow as tf
import os

from dltk.io.augmentation import *
from dltk.io.preprocessing import *


def read_fn(file_references, mode, params=None):
    """A custom python read function for interfacing with nii image files.
    
    Args:
        file_references (list): A list of lists containing file references, such as [['id_0', 'image_filename_0', target_value_0], ..., ['id_N', 'image_filename_N', target_value_N]].
        mode (str): One of the tf.estimator.ModeKeys strings: TRAIN, EVAL or PREDICT.
        params (dict, optional): A dictionary to parameterise read_fn ouputs (e.g. reader_params = {'n_examples': 10, 'example_size': [64, 64, 64], 'extract_examples': True}, etc.).
    
    Yields:
        dict: A dictionary of reader outputs for dltk.io.abstract_reader. 
    """
    
    def _augment(img):
        """An image augmentation function. 
        
        Args:
            img (np.array): Input image to be augmented. 
        
        Returns:
            np.array: The augmented image.
        """

        return flip(img, axis=2)

    for f in file_references:
        subject_id = f[0]
        
        data_path = '../../../data/IXI_HH/2mm'
        
        # Read the image nii with sitk
        t1_fn = os.path.join(data_path, '{}/T1_2mm.nii.gz'.format(subject_id))
        t1 = sitk.GetArrayFromImage(sitk.ReadImage(t1_fn))

        # Normalise volume image
        t1 = whitening(t1)
        
        images = np.expand_dims(t1, axis=-1).astype(np.float32)

        
        if mode == tf.estimator.ModeKeys.PREDICT:
            yield {'features': {'x': images}}

        # Parse the sex classes from the file_references [1,2] and shift them to [0,1]
        sex = np.int(f[1]) - 1
        y = np.expand_dims(sex, axis=-1).astype(np.int32)
        
        # Augment if used in training mode
        if mode == tf.estimator.ModeKeys.TRAIN:
            images = _augment(images)
        
        # Check if the reader is supposed to return training examples or full images
        if params['extract_examples']:
            images = extract_random_example_array(images, example_size=params['example_size'],
                                                  n_examples=params['n_examples'])
            
            for e in range(params['n_examples']):
                yield {'features': {'x': images[e].astype(np.float32)}, 'labels': {'y': y.astype(np.int32)}}
                       
        else:
            yield {'features': {'x': images}, 'labels': {'y': y.astype(np.int32)}}

    return