# ===========
#  Libraries
# ===========
import numpy as np
import matplotlib.pyplot as plt
import modules.loss as loss


# ==================
#  Global Variables
# ==================


# ===========
#  Functions
# ===========
def updateColorBar(cbar, img):
    vmin, vmax = np.min(img), np.max(img)
    cbar.set_clim(vmin, vmax)

    # Debug
    # print(vmin, vmax)


# ===================
#  Class Declaration
# ===================
class Plot(object):
    def __init__(self, mode, title):
        self.fig, self.axes = None, None

        if mode == 'train':  # and Validation
            self.fig, self.axes = plt.subplots(7, 1, figsize=(15, 5))
            self.axes[0] = plt.subplot(231)
            self.axes[1] = plt.subplot(232)
            self.axes[2] = plt.subplot(233)
            self.axes[3] = plt.subplot(234)
            self.axes[4] = plt.subplot(235)

            # Sets Titles
            self.axes[0].set_title("Image")
            self.axes[1].set_title("Label")
            self.axes[2].set_title("log(Label)")
            self.axes[3].set_title("Pred")
            self.axes[4].set_title("MSE(Pred)")

        elif mode == 'test':
            self.fig, self.axes = plt.subplots(9, 1, figsize=(15, 5))
            self.axes[0] = plt.subplot(331)
            self.axes[1] = plt.subplot(334)
            self.axes[2] = plt.subplot(332)
            self.axes[3] = plt.subplot(335)
            self.axes[4] = plt.subplot(336)
            self.axes[5] = plt.subplot(337)
            self.axes[6] = plt.subplot(338)
            self.axes[7] = plt.subplot(339)

            # Sets Titles
            self.axes[0].set_title("Image")
            self.axes[1].set_title("Depth")
            self.axes[2].set_title("Image Resized")
            self.axes[3].set_title("Depth Resized")
            self.axes[4].set_title("log(Label)")
            self.axes[5].set_title("Pred")
            self.axes[6].set_title("up(Pred)")
            self.axes[7].set_title("exp(Pred_up)")

        self.fig.canvas.set_window_title(title)
        # self.fig.set_size_inches(9, 5)
        self.fig.tight_layout(pad=0.4, w_pad=2, h_pad=1.0)  # Fix Subplots Spacing

        self.isFirstTime = True

    def showResults(self, raw, label, log_label, pred):
        predMSE = loss.np_MSE(y=pred, y_=log_label)

        if self.isFirstTime:
            self.cax1 = self.axes[0].imshow(raw)
            self.cax2 = self.axes[1].imshow(label)
            self.cax3 = self.axes[2].imshow(log_label)
            self.cax4 = self.axes[3].imshow(pred)
            self.cax5 = self.axes[4].imshow(predMSE, cmap='jet')

            # Creates ColorBars
            self.cbar2 = self.fig.colorbar(self.cax2, ax=self.axes[1])
            self.cbar3 = self.fig.colorbar(self.cax3, ax=self.axes[2])
            self.cbar4 = self.fig.colorbar(self.cax4, ax=self.axes[3])
            self.cbar5 = self.fig.colorbar(self.cax5, ax=self.axes[4])

            self.isFirstTime = False
        else:
            # Updates Colorbars
            updateColorBar(self.cbar2, label)
            updateColorBar(self.cbar3, log_label)
            updateColorBar(self.cbar4, pred)
            updateColorBar(self.cbar5, predMSE)

            # Updates Images
            self.cax1.set_data(raw)
            self.cax2.set_data(label)
            self.cax3.set_data(log_label)
            self.cax4.set_data(pred)
            self.cax5.set_data(predMSE)
            plt.draw()

        plt.pause(0.001)

    def showTestResults(self, image, depth, image_resized, depth_resized, log_label, pred, pred_up, pred_exp, i):
        # predMSE = loss.np_MSE(y=pred, y_=log_label)

        if self.isFirstTime:
            self.cax0 = self.axes[0].imshow(image)
            self.cax1 = self.axes[1].imshow(depth)
            self.cax2 = self.axes[2].imshow(image_resized)
            self.cax3 = self.axes[3].imshow(depth_resized)
            self.cax4 = self.axes[4].imshow(log_label)
            self.cax5 = self.axes[5].imshow(pred)
            self.cax6 = self.axes[6].imshow(pred_up)
            self.cax7 = self.axes[7].imshow(pred_exp)
            # self.cax7 = self.axes[6].imshow(predMSE, cmap='jet')

            # Creates ColorBars
            # self.cbar0 = self.fig.colorbar(self.cax0, ax=self.axes[0])
            self.cbar1 = self.fig.colorbar(self.cax1, ax=self.axes[1])
            # self.cbar2 = self.fig.colorbar(self.cax2, ax=self.axes[2])
            self.cbar3 = self.fig.colorbar(self.cax3, ax=self.axes[3])
            self.cbar4 = self.fig.colorbar(self.cax4, ax=self.axes[4])
            self.cbar5 = self.fig.colorbar(self.cax5, ax=self.axes[5])
            self.cbar6 = self.fig.colorbar(self.cax6, ax=self.axes[6])
            self.cbar7 = self.fig.colorbar(self.cax7, ax=self.axes[7])

            self.isFirstTime = False
        else:
            # Updates Colorbars
            updateColorBar(self.cbar1, depth)
            updateColorBar(self.cbar3, depth_resized)
            updateColorBar(self.cbar4, log_label)
            updateColorBar(self.cbar5, pred)
            updateColorBar(self.cbar6, pred_up)
            updateColorBar(self.cbar7, pred_exp)

            # Updates Images
            self.cax0.set_data(image)
            self.cax1.set_data(depth)
            self.cax2.set_data(image_resized)
            self.cax3.set_data(depth_resized)
            self.cax4.set_data(log_label)
            self.cax5.set_data(pred)
            self.cax6.set_data(pred_up)
            self.cax7.set_data(pred_exp)
            # self.cax7.set_data(predMSE)
            plt.draw()

        self.fig.canvas.set_window_title("Test Predictions [%d]" % i)

        plt.pause(0.5)
