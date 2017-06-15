import json

import matplotlib.pyplot as plt
import pandas as pd
from keras.callbacks import EarlyStopping, ModelCheckpoint
from keras.models import Model, model_from_json
from keras.layers import Convolution2D, Input, Dropout
from keras.layers import Flatten, Dense
from keras.utils.visualize_util import plot
from keras.preprocessing.image import *
import tensorflow as tf
from PIL import Image
from utils import RegressionImageDataGenerator

np.random.seed(7)

# Constants
IMG_SIZE = [120, 160]
CROPPING = (0, 0, 0, 0)
SHIFT_OFFSET = 0.2
SHIFT_RANGE = 0.2

BATCH_SIZE = 64
PATIENCE = 10
NB_EPOCH = 1

DATA_PATH_PREFIX = 'data/'  # allows easy change for various folders
TRAINING_DATA_PATHS = [
    DATA_PATH_PREFIX + 'central/driving_log.csv',
    DATA_PATH_PREFIX + 'slalom/driving_log.csv',
    DATA_PATH_PREFIX + 'reverse/driving_log.csv',
    DATA_PATH_PREFIX + 'recover_1/driving_log.csv',
    DATA_PATH_PREFIX + 'recover_2/driving_log.csv',
    DATA_PATH_PREFIX + 'track_2_central/driving_log.csv',
    DATA_PATH_PREFIX + 'track_2_slalom/driving_log.csv',
    DATA_PATH_PREFIX + 'track_2_slalom_2/driving_log.csv',
    DATA_PATH_PREFIX + 'track_2_recover/driving_log.csv',
]

VALIDATION_DATA_PATHS = [
    DATA_PATH_PREFIX + 'track_2_recover/driving_log.csv',
    DATA_PATH_PREFIX + 'track_2_central/driving_log.csv',
    DATA_PATH_PREFIX + 'test_1/driving_log.csv',
    DATA_PATH_PREFIX + 'test_2/driving_log.csv',
]


# Data loading


def get_generator(train_paths, validation_paths, batch_size=32):
    global training_log, validation_log
    """
    Creates an image data generator for training data and one for validation data. Left and Right images are
    added with an offset steering angle.
    :param train_paths: A list of paths to all the log files used for training
    :param validation_paths: A list of paths to all the log files used for validation
    :param batch_size: The batch size to use
    :return: training generator, validation generator
    """
    header = ['image', 'steering_angle']
    training_log = pd.concat([pd.read_csv(path, names=header) for path in train_paths])
    validation_log = pd.concat([pd.read_csv(path, names=header) for path in validation_paths])

    training_data_generator = RegressionImageDataGenerator(rescale=lambda x: x / 127.5 - 1.,
                                                           horizontal_flip=True,
                                                           horizontal_flip_value_transform=lambda val: -val,
                                                           # rotation_range=2,
                                                           # channel_shift_range=0.2,
                                                           # width_shift_range=SHIFT_RANGE,
                                                           # width_shift_value_transform=lambda val, shift: val - (
                                                           #     (SHIFT_OFFSET / SHIFT_RANGE) * shift)
                                                           # cropping=CROPPING
                                                           )

    validation_data_generator = RegressionImageDataGenerator(rescale=lambda x: x / 127.5 - 1.
                                                             # cropping=CROPPING
                                                             )

    return (
        training_data_generator.flow_from_directory(training_log.image.values, training_log.steering_angle.values,
                                                    shuffle=True, target_size=IMG_SIZE,
                                                    batch_size=batch_size),
        validation_data_generator.flow_from_directory(validation_log.image.values,
                                                      validation_log.steering_angle.values, shuffle=True,
                                                      target_size=IMG_SIZE, batch_size=batch_size))


def get_model():
    image_input = Input(shape=(IMG_SIZE[0], IMG_SIZE[1], 3), name='image_input')
    x = Convolution2D(8, 3, 3, subsample=(2, 2), activation='relu', border_mode='same')(image_input)
    x = Convolution2D(16, 3, 3, subsample=(2, 2), activation='relu', border_mode='same')(x)
    x = Convolution2D(32, 3, 3, subsample=(2, 2), activation='relu', border_mode='same')(x)

    merged = Flatten()(x)
    x = Dense(256, activation='linear')(merged)
    x = Dropout(.2)(x)
    steering_angle_out = Dense(1, activation='linear', name='steering_angle_out')(x)

    return Model(input=[image_input], output=[steering_angle_out])


if __name__ == '__main__':
    # Tweaks for low memory VGA
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    config.gpu_options.per_process_gpu_memory_fraction = 0.7
    session = tf.Session(config=config)

    # Get augmented data
    X_train, X_test = get_generator(TRAINING_DATA_PATHS, VALIDATION_DATA_PATHS, batch_size=BATCH_SIZE)

    # Load model
    model = get_model()
    model.summary()
    plot(model, to_file='model.png', show_shapes=True)
    model.compile(optimizer='adam', loss='mean_squared_error', metrics=['mae', 'acc'])

    # Persist loaded model
    model_json = model.to_json()
    with open('model.json', 'w') as f:
        json.dump(model_json, f)

    checkpoint = ModelCheckpoint('model.h5', monitor='val_loss', verbose=1, save_best_only=True,
                                 save_weights_only=False, mode='auto')
    early_stopping = EarlyStopping(monitor='val_loss', min_delta=0, patience=PATIENCE, verbose=1, mode='auto')

    history = model.fit_generator(X_train,
                                  samples_per_epoch=X_train.n,
                                  validation_data=X_test,
                                  nb_val_samples=X_test.n,
                                  nb_epoch=NB_EPOCH,
                                  callbacks=[checkpoint, early_stopping])

    # Load model
    # print 'Loading model'
    # with open('model.json', 'r') as model_file:
    #     model = model_from_json(json.load(model_file))
    #
    # print 'Compiling model'
    # model.compile(optimizer="adam", loss="mse", metrics=['mae', 'acc'])
    # model.load_weights('model.h5')

    # Test the model on training images to check the accuracy
    predicted_steering_angles = []  # Y_train
    for path in training_log.image.values:
        image = Image.open(path)
        image_array = np.asarray(image)
        image_norm = image_array / 127.5 - 1.
        transformed_image_array = image_norm[None, :, :, :]
        steering_angle_center = int(model.predict(transformed_image_array, batch_size=1))
        predicted_steering_angles.append(steering_angle_center)

    # Print accuracy values
    print 'MODEL HISTORY VALUES'
    print 'Accuracy: ', history.history['acc'][-1]
    print 'Loss    : ', history.history['mean_absolute_error'][-1]
    model_stats_file = open("model_stats.txt", "w")
    model_stats_file.write('Training set size  : %d\n' % X_train.n)
    model_stats_file.write('Validation set size: %d\n' % X_test.n)
    model_stats_file.write('Epochs  : %d\n' % NB_EPOCH)
    model_stats_file.write('Accuracy: %f\n' % history.history['acc'][-1])
    model_stats_file.write('Loss    : %f' % history.history['mean_absolute_error'][-1])
    model_stats_file.close()

    # Plot accuracy history during model training
    plt.figure(0)
    plt.plot(history.history['acc'])
    plt.plot(history.history['val_acc'])
    plt.title('model accuracy')
    plt.ylabel('accuracy')
    plt.xlabel('epoch')
    plt.legend(['train', 'test'], loc='upper left')

    # Plot loss history during model training
    plt.figure(1)
    plt.plot(history.history['loss'])
    plt.plot(history.history['val_loss'])
    plt.title('model loss')
    plt.ylabel('loss')
    plt.xlabel('epoch')
    plt.legend(['train', 'test'], loc='upper left')

    # Plot predicted values with ground truths
    plt.figure(2)
    plt.plot(predicted_steering_angles)
    plt.plot(training_log.steering_angle.values)
    plt.title('accuracy')
    plt.legend(['predicted', 'actual'], loc='upper left')
    plt.show()
