from __future__ import division
from __future__ import absolute_import
from __future__ import print_function

import tensorflow as tf
import numpy as np


def vanilla_residual_unit_3D(inputs, out_filters, kernel_size=(3, 3, 3),
                             strides=(1, 1, 1), mode=tf.estimator.ModeKeys.EVAL, use_bias=False,
                             kernel_initializer=tf.uniform_unit_scaling_initializer(),
                             bias_initializer=tf.zeros_initializer(), kernel_regularizer=None,
                             bias_regularizer=None):
    """Implementation of a 3D residual unit according to [1]. This implementation supports strided convolutions and automatically handles different input and output filters. 

    [1] K. He et al. Identity Mappings in Deep Residual Networks. ECCV 2016.

    Args:
        inputs (tf.Tensor): Input tensor to the residual unit. Is required to have a rank of 5 (i.e. [batch, x, y, z, channels]).
        out_filters (int): Number of convolutional filters used in the sub units.
        kernel_size (tuple, optional): Size of the convoltional kernels used in the sub units
        strides (tuple, optional): Convolution strides in (x,y,z) of sub unit 0. Allows downsampling of the input tensor via strides convolutions.
        mode (str, optional): One of the tf.estimator.ModeKeys: TRAIN, EVAL or PREDICT
        use_bias (bool, optional): Train a bias with each convolution.
        kernel_initializer (TYPE, optional): Initialisation of convolution kernels
        bias_initializer (TYPE, optional): Initialisation of bias
        kernel_regularizer (None, optional): Additional regularisation op
        bias_regularizer (None, optional): Additional regularisation op

    Returns:
        tf.Tensor: Output of the residual unit
    """

    relu_op = tf.nn.relu6  # or tf.nn.relu
    pool_op = tf.layers.max_pooling3d

    conv_params = {'padding': 'same',
                   'use_bias': use_bias,
                   'kernel_initializer': kernel_initializer,
                   'bias_initializer': bias_initializer,
                   'kernel_regularizer': kernel_regularizer,
                   'bias_regularizer': bias_regularizer}

    in_filters = inputs.get_shape().as_list()[-1]
    assert in_filters == inputs.get_shape().as_list(
    )[-1], 'Module was initialised for a different input shape'

    x = inputs
    orig_x = x

    # Handle strided convolutions
    if np.prod(strides) != 1:
        orig_x = pool_op(orig_x, strides, strides, 'valid')

    # Sub unit 0
    with tf.variable_scope('sub_unit0'):

        # Adjust the strided conv kernel size to prevent losing information
        k = [s * 2 if s > 1 else k for k, s in zip(kernel_size, strides)]

        x = tf.layers.batch_normalization(
            x, training=mode == tf.estimator.ModeKeys.TRAIN)
        x = relu_op(x)
        x = tf.layers.conv3d(x, out_filters, k, strides, **conv_params)

    # Sub unit 1
    with tf.variable_scope('sub_unit1'):
        x = tf.layers.batch_normalization(
            x, training=mode == tf.estimator.ModeKeys.TRAIN)
        x = relu_op(x)
        x = tf.layers.conv3d(x, out_filters, kernel_size,
                             (1, 1, 1), **conv_params)

    # Add the residual
    with tf.variable_scope('sub_unit_add'):

        # Handle differences in input and output filter sizes
        if in_filters < out_filters:
            orig_x = tf.pad(orig_x, [[0, 0]] * (len(x.get_shape().as_list()) - 1) +
                            [[int(np.floor((out_filters - in_filters) / 2.)),
                              int(np.ceil((out_filters - in_filters) / 2.))]])
        elif in_filters > out_filters:
            orig_x = tf.layers.conv3d(
                orig_x, out_filters, kernel_size, (1, 1, 1), **conv_params)
        x += orig_x

    return x
