"""Summary
"""
from __future__ import division
from __future__ import absolute_import
from __future__ import print_function

import tensorflow as tf
import numpy as np


def simple_super_resolution_3D(inputs, num_convolutions=1, filters=(16, 32, 64), upsampling_factor=(2,2,2),
                    mode=tf.estimator.ModeKeys.EVAL, use_bias=False, name='conv_autoencoder_3D',
                    kernel_initializer=tf.uniform_unit_scaling_initializer(), bias_initializer=tf.zeros_initializer(),
                    kernel_regularizer=None, bias_regularizer=None):
    """Convolutional autoencoder with num_convolutions on len(filters) resolution scales. Downsampling features is done via strided convolutions. 
    
    Args:
        inputs (TYPE): Description
        num_convolutions (int, optional): Description
        filters (tuple, optional): Description
        upsampling_factor(tuple, optional): Description
        mode (TYPE, optional): Description
        name (str, optional): Description
    
    Returns:
        TYPE: Description
    """

    outputs = {}
    assert len(inputs.get_shape().as_list()) == 5, 'inputs are required to have a rank of 5.'
    assert len(upsampling_factor) == 3, 'upsampling factor is required to be of length 3.' 

    conv_op = tf.layers.conv3d
    tp_conv_op = tf.layers.conv3d_transpose
    relu_op = tf.nn.relu6
    
    conv_params = {'padding' : 'same',
                  'use_bias' : use_bias,
                  'kernel_initializer' : kernel_initializer,
                  'bias_initializer' : bias_initializer,
                  'kernel_regularizer' : kernel_regularizer,
                  'bias_regularizer' : bias_regularizer}

    x = inputs
    tf.logging.info('Input tensor shape {}'.format(x.get_shape()))

    # Convolutional feature encoding blocks with num_convolutions at different resolution scales res_scales
    for unit in range(0, len(filters)):
        for i in range(0, num_convolutions):
            with tf.variable_scope('enc_unit_{}_{}'.format(unit, i)):
                x = conv_op(x, filters[unit], (3, 3, 3), (1, 1, 1), **conv_params)
                x = tf.layers.batch_normalization(x, training=mode==tf.estimator.ModeKeys.TRAIN)
                x = relu_op(x)       
                tf.logging.info('Encoder at unit_{}_{} tensor shape: {}'.format(unit, i, x.get_shape()))
            
    # Upsampling
    with tf.variable_scope('upsampling_unit'):
        
        # Adjust the strided tp conv kernel size to prevent losing information
        k_size = [u * 2 for u in upsampling_factor]
        x = tp_conv_op(x, inputs.get_shape().as_list()[-1], k_size, upsampling_factor, **conv_params)
    
    tf.logging.info('Output tensor shape: {}'.format(x.get_shape()))
    outputs['x_'] = x
    
    return outputs