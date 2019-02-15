# ===========
#  Libraries
# ===========
import os
import sys

import numpy as np
import tensorflow as tf

import modules.loss as loss
from modules.args import args
from modules.size import Size
from modules.train import Train
from modules.validation import Validation


# ===================
#  Class Declaration
# ===================
class Model(object):
    def __init__(self, data):
        selected_loss = args.loss
        selected_px = args.px

        self.input_size = Size(228, 304, 3)
        self.output_size = Size(128, 160, 1)

        model_index = 0
        self.model_collection = ['model_' + str(model_index)]

        self.train = None
        self.valid = None

        self.loss_name = ''
        self.train_step = None
        self.summary_writer = None
        self.summary_op = None
        self.tf_summary_train_loss = None
        self.train_saver = None

        # Invoke Methods
        self.build_model(data)
        self.build_losses(selected_loss, selected_px)
        self.build_optimizer()
        self.build_summaries()
        self.count_params()

    def build_model(self, data):
        print("\n[Network/Model] Build Network Model...")

        # =============================================
        #  FCRN (Fully Convolutional Residual Network)
        # =============================================
        # Construct the network graphs
        with tf.variable_scope("model"):
            self.train = Train(data, self.input_size, self.output_size)

        with tf.variable_scope("model", reuse=True):
            self.valid = Validation(self.input_size, self.output_size, data.dataset.max_depth,
                                    data.dataset.name)

    def build_losses(self, selected_loss, selected_px):
        valid_pixels = True if selected_px == 'valid' else False

        with tf.name_scope("Losses"):
            # Select Loss Function:
            if selected_loss == 'mse':
                self.loss_name, self.train.tf_loss = loss.tf_L_MSE(self.train.tf_pred,
                                                                   self.train.tf_batch_depth,
                                                                   valid_pixels)

                _, self.valid.tf_loss = loss.tf_L_MSE(self.valid.tf_pred,
                                                      self.valid.tf_depth_resized,
                                                      valid_pixels)

            elif selected_loss == 'berhu':
                self.loss_name, self.train.tf_loss = loss.tf_BerHu(self.train.tf_pred,
                                                                   self.train.tf_batch_depth,
                                                                   valid_pixels)

                _, self.valid.tf_loss = loss.tf_BerHu(self.valid.tf_pred,
                                                      self.valid.tf_depth_resized,
                                                      valid_pixels)

            elif selected_loss == 'eigen':
                self.loss_name, self.train.tf_loss = loss.tf_L_eigen(self.train.tf_pred,
                                                                     self.train.tf_batch_depth,
                                                                     valid_pixels,
                                                                     gamma=0.5)

                _, self.valid.tf_loss = loss.tf_L_eigen(self.valid.tf_pred,
                                                        self.valid.tf_depth_resized,
                                                        valid_pixels,
                                                        gamma=0.5)

            elif selected_loss == 'eigen_grads':
                self.loss_name, self.train.tf_loss = loss.tf_L_eigen_grads(self.train.tf_pred,
                                                                           self.train.tf_batch_depth,
                                                                           valid_pixels,
                                                                           gamma=0.5)

                _, self.valid.tf_loss = loss.tf_L_eigen_grads(self.valid.tf_pred,
                                                              self.valid.tf_depth_resized,
                                                              valid_pixels,
                                                              gamma=0.5)
            else:
                print("[Network/Loss] Invalid Loss Function Selected!")
                sys.exit()

            if args.l2norm:
                self.train.tf_loss += loss.calculateL2norm()

            if valid_pixels:
                print("[Network/Loss] Compute: Ignore invalid pixels")
            else:
                print("[Network/Loss] Loss: All Pixels")
            print("[Network/Loss] Loss Function: %s" % self.loss_name)

    def build_optimizer(self):
        with tf.name_scope("Optimizer"):
            def optimizer_selector(argument, tf_learning_rate):
                switcher = {
                    1: tf.train.GradientDescentOptimizer(tf_learning_rate),
                    2: tf.train.AdamOptimizer(tf_learning_rate),
                    3: tf.train.MomentumOptimizer(tf_learning_rate, momentum=0.9, use_nesterov=True),
                    4: tf.train.AdadeltaOptimizer(tf_learning_rate),
                    5: tf.train.RMSPropOptimizer(tf_learning_rate),
                }

                return switcher.get(argument, "Invalid optimizer")

            # Select Optimizer:
            optimizer = optimizer_selector(2, self.train.tf_learning_rate)

            self.train_step = optimizer.minimize(self.train.tf_loss, global_step=self.train.tf_global_step)
            tf.add_to_collection("train_step", self.train_step)

    def build_summaries(self):
        # Filling Summary Obj
        with tf.name_scope("Train"):
            tf.summary.scalar('learning_rate', self.train.tf_learning_rate, collections=self.model_collection)
            self.tf_summary_train_loss = tf.summary.scalar('loss', self.train.tf_loss, collections=self.model_collection)

            tf.summary.image('input/batch_image', self.train.tf_batch_image, max_outputs=1, collections=self.model_collection)
            # tf.summary.image('input/batch_image_uint8', self.train.tf_batch_image_uint8, max_outputs=1, collections=self.model_collection)
            tf.summary.image('input/batch_depth', self.train.tf_batch_depth, max_outputs=1, collections=self.model_collection)

            tf.summary.image('output/batch_pred', self.train.tf_pred, max_outputs=1, collections=self.model_collection)

        with tf.name_scope("Valid"):
            tf.summary.scalar('loss', self.valid.tf_loss, collections=self.model_collection)

            tf.summary.image('input/image', tf.expand_dims(self.valid.tf_image, axis=0), max_outputs=1, collections=self.model_collection)
            tf.summary.image('input/depth', tf.expand_dims(self.valid.tf_depth, axis=0), max_outputs=1, collections=self.model_collection)
            tf.summary.image('input/image_resized', tf.expand_dims(self.valid.tf_image_resized, axis=0), max_outputs=1, collections=self.model_collection)
            tf.summary.image('input/depth_resized', tf.expand_dims(self.valid.tf_depth_resized, axis=0), max_outputs=1, collections=self.model_collection)

            tf.summary.image('output/pred', self.valid.fcrn.get_output(), max_outputs=1, collections=self.model_collection)

    @staticmethod
    def count_params():
        # Count Params
        total_num_parameters = 0
        for variable in tf.trainable_variables():
            total_num_parameters += np.array(variable.get_shape().as_list()).prod()
        print("[Network/Model] Number of trainable parameters: {}".format(total_num_parameters))

    def collect_summaries(self, save_path, graph):
        with tf.name_scope("Summaries"):
            # Summary Objects
            self.summary_writer = tf.summary.FileWriter(save_path + args.log_directory, graph)  # TODO: atrelar este log_directory com a classe settings
            self.summary_op = tf.summary.merge_all('model_0')

    def create_train_saver(self):
        """Creates Saver Object."""
        self.train_saver = tf.train.Saver()

    @staticmethod
    def save_trained_model(save_path, session, saver, model_name):
        """Creates saver obj which backups all the variables."""
        print("[Network/Training] List of Saved Variables:")
        for i in tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES):
            print(i)  # i.name if you want just a name

        file_path = saver.save(session, os.path.join(save_path, "model." + model_name))
        print("\n[Results] Model saved in file: %s" % file_path)

    # TODO: Acho que não preciso das variaveis root_path blabla
    def save_results(self, datetime, epoch, max_epochs, step, max_steps, sim_train):
        """Logs the obtained simulation results."""
        root_path = os.path.abspath(os.path.join(__file__, "../.."))
        relative_path = 'results.txt'
        save_file_path = os.path.join(root_path, relative_path)

        print("[Results] Logging simulation info to '%s' file..." % relative_path)

        f = open(save_file_path, 'a')
        f.write("%s\t\t%s\t\t%s\t\t%s\t\tepoch: %d/%d\t\tstep: %d/%d\ttrain_loss: %f\tvalid_loss: %f\tt: %f s\n" % (
            datetime, args.model_name, args.dataset, self.loss_name, epoch, max_epochs, step, max_steps,
            self.train.loss, self.valid.loss,
            sim_train))
        f.close()
