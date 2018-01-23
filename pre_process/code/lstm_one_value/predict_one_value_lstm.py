#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Dec 16 21:10:46 2017

@author: dingwangxiang
"""

# import your module here
import pandas as pd
import numpy as np
from keras.models import Sequential, model_from_json
from keras.layers import Dense, LSTM, Dropout
# from sklearn.preprocessing import MinMaxScaler
from trainingset_selection import TrainingSetSelection
from keras.models import load_model, save_model
from keras.utils import plot_model
#from keras.layers.core import Dense, Dropout, Activation
from sklearn.model_selection import train_test_split
from preprocessing import get_ids_and_files_in_dir, percentile_remove_outlier, MinMaxScaler, NormalDistributionScaler, binning_date_y
import os

# (global) variable definition here
file_sets = [
        'DBID(1002089510)_INSTID(1)','DBID(2897570545)_INSTID(1)',
        'DBID(1227435885)_INSTID(1)','DBID(2949199900)_INSTID(1)',
        'DBID(1227435885)_INSTID(2)','DBID(3065831173)_INSTID(1)',
        'DBID(1254139675)_INSTID(1)','DBID(3111200895)_INSTID(1)',
        'DBID(1384807946)_INSTID(1)','DBID(3172835364)_INSTID(1)',
        'DBID(1624869053)_INSTID(1)','DBID(3204204681)_INSTID(1)',
        'DBID(1636599671)_INSTID(1)','DBID(3482311182)_INSTID(1)',
        'DBID(1636599671)_INSTID(2)','DBID(349165204)_INSTID(1)',
        'DBID(172908691)_INSTID(1)','DBID(3671658776)_INSTID(1)',
        'DBID(1855232979)_INSTID(1)','DBID(3671658776)_INSTID(2)',
        'DBID(1982696497)_INSTID(1)','DBID(3775482706)_INSTID(1)',
        'DBID(2031853600)_INSTID(1)','DBID(3775482706)_INSTID(2)',
        'DBID(2052255707)_INSTID(1)','DBID(4213264717)_INSTID(1)',
        'DBID(2238741707)_INSTID(1)','DBID(4215505906)_INSTID(1)',
        'DBID(2238741707)_INSTID(2)','DBID(4225426100)_INSTID(1)',
        'DBID(2328880794)_INSTID(1)','DBID(4291669003)_INSTID(1)',
        'DBID(2413621137)_INSTID(1)','DBID(4291669003)_INSTID(2)',
        'DBID(2612437783)_INSTID(1)','DBID(447326245)_INSTID(1)',
        'DBID(2644427317)_INSTID(1)','DBID(468957624)_INSTID(1)',
        'DBID(2707003786)_INSTID(1)','DBID(505574722)_INSTID(1)',
        'DBID(2762567375)_INSTID(1)','DBID(522516877)_INSTID(1)',
        'DBID(2768077198)_INSTID(1)','DBID(770699067)_INSTID(1)',
        'DBID(2778659381)_INSTID(1)','DBID(929227073)_INSTID(1)',
        'DBID(2778659381)_INSTID(2)','DBID(942093433)_INSTID(1)',
        'DBID(2802676787)_INSTID(1)','DBID(998852395)_INSTID(1)',
        ]

file_all = ['DBID(9999999999)_INSTID(1)',]

# class definition here
class NeuralNetwork():
    def __init__(self,
                 training_set_dir,
                 model_save_dir,
                 output_dir=".",
                 model_file_prefix='model',
                 training_set_id_range=(0, np.Inf),
                 training_set_length=3,
                 scaler = 'mm',
                 **kwargs):
        """
        :param training_set_dir: directory contains the training set files. File format: 76.csv
        :param model_save_dir: directory to receive trained model and model weights. File format: model-76.json/model-weight-76.h5
        :param model_file_prefix='model': file prefix for model file
        :param training_set_range=(0, np.Inf): enterprise ids in this range (a, b) would be analyzed. PS: a must be less than b
        :param training_set_length=3: first kth columns in training set file will be used as training set and the following one is expected value
        :param train_test_ratio=3: the ratio of training set size to test set size when splitting input data
        :param output_dir=".": output directory for prediction files
        :param scaler: scale data set using - mm: MinMaxScaler, norm: NormalDistributionScaler
        :param **kwargs: lstm_output_dim=4: output dimension of LSTM layer;
                        activation_lstm='relu': activation function for LSTM layers;
                        activation_dense='relu': activation function for Dense layer;
                        activation_last='softmax': activation function for last layer;
                        drop_out=0.2: fraction of input units to drop;
                        np_epoch=25, the number of epoches to train the model. epoch is one forward pass and one backward pass of all the training examples;
                        batch_size=100: number of samples per gradient update. The higher the batch size, the more memory space you'll need;
                        loss='categorical_crossentropy': loss function;
                        optimizer='rmsprop'
        """
        self.training_set_dir = training_set_dir
        self.model_save_dir = model_save_dir
        self.model_file_prefix = model_file_prefix
        self.training_set_id_range = training_set_id_range
        self.training_set_length = training_set_length
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        if not os.path.exists(self.model_save_dir):
            os.makedirs(self.model_save_dir)
        self.scaler = scaler
        self.test_size = kwargs.get('test_size', 0.2)
        self.lstm_output_dim = kwargs.get('lstm_output_dim', 8)
        self.activation_lstm = kwargs.get('activation_lstm', 'relu')
        self.activation_dense = kwargs.get('activation_dense', 'relu')
        self.activation_last = kwargs.get('activation_last', 'softmax')    # softmax for multiple output
        self.dense_layer = kwargs.get('dense_layer', 2)  # at least 2 layers
        self.lstm_layer = kwargs.get('lstm_layer', 2) # at least 2 layers
        self.drop_out = kwargs.get('drop_out', 0.2)
        self.nb_epoch = kwargs.get('nb_epoch', 100)
        self.batch_size = kwargs.get('batch_size', 100)
        self.loss = kwargs.get('loss', 'categorical_crossentropy')
        self.optimizer = kwargs.get('optimizer', 'rmsprop')


    def NN_model_train(self, trainX, trainY, testX, testY, model_save_path):
        """
        :param trainX: training data set
        :param trainY: expect value of training data
        :param testX: test data segt
        :param testY: expect value of test data
        :param model_save_path: h5 file to store the trained model
        :param override: override existing models
        :return: model after training
        """
        input_dim = trainX[0].shape[1]
        output_dim = trainY.shape[1]
        # print predefined parameters of current model:
        model = Sequential()
        # applying a LSTM layer with x dim output and y dim input. Use dropout parameter to avoid overfit
        model.add(LSTM(output_dim=self.lstm_output_dim,
                       input_dim=input_dim,
                       activation=self.activation_lstm,
                       dropout=self.drop_out,
                       return_sequences=True))
        for i in range(self.lstm_layer-2):
            model.add(LSTM(output_dim=self.lstm_output_dim,
                       activation=self.activation_lstm,
                       dropout=self.drop_out,
                       return_sequences=True ))
        # return sequences should be False to avoid dim error when concatenating with dense layer
        model.add(LSTM(output_dim=self.lstm_output_dim, activation=self.activation_lstm, dropout_U=self.drop_out))
        # applying a full connected NN to accept output from LSTM layer
        for i in range(self.dense_layer-1):
            model.add(Dense(output_dim=self.lstm_output_dim, activation=self.activation_dense))
            model.add(Dropout(self.drop_out))
        model.add(Dense(output_dim=output_dim, activation=self.activation_last))
        # configure the learning process
        model.compile(loss=self.loss, optimizer=self.optimizer, metrics=['accuracy'])
        # train the model with fixed number of epoches
        model.fit(x=trainX, y=trainY, nb_epoch=self.nb_epoch, batch_size=self.batch_size, validation_data=(testX, testY))
        model.summary()
        plot_model(model, to_file='model.png')
        score = model.evaluate(trainX, trainY, self.batch_size)
        print ("Model evaluation: {}".format(score))                  # [0.29132906793909186, 0.91639871695672837]
        # store model to json file
        save_model(model, model_save_path)


    @staticmethod
    def NN_prediction(dataset, model_save_path):
        dataset = np.asarray(dataset)
        if not os.path.exists(model_save_path):
            raise ValueError("Lstm model not found! Train one first or check your input path: {}".format(model_save_path))
        model = load_model(model_save_path)
        predict_class = model.predict_classes(dataset)
        class_prob = model.predict_proba(dataset)
        return predict_class, class_prob


    def model_train_predict_test(self, input_file_regx="(DBID)\((\d+)\)_INSTID\([1]\).csv", override=False):            # "^(\d+)\.csv"
        """
        :param override=Fasle: rerun the model prediction no matter if the expected output file exists
        :return: model file, model weights files, prediction file, discrepancy statistic bar plot file
        """
        # get training sets for lstm training
        print ("Scanning files within select id range ...")
        print(input_file_regx)
        print(self.training_set_dir)
        ids, files = get_ids_and_files_in_dir(inputdir=self.training_set_dir,
                                                          range=self.training_set_id_range,
                                                          input_file_regx=input_file_regx)
        print ("Scanning done! Selected enterprise ids are {}".format(ids))
        if not files:
            raise ValueError("No files selected in current id range. Please check the input training set directory, "
                             "input enterprise id range or file format which should be '[0-9]+.csv'")

        # get train, test, validation data
        for id_index, id_file in enumerate(files):
            # store prediction result to prediction directory
            enter_file = self.training_set_dir + "/" + id_file
            print ("Processing dataset - enterprise_id is: {}".format(ids[id_index]))
            print ("Reading from file {}".format(enter_file))
            df = pd.read_csv(enter_file)
            df.index = range(len(df.index))
            # retrieve training X and Y columns. First column is customer_id
            select_col = []
            select_col = np.append(select_col, ['X' + str(i) for i in range(1, 1+self.training_set_length)])
            select_col = np.append(select_col, ['Y'])
            df_selected = df.ix[:, select_col]
            print(df_selected)
            # remove outlier records
            """
            df_selected = percentile_remove_outlier(df_selected, filter_start=0, filter_end=1+self.training_set_length)
            print(df_selected)
            """
            # scale the train columns
            print ("Scaling...")
            if self.scaler == 'mm':
                global bin_boundary
                df_scale, minVal, maxVal, bin_boundary = MinMaxScaler(df_selected, start_col_index=0, end_col_index=self.training_set_length)
            elif self.scaler == 'norm':
                df_scale, meanVal, stdVal = NormalDistributionScaler(df_selected, start_col_index=0, end_col_index=self.training_set_length)
            else:
                raise ValueError("Argument scaler must be mm or norm!")
            # bin date y
            df_bin, bin_boundary = binning_date_y(df_scale, y_col=self.training_set_length, n_group=5, bin_boundary=bin_boundary)
            print ("Bin boundary is {}".format(bin_boundary))
            # get train and test dataset
            print ("Randomly selecting training set and test set...")
            all_data_x = np.asarray(df_bin.ix[:, 0:self.training_set_length]).reshape((len(df_bin.index), 1, self.training_set_length))
            all_data_y = np.asarray(df_bin.ix[:, self.training_set_length])
            # convert y label to one-hot dummy label
            y_dummy_label = np.asarray(pd.get_dummies(all_data_y))
            # format train, test, validation data
            sub_train, val_train, sub_test, val_test = train_test_split(all_data_x, y_dummy_label, test_size=self.test_size)
            train_x, test_x, train_y, test_y = train_test_split(sub_train, sub_test, test_size=self.test_size)
            # create and fit the NN model
            model_save_path = self.model_save_dir + "/" + self.model_file_prefix + "-" + str(ids[id_index]) + ".h5"
            # check if model file exists
            if not os.path.exists(model_save_path) or override:
                self.NN_model_train(train_x, train_y, test_x, test_y, model_save_path=model_save_path)
            # generate prediction for training
            print ("Predicting the output of validation set...")           
            val_predict_class, val_predict_prob = self.NN_prediction(val_train, model_save_path=model_save_path)
            # statistic of discrepancy between expected value and real value
            total_sample_count = len(val_predict_class)
            val_test_label = np.asarray([list(x).index(1) for x in val_test])
            match_count = (np.asarray(val_predict_class) == np.asarray(val_test_label.ravel())).sum()
            print ("Precision using validation dataset is {}".format(float(match_count) / total_sample_count))           # 0.9178082191780822

# function definition here
def create_interval_dataset(dataset, lookback):
    """
    :param dataset: input array of time intervals
    :param look_back: each training set feature length
    :return: convert an array of values into a dataset matrix.
    """
    dataX, dataY = [], []
    for i in range(len(dataset) - lookback):
        dataX.append(dataset[i:i+lookback])
        dataY.append(dataset[i+lookback])
    return np.asarray(dataX), np.asarray(dataY)


def main():
    print("a1")
    training_set_dir = "../../time_series_50_to_1"                             # "/your_local_path/RNN_prediction_2/cluster/train"
    output_dir = "./cluster_lstm_model"                                        # "/your_local_path/RNN_prediction_2/cluster_lstm_model"
    training_set_id_range = (9999999999, 9999999999)
    training_set_length = 50
    dense_layer = 2
    model_file_prefix = 'model'
    model_save_dir = output_dir + "/" + model_file_prefix
    training_set_regx_format = "(DBID)\((\d+)\)_INSTID\([1]\)_perf.csv"        # "cluster-(\d+)\.csv"
    print("a2")
    obj_NN = NeuralNetwork(output_dir=output_dir,
                           training_set_dir=training_set_dir,
                           model_save_dir=model_save_dir,
                           model_file_prefix=model_file_prefix,
                           training_set_id_range=training_set_id_range,
                           training_set_length=training_set_length,
                           dense_layer=dense_layer)
    # record program process printout in log file
    """
    stdout_backup = sys.stdout
    log_file_path = output_dir + "/NN_model_running_log.txt"
    log_file_handler = open(log_file_path, "w")
    print ("Log message could be found in file: {}".format(log_file_path))
    sys.stdout = log_file_handler
    """
    # check if the training set directory is empty. If so, run the training set selection
    if not os.listdir(obj_NN.training_set_dir):
        print ("Training set files not exist! Run trainingSetSelection.trainingSetGeneration to generate them! Start running generating training set files...")
        trainingSetObj = TrainingSetSelection(min_purchase_count=4)
        trainingSetObj.trainingset_generation(outdir=obj_NN.training_set_dir)
        print ("Training set file generation done! They are store at %s directory!".format(obj_NN.training_set_dir))
    print ("Train NN model and test!")
    obj_NN.model_train_predict_test(override=False, input_file_regx=training_set_regx_format)
    print ("Models and their parameters are stored in {}".format(obj_NN.model_save_dir))
    # close log file
    """
    log_file_handler.close()
    sys.stdout = stdout_backup
    """

# main program here
if  __name__ == '__main__':
    main()
    """
    csv_file_name = '../../time_series_one/' + file_all[0] + '_perf'+'.csv'
    df = pd.read_csv(csv_file_name)    
    dataset_init = np.asarray(df).reshape(-1)    # if only 1 column
    dataX, dataY = create_interval_dataset(dataset_init, lookback=50)    # look back if the training set sequence length
    df_new = pd.DataFrame(dataX, columns = ['X' + str(i) for i in range(1, 1+dataX.shape[1])])
    df_new['Y'] = pd.Series(dataY,index = df_new.index)
    df_new.to_csv(path_or_buf = '../../time_series_50_to_1/' + file_all[0] + '_perf'+'.csv', index=False)
    """
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    