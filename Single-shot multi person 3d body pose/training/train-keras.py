import math
import os
import re
import sys
import pandas
from functools import partial

import keras.backend as K
from keras.applications.resnet50 import ResNet50
from keras.callbacks import LearningRateScheduler, ModelCheckpoint, CSVLogger, TensorBoard
from keras.layers.convolutional import Conv2D

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from model.cmu_model import get_training_model
from training.optimizers import MultiSGD
from training.dataset import get_dataflow, batch_dataflow

batch_size = 8
base_lr = 4e-5 # 2e-5
momentum = 0.9
weight_decay = 5e-4
lr_policy =  "step"
gamma = 0.333
stepsize = 136106 #68053   // after each stepsize iterations update learning rate: lr=lr*gamma
max_iter = 200000 # 600000

weights_best_file = "weights.best.h5"
training_log = "training.csv"
logs_dir = "./logs"
from_resnet = {
    'conv1_1': 'conv1',
    'conv1_2': 'res2a_branch2a',
    'conv2_1': 'res2a_branch2b',
    'conv2_2': 'res2a_branch2c',
    'conv3_1': 'res2a_branch1',
    'conv3_2': 'res2b_branch2a',
    'conv3_3': 'res2b_branch2b',
    'conv3_4': 'res2b_branch2c',
    'conv4_1': 'res2c_branch2a',
    'conv4_2': 'res2c_branch2b',
    'conv5': 'res2c_branch2c',
    'conv6': 'res3a_branch2a',
    'conv7': 'res3a_branch2b',
    'conv8': 'res3a_branch2c',
    'conv9': 'res3a_branch1',
    'conv10': 'res3b_branch2a',
    'conv11': 'res3b_branch2b',
    'conv12': 'res3b_branch2c',
    'conv13': 'res3c_branch2a',
    'conv14': 'res3c_branch2b',
    'conv15': 'res3c_branch2c',
    'conv16': 'res3d_branch2a',
    'conv17': 'res3d_branch2b',
    'conv18': 'res3d_branch2c',
    'conv19': 'res4a_branch2a',
    'conv20': 'res4a_branch2b',
    'conv21': 'res4a_branch2c',
    'conv22': 'res4a_branch1',
    'conv23': 'res4b_branch2a',
    'conv24': 'res4b_branch2b',
    'conv25': 'res4b_branch2c',
    'conv26': 'res4c_branch2a',
    'conv27': 'res4c_branch2b',
    'conv28': 'res4c_branch2c',
    'conv29': 'res4d_branch2a',
    'conv30': 'res4d_branch2b',
    'conv31': 'res4d_branch2c',
    'conv32': 'res4e_branch2a',
    'conv33': 'res4e_branch2b',
    'conv34': 'res4e_branch2c',
    'conv35': 'res4f_branch2a',
    'conv36': 'res4f_branch2b',
    'conv37': 'res4f_branch2c'
    
    
}

def get_last_epoch():
    """
    Retrieves last epoch from log file updated during training.
    :return: epoch number
    """
    data = pandas.read_csv(training_log)
    return max(data['epoch'].values)

def restore_weights(weights_best_file, model):
    """
    Restores weights from the checkpoint file if exists or
    preloads the first layers with VGG19 weights
    :param weights_best_file:
    :return: epoch number to use to continue training. last epoch + 1 or 0
    """
    # load previous weights or vgg19 if this is the first run
    if os.path.exists(weights_best_file):
        print("Loading the best weights...")

        model.load_weights(weights_best_file)

        return get_last_epoch() + 1
    else:
        print("Loading model1 weights...")

        resnet_model = ResNet50(weights='imagenet',include_top=False)

        for layer in model.layers:
            if layer.name in from_resnet.values():
                resnet_layer_name = from_resnet[layer.name]
                layer.set_weights(resnet_model.get_layer(resnet_layer_name).get_weights())
                print("Loaded Resnet layer: " + resnet_layer_name)

        return 0


if __name__ == '__main__':
    # get the model
    model1,model2 = get_training_model(weight_decay)
    #Branch1 to be trained on coco-----------------------------------------------
    
    #restore weights

    last_epoch = restore_weights(weights_best_file, model1)

    # prepare generators

    curr_dir = os.path.dirname(__file__)
    annot_path = os.path.join(curr_dir, '../dataset/annotations/person_keypoints_train2017.json')
    img_dir = os.path.abspath(os.path.join(curr_dir, '../dataset/train2017/'))

    # get dataflow of samples

    df = get_dataflow(
        annot_path=annot_path,
        img_dir=img_dir)
    train_samples = df.size()
    # get generator of batches

    batch_df = batch_dataflow(df, batch_size)
    train_gen = gen(batch_df)

    
    