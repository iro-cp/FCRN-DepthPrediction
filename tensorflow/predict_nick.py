#!/usr/bin/python3
# -*- coding: utf-8 -*-

# ============
#  To-Do FCRN
# ============
# TODO: Dar suporte a outros Datasets
# TODO: Validar Métricas.

# TODO: Implementar Bilinear
# TODO: Estou aplicando a normalização da entrada em todos os módulos (predict, test, train, valid)?
# FIXME: Qualidade dos labels de treinamento menos discretizado que os labels de validação

# ===========
#  Libraries
# ===========
import os
import warnings
import time
import sys
import pyxhook

import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt

import modules.metrics as metricsLib
import modules.args as argsLib

from PIL import Image
from sys import getsizeof, stderr
from itertools import chain
from collections import deque

from modules.dataset.dataloader import Dataloader
from modules.framework import Model
from modules.model.fcrn import ResNet50UpProj
from modules.size import Size
from modules.plot import Plot

# =============================
#  Framework Config - Training
# =============================
# Select the Loss Function:
# 0 - MSE
# 1 - Eigen's Log Depth
# 2 - BerHu
LOSS_FUNCTION = 1

# Select to consider only the valid Pixels (True) OR ALL Pixels (False)
VALID_PIXELS = True  # Default: True

TRAIN_ON_SINGLE_IMAGE = False  # Default: False
ENABLE_EARLY_STOP = False  # Default: True # TODO: Ativar
ENABLE_TENSORBOARD = True  # Default: True
SAVE_TRAINED_MODEL = True  # Default: True

# =============================
#  Framework Config - Testing
# =============================
# Select Subset:
# 0 - TestData      # Default
# 1 - TrainData
TEST_EVALUATE_SUBSET = 0

SAVE_TEST_DISPARITIES = True  # Default: True
APPLY_BILINEAR_OUTPUT = False  # Default: False

# ==================
#  Global Variables
# ==================
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings("ignore")  # Suppress Warnings

appName = 'fcrn'
datetime = time.strftime("%Y-%m-%d") + '_' + time.strftime("%H-%M-%S")
LOG_INITIAL_VALUE = 1

firstTime = True


# ===========
#  Functions
# ===========
def createSaveFolder():
    save_path = None
    save_restore_path = None

    if SAVE_TRAINED_MODEL or ENABLE_TENSORBOARD:
        # Saves the model variables to disk.
        relative_save_path = 'output/' + appName + '/' + datetime + '/'
        save_path = os.path.join(os.getcwd(), relative_save_path)
        save_restore_path = os.path.join(save_path, 'restore/')

        if not os.path.exists(save_restore_path):
            os.makedirs(save_restore_path)

    return save_path, save_restore_path


# This function is called every time a key is presssed
def kbevent(event):
    # print key info
    # print(event)

    # If the ascii value matches spacebar, terminate the while loop
    if event.Ascii == 27:
        global running
        running = False


# Create hookmanager
hookman = pyxhook.HookManager()
# Define our callback to fire when a key is pressed down
hookman.KeyDown = kbevent
# Hook the keyboard
hookman.HookKeyboard()
# Start our listener
hookman.start()


def total_size(o, handlers={}, verbose=False):
    """ Returns the approximate memory footprint an object and all of its contents.

    Automatically finds the contents of the following builtin containers and
    their subclasses:  tuple, list, deque, dict, set and frozenset.
    To search other containers, add handlers to iterate over their contents:

        handlers = {SomeContainerClass: iter,
                    OtherContainerClass: OtherContainerClass.get_elements}

    """
    dict_handler = lambda d: chain.from_iterable(d.items())
    all_handlers = {tuple: iter,
                    list: iter,
                    deque: iter,
                    dict: dict_handler,
                    set: iter,
                    frozenset: iter,
                   }
    all_handlers.update(handlers)     # user handlers take precedence
    seen = set()                      # track which object id's have already been seen
    default_size = getsizeof(0)       # estimate sizeof object without __sizeof__

    def sizeof(o):
        if id(o) in seen:       # do not double count the same object
            return 0
        seen.add(id(o))
        s = getsizeof(o, default_size)

        if verbose:
            print(s, type(o), repr(o), file=stderr)

        for typ, handler in all_handlers.items():
            if isinstance(o, typ):
                s += sum(map(sizeof, handler(o)))
                break
        return s

    return sizeof(o)


# ========= #
#  Predict  #
# ========= #
def predict(model_data_path, image_path):
    print('[%s] Selected mode: Predict' % appName)

    # Default input size
    height = 228
    width = 304
    channels = 3
    batch_size = 1

    # Read image
    img = Image.open(image_path)
    img = img.resize([width, height], Image.ANTIALIAS)
    img = np.array(img).astype('float32')
    img = np.expand_dims(np.asarray(img), axis=0)

    # Create a placeholder for the input image
    tf_image = tf.placeholder(tf.float32, shape=(None, height, width, channels))

    with tf.variable_scope('model'):
        # Construct the network
        net = ResNet50UpProj({'data': tf_image}, batch_size, 1, False)

        # for var in tf.trainable_variables():
        #     print(var)

    with tf.Session() as sess:
        # Load the converted parameters
        print('\n[network/Predict] Loading the model')

        # Use to load from ckpt file
        saver = tf.train.Saver()
        saver.restore(sess, model_data_path)

        # Use to load from npy file
        # net.load(model_data_path, sess)

        # Evalute the network for the given image
        pred = sess.run(net.get_output(), feed_dict={tf_image: img})

        # Plot result
        fig = plt.figure()
        ii = plt.imshow(pred[0, :, :, 0], interpolation='nearest')
        fig.colorbar(ii)
        plt.show()

        return pred


# ===================== #
#  Training/Validation  #
# ===================== #
def train(args):
    print('[%s] Selected mode: Train' % appName)

    # Local Variables
    global firstTime
    global running  # Create a loop to keep the application running
    running = True

    save_path, save_restore_path = createSaveFolder()  # TODO: Evitar criar pastas vazias

    # ----------------------------------------- #
    #  Network Training Model - Building Graph  #
    # ----------------------------------------- #
    graph = tf.Graph()
    with graph.as_default():
        data = Dataloader(args)

        # If enabled, the framework will train the network for only one image!!!
        if TRAIN_ON_SINGLE_IMAGE:
            data.train_image_filenames = tf.expand_dims(data.train_image_filenames[0], axis=0)
            data.train_depth_filenames = tf.expand_dims(data.train_depth_filenames[0], axis=0)

        data.tf_train_image, data.tf_train_depth = data.readData(data.train_image_filenames, data.train_depth_filenames)

        # Build Network Model
        model = Model(args, data, LOSS_FUNCTION, VALID_PIXELS)
        model.collectSummaries(save_path, graph)
        model.createTrainSaver()

    # ---------------------------------------- #
    #  Network Training Model - Running Graph  #
    # ---------------------------------------- #
    # Local Variables and Memory Allocation
    epoch, step = 0, 0

    with tf.Session(graph=graph) as sess:
        print("\n[Network/Training] Initializing graph's variables...")
        sess.run([tf.global_variables_initializer(), tf.local_variables_initializer()])

        # Check Dataset Integrity
        print("[Dataloader] Checking if RGB and Depth images are paired... ")

        # FIXME: Tirar checagem do código, fazer ao fazer a leitura do dataset
        # data.checkIntegrity(sess, tf_train_image_filenames, tf_train_depth_filenames, 'TrainData')
        # data.checkIntegrity(sess, tf_test_image_filenames, tf_test_depth_filenames, 'TestData')

        # Proclaim the epochs
        max_epochs = int(np.floor(args.batch_size * args.max_steps / data.numTrainSamples))
        print('\nTrain with approximately %d epochs' % max_epochs)

        # ===============
        #  Training Loop
        # ===============
        print("[Network/Training] Training Initialized!\n")
        coord = tf.train.Coordinator()
        threads = tf.train.start_queue_runners(coord=coord)

        start = time.time()
        for step in range(args.max_steps + 1):
            if running:
                start2 = time.time()

                # ----- Session Run! ----- #
                # Training
                # TODO: Create train_ops variable
                if args.show_train_progress:
                    _, batch_data_raw, batch_data, batch_labels, log_batch_labels, batch_pred, model.train.loss, summary_str = sess.run(
                        [model.train_step, model.train.tf_batch_data_resized, model.train.tf_batch_data,
                         model.train.tf_batch_labels, model.train.tf_log_batch_labels,
                         model.train.fcrn.get_output(), model.train.tf_loss, model.summary_op])
                else:
                    _, model.train.loss, summary_str = sess.run(
                        [model.train_step, model.train.tf_loss, model.summary_op])

                def debug_data_augmentation():
                    fig, axes = plt.subplots(nrows=2, ncols=2)

                    axes[0, 0].set_title('images_resized')
                    axes[0, 0].imshow(images_resized)

                    axes[0, 1].set_title('depths_resized[:, :, 0]')
                    axes[0, 1].imshow(depths_resized[:, :, 0])

                    axes[1, 0].set_title('images_proc')
                    axes[1, 0].imshow(images_proc)

                    axes[1, 1].set_title('depths_proc[:,:,0]')
                    axes[1, 1].imshow(depths_proc[:, :, 0])
                    fig.tight_layout()

                    plt.pause(0.001)
                    input("proc")

                # debug_data_augmentation()

                # Prints Training Progress
                if step % 10 == 0:
                    if args.show_train_progress:
                        model.train.plot.showResults(raw=batch_data_raw[0],
                                                     label=batch_labels[0, :, :, 0],
                                                     log_label=log_batch_labels[0, :, :, 0],
                                                     pred=batch_pred[0, :, :, 0],
                                                     cbar_range=data.datasetObj)

                    end2 = time.time()

                    print(
                        'epoch: {0:d}/{1:d} | step: {2:d}/{3:d} | t: {4:f} | Batch trLoss: {5:>16.4f} | vLoss: {6:>16.4f} '.format(
                            epoch,
                            max_epochs,
                            step,
                            args.max_steps,
                            end2 - start2,
                            model.train.loss,
                            model.valid.loss))

                # Detects the end of a epoch
                if np.floor((step * args.batch_size) / data.numTrainSamples) != epoch:
                    # Validation
                    # TODO: Create valid_ops variable
                    # TODO: Portar Leitura para o Tensorflow
                    # TODO: Implementar Leitura por Batches

                    valid_loss_sum = 0
                    print("\n[Network/Validation] Epoch finished. Starting TestData evaluation...")
                    for i in range(data.numTestSamples):
                        feed_valid = {
                            model.valid.tf_image: np.expand_dims(plt.imread(data.test_image_filenames[i]), axis=0),
                            model.valid.tf_depth: np.expand_dims(
                                np.expand_dims(plt.imread(data.test_depth_filenames[i]), axis=0), axis=3)}

                        if args.show_valid_progress:
                            valid_image, valid_pred, valid_labels, valid_log_labels, model.valid.loss = sess.run(
                                [model.valid.tf_image_resized, model.valid.fcrn.get_output(),
                                 model.valid.tf_depth_resized,
                                 model.valid.tf_log_depth_resized, model.valid.tf_loss],
                                feed_dict=feed_valid)  # FIXME: Só funciona na primeira vez

                            model.valid.plot.showResults(raw=valid_image[0, :, :],
                                                         label=valid_labels[0, :, :, 0],
                                                         log_label=valid_log_labels[0, :, :, 0],
                                                         pred=valid_pred[0, :, :, 0],
                                                         cbar_range=data.datasetObj)
                        else:
                            model.valid.loss = sess.run(model.valid.tf_loss, feed_dict=feed_valid)

                        valid_loss_sum += model.valid.loss

                        print("%d/%d\tvalid_loss_sum: %f\tvalid_loss: %f" % (
                            i, data.numTestSamples, valid_loss_sum, model.valid.loss))

                    # Calculate mean value of 'valid_loss'
                    model.valid.loss = valid_loss_sum / data.numTestSamples  # Updates 'Valid_loss' value
                    print("mean(valid_loss): %f\n" % model.valid.loss)

                    # TODO: Move
                    def plotGraph(firstTime):
                        model.train.loss_hist.append(model.train.loss)
                        model.valid.loss_hist.append(model.valid.loss)

                        plt.figure(3)
                        plt.plot(range(len(model.train.loss_hist)), model.train.loss_hist, 'b', label='Train Loss')
                        plt.plot(range(len(model.valid.loss_hist)), model.valid.loss_hist, 'r', label='Valid Loss')

                        if firstTime:
                            plt.title('Training and Validation Loss')
                            plt.xlabel('Epochs')
                            plt.ylabel('Loss')
                            plt.legend()
                            plt.draw()
                            firstTime = False
                        else:
                            plt.draw()

                    # plotGraph() # TODO: REATIVAR!!!!!!!!!!!

                    if ENABLE_EARLY_STOP:
                        if model.train.stop.check(step, model.valid.loss):  # TODO: Validar
                            break

                # Write information to TensorBoard
                if ENABLE_TENSORBOARD:
                    model.summary_writer.add_summary(summary_str, step)
                    model.summary_writer.flush()  # Don't forget this command! It makes sure Python writes the summaries to the log-file

                epoch = int(np.floor((step * args.batch_size) / data.numTrainSamples))
            else:
                print("[KeyEvent] 'ESC' Pressed! Training process aborted!")

        coord.request_stop()
        coord.join(threads)

        end = time.time()
        sim_train = end - start

        # Close the listener when we are done
        hookman.cancel()

        print("\n[Network/Training] Training FINISHED! Time elapsed: %f s\n" % sim_train)

        # ==============
        #  Save Results
        # ==============
        if SAVE_TRAINED_MODEL:
            model.saveTrainedModel(save_restore_path, sess, model.train_saver, args.model_name)

        model.saveResults(datetime, step, sim_train)


# ========= #
#  Testing  #
# ========= #
def test(args):
    print('[%s] Selected mode: Test' % appName)

    # Local Variables
    numSamples = None

    # -----------------------------------------
    #  Network Testing Model - Importing Graph
    # -----------------------------------------
    # Loads the dataset and restores a specified trained model.
    data = Dataloader(args)

    # Searches dataset images filenames
    # data.train_image_filenames, data.train_depth_filenames, tf_train_image_filenames, tf_train_depth_filenames = data.getTrainData()

    if TEST_EVALUATE_SUBSET == 0:
        _ = data.getTestData()
        numSamples = data.numTestSamples
    elif TEST_EVALUATE_SUBSET == 1:
        data.test_image_filenames, data.test_depth_filenames, tf_test_image_filenames, tf_test_depth_filenames = data.getTrainData()
        numSamples = data.numTrainSamples

    # Construct the network
    with tf.variable_scope('model'):
        input_size = Size(228, 304, 3)
        output_size = Size(128, 160, 1)
        batch_size = 1

        tf_image = tf.placeholder(tf.float32, shape=(None, input_size.height, input_size.width, input_size.nchannels))
        net = ResNet50UpProj({'data': tf_image}, batch_size, 1, False)

    with tf.Session() as sess:
        print('\n[network/Testing] Loading the model...')

        # Use to load from *.ckpt file
        saver = tf.train.Saver()
        saver.restore(sess, args.model_path)

        # Use to load from npy file
        # net.load(model_data_path, sess)

        # ==============
        #  Testing Loop
        # ==============
        if args.show_test_results:
            test_plotObj = Plot(args.mode, title='Test Predictions')

        # Memory Allocation
        image_resized = np.zeros(shape=input_size.getSize(), dtype=np.uint8)   # (228, 304, 3)
        pred = np.zeros(shape=output_size.getSize(), dtype=np.float32)      # (128, 160, 1)
        depth_resized = np.zeros(shape=output_size.getSize(), dtype=np.int32)       # (128, 160, 1)

        start = time.time()
        for i in range(data.numTestSamples):
            start2 = time.time()

            if data.test_depth_filenames:  # It's not empty
                image_resized, depth_resized = data.readImage(data.test_image_filenames[i],
                                                              data.test_depth_filenames[i],
                                                              input_size,
                                                              output_size,
                                                              mode='test',
                                                              showImages=False)
            else:
                image_resized, _ = data.readImage(data.test_image_filenames[i],
                                                  None,
                                                  input_size,
                                                  output_size,
                                                  mode='test')

            # Evalute the network for the given image
            feed_test = {tf_image: np.expand_dims(np.asarray(image_resized), axis=0)}
            pred = sess.run(net.get_output(), feed_dict=feed_test)

            # Prints Testing Progress
            end2 = time.time()
            print('step: %d/%d | t: %f' % (i + 1, numSamples, end2 - start2))
            # break # Test

            # Show Results
            test_plotObj.showTestResults(raw=image_resized,
                                         label=depth_resized[:, :, 0],
                                         log_label=np.log(depth_resized[:, :, 0] + LOG_INITIAL_VALUE),
                                         pred=pred[0, :, :, 0], i=i+1)

        # Testing Finished.
        end = time.time()
        print("\n[Network/Testing] Testing FINISHED! Time elapsed: %f s" % (end - start))

        # ==============
        #  Save Results
        # ==============
        # Saves the Test Predictions
        if SAVE_TEST_DISPARITIES:
            print("[Network/Testing] Saving testing predictions...")
            output_directory = os.path.dirname(args.model_path) if args.output_directory == '' else args.output_directory

            if not os.path.exists(output_directory):
                os.makedirs(output_directory)

            # np.save(output_directory[:-7] + 'test_pred.npy', pred)  # The indexing removes 'restore' from folder path # FIXME: Reativar

        # FIXME: Reativar
        # # Calculate Metrics
        # if data.test_depth_filenames:
        #     metricsLib.evaluateTesting(pred, test_labels_o)
        # else:
        #     print(
        #         "[Network/Testing] It's not possible to calculate Metrics. There are no corresponding labels for Testing Predictions!")

        # Close the listener when we are done
        hookman.cancel() # TODO: Não faz sentido usar no teste. Se o hookman não foi cancelado, programa pode ter problemas em desligar


# ======
#  Main
# ======
def main(args):
    print('\n[%s] Selected Params: \n\n%s\n' % (appName, args))

    if args.mode == 'train':
        train(args)
    elif args.mode == 'test':
        test(args)
    elif args.mode == 'pred':
        predict(args.model_path, args.image_path)

    print("\n[%s] Done." % appName)
    sys.exit()

if __name__ == '__main__':
    args = argsLib.argumentHandler()

    # Limits Tensorflow to see only the specified GPU.
    os.environ['CUDA_VISIBLE_DEVICES'] = args.gpu

    tf.app.run(main=main(args))
