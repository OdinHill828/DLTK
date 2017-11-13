# -*- coding: utf-8 -*-
#from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from builtins import input

import argparse
import os
import sys

import numpy as np
import pandas as pd
import tensorflow as tf

from dltk.core.metrics import *
from dltk.core.losses import *
from dltk.models.regression_classification.resnet import resnet_3D
from dltk.io.abstract_reader import Reader
from reader import read_fn

# PARAMS
EVAL_EVERY_N_STEPS = 100
EVAL_STEPS = 5

NUM_CLASSES = 1
NUM_CHANNELS = 1

NUM_FEATURES_IN_SUMMARIES = min(4, NUM_CHANNELS)

BATCH_SIZE = 8
SHUFFLE_CACHE_SIZE = 32

MAX_STEPS = 100000


# MODEL
def model_fn(features, labels, mode, params):
    """Summary
    
    Args:
        features (TYPE): Description
        labels (TYPE): Description
        mode (TYPE): Description
        params (TYPE): Description
    
    Returns:
        TYPE: Description
    """

    # 1. create a model and its outputs
    net_output_ops = resnet_3D(features['x'], num_res_units=2, num_classes=NUM_CLASSES, 
                              filters=(16, 32, 64, 128, 256, 512),
                              strides=((1, 1, 1), (2, 2, 2), (2, 2, 2), (2, 2, 2), (2, 2, 2), (4, 6, 6)), 
                              mode=mode, kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-4))
    
    # 1.1 Generate predictions only (for `ModeKeys.PREDICT`)
    if mode == tf.estimator.ModeKeys.PREDICT:
        return tf.estimator.EstimatorSpec(mode=mode, predictions=net_output_ops,
                                          export_outputs={'out': tf.estimator.export.PredictOutput(net_output_ops)})
    # 2. set up a loss function
    loss = tf.losses.mean_squared_error(labels=labels['y'], predictions=net_output_ops['logits'])
    
    # 3. define a training op and ops for updating moving averages (i.e. for batch normalisation)  
    global_step = tf.train.get_global_step()
    optimiser = tf.train.AdamOptimizer(learning_rate=params["learning_rate"], epsilon=1e-5)
      
    update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
    with tf.control_dependencies(update_ops):
        train_op = optimiser.minimize(loss, global_step=global_step)
    
    # 4.1 (optional) create custom image summaries for tensorboard
    my_image_summaries = {}
    my_image_summaries['feat_t1'] = features['x'][0,32,:,:,0]
        
    expected_output_size = [1, 96, 96, 1] # [B, W, H, C]
    [tf.summary.image(name, tf.reshape(image, expected_output_size)) for name, image in my_image_summaries.items()]
    
    # 4.2 (optional) track the rmse (scaled back by 100, see reader.py)
    eval_metric_ops = {"rmse": tf.metrics.root_mean_squared_error(labels['y'], net_output_ops['logits']),
                      "mae": tf.metrics.mean_absolute_error(labels['y'], net_output_ops['logits'])}
    
    # 5. Return EstimatorSpec object
    return tf.estimator.EstimatorSpec(mode=mode, predictions=net_output_ops, loss=loss, train_op=train_op, eval_metric_ops=eval_metric_ops)


def train(args):

    np.random.seed(42)
    tf.set_random_seed(42)

    print('Setting up...')

    # Parse csv files for file names
    all_filenames = pd.read_csv(args.data_csv, dtype=object, keep_default_na=False, na_values=[]).as_matrix()
    
    train_filenames = all_filenames[:150]
    val_filenames = all_filenames[150:]
    
    # Set up a data reader to handle the file i/o. 
    reader_params = {'n_examples': 2, 'example_size': [64, 96, 96], 'extract_examples': True}
    reader_example_shapes = {'features': {'x': reader_params['example_size'] + [NUM_CHANNELS,]},
                             'labels': {'y': [1]}}
    reader = Reader(read_fn, {'features': {'x': tf.float32}, 'labels': {'y': tf.float32}})

    # Get input functions and queue initialisation hooks for training and validation data
    train_input_fn, train_qinit_hook = reader.get_inputs(train_filenames, 
                                                         tf.estimator.ModeKeys.TRAIN,
                                                         example_shapes=reader_example_shapes,
                                                         batch_size=BATCH_SIZE,
                                                         shuffle_cache_size=SHUFFLE_CACHE_SIZE,
                                                         params=reader_params)
    
    val_input_fn, val_qinit_hook = reader.get_inputs(val_filenames, 
                                                     tf.estimator.ModeKeys.EVAL,
                                                     example_shapes=reader_example_shapes, 
                                                     batch_size=BATCH_SIZE,
                                                     shuffle_cache_size=min(SHUFFLE_CACHE_SIZE, EVAL_STEPS),
                                                     params=reader_params)
    
    # Instantiate the neural network estimator
    nn = tf.estimator.Estimator(model_fn=model_fn,
                                model_dir=args.save_path,
                                params={"learning_rate": 0.001}, 
                                config=tf.estimator.RunConfig())
    
    # Hooks for validation summaries
    val_summary_hook  = tf.contrib.training.SummaryAtEndHook(os.path.join(args.save_path, 'eval'))
    step_cnt_hook = tf.train.StepCounterHook(every_n_steps=EVAL_EVERY_N_STEPS, output_dir=args.save_path)
    
    print('Starting training...')
    try:
        while True: 
            nn.train(input_fn=train_input_fn, hooks=[train_qinit_hook, step_cnt_hook], steps=EVAL_EVERY_N_STEPS)
            
            if args.run_validation:
                results_val = nn.evaluate(input_fn=val_input_fn, hooks=[val_qinit_hook, val_summary_hook], steps=EVAL_STEPS)
                print('Step = {}; val loss = {:.5f};'.format(results_val['global_step'], results_val['loss']))

    except KeyboardInterrupt:
        print('Stopping now.')
        export_dir = nn.export_savedmodel(export_dir_base=args.save_path,
            serving_input_receiver_fn=reader.serving_input_receiver_fn(reader_example_shapes))
        print('Model saved to {}.'.format(export_dir))
        
        
if __name__ == '__main__':

    # Set up argument parser
    parser = argparse.ArgumentParser(description='Example: IXI HH resnet regression training script')
    parser.add_argument('--run_validation', default=True)
    parser.add_argument('--resume', default=False, action='store_true')
    parser.add_argument('--verbose', default=False, action='store_true')
    parser.add_argument('--cuda_devices', '-c', default='0')
    
    parser.add_argument('--save_path', '-p', default='/tmp/IXI_regression/')
    parser.add_argument('--data_csv', default='../../../data/IXI_HH/demographic_HH.csv')
    
    args = parser.parse_args()
        
    # Set verbosity
    if args.verbose:
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1'
        tf.logging.set_verbosity(tf.logging.INFO)
    else:
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
        tf.logging.set_verbosity(tf.logging.ERROR)

    # GPU allocation options
    os.environ["CUDA_VISIBLE_DEVICES"] = args.cuda_devices
    
    # Create model save path
    os.system("rm -rf %s" % args.save_path)
    os.system("mkdir -p %s" % args.save_path)

    # Call training
    train(args)