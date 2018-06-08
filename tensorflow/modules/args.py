# ===========
#  Libraries
# ===========
import argparse


# ===========
#  Functions
# ===========
def argumentHandler():
    # Creating Arguments Parser
    parser = argparse.ArgumentParser(
        "Train the FCRN (Fully Convolution Residual Network) Tensorflow implementation taking image files as input.")

    # Input
    parser.add_argument('--gpu', type=str, help="Select which gpu to run the code", default='0')
    parser.add_argument('-m', '--mode', type=str, help="Select 'train' or 'test' mode", default='train')

    # ========== #
    #  Training  #
    # ========== #
    parser.add_argument('--machine', type=str, help="Select the current Machine: 'olorin', 'xps', etc",
                        default='xps')

    parser.add_argument('--model_name', type=str, help="Select Network topology: 'fcrn', etc",
                        default='fcrn')

    parser.add_argument('--data_path', type=str,
                        help="Set relative path to the input dataset <filename>.pkl file",
                        default='/media/olorin/Documentos/datasets/')

    parser.add_argument('-s', '--dataset', action='store',
                        help="Selects the dataset ['apolloscape', 'kittidepth', 'kittidiscrete', 'kitticontinuous', 'kitticontinuous_residential', 'nyudepth']", default='')

    parser.add_argument('--batch_size', type=int, help="Define the Training batch size", default=4)
    parser.add_argument('--max_steps', type=int, help="Define the number of max Steps", default=1000)
    parser.add_argument('-l', '--learning_rate', type=float, help="Define the initial learning rate", default=1e-4)
    parser.add_argument('-d', '--dropout', type=float, help="Enable dropout in the model during training", default=0.5)
    parser.add_argument('--ldecay', action='store_true', help="Enable learning decay", default=False)
    parser.add_argument('-n', '--l2norm', action='store_true', help="Enable L2 Normalization", default=False)

    parser.add_argument('--full_summary', action='store_true',
                        help="If set, will keep more data for each summary. Warning: the file can become very large")

    parser.add_argument('--log_directory', type=str, help="Set directory to save checkpoints and summaries",
                        default='log_tb/')

    parser.add_argument('-t', '--show_train_progress', action='store_true', help="Show Training Progress Images",
                        default=False)

    parser.add_argument('-v', '--show_valid_progress', action='store_true', help="Show Validation Progress Images",
                        default=False)

    # ========= #
    #  Testing  #
    # ========= #
    parser.add_argument('-o', '--output_directory', type=str,
                        help='output directory for test disparities, if empty outputs to checkpoint folder',
                        default='')

    parser.add_argument('-u', '--show_test_results', action='store_true',
                        help="Show the first batch testing Network prediction img", default=False)

    # ============ #
    #  Prediction  #
    # ============ #
    parser.add_argument('-r', '--model_path', type=str, help="Set path to a specific model to be restored", default='')
    parser.add_argument('-i', '--image_path', help='Set path to the image to be predicted', default='')

    return parser.parse_args()

