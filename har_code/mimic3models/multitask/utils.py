from __future__ import absolute_import
from __future__ import print_function

from har_code.mimic3models import metrics
from har_code.mimic3models import common_utils
import numpy as np
import threading
import random


# class BatchGen(object):
#     def __init__(self, reader, discretizer, normalizer, ihm_pos, partition,
#                  target_repl, batch_size, small_part, shuffle, return_names=False):
#         self.discretizer = discretizer
#         self.normalizer = normalizer
#         self.ihm_pos = ihm_pos
#         self.partition = partition
#         self.target_repl = target_repl
#         self.batch_size = batch_size
#         self.shuffle = shuffle
#         self.return_names = return_names

#         N = reader.get_number_of_examples()

#         if small_part:
#             N = 5000
#         self.steps = (N + batch_size - 1) // batch_size
#         self.lock = threading.Lock()

#         ret = common_utils.read_chunk(reader, N)
#         Xs = ret['X']
#         ts = ret['t']
#         # these are all labels
#         ihms = ret['ihm']
#         # los : Array of 2 arrays: [masks, labels].
#         loss = ret['los']
#         phenos = ret['pheno']
#         # decoms [masks, labels]
#         decomps = ret['decomp']


#         self.data = dict()
#         self.data['pheno_ts'] = ts
#         self.data['names'] = ret['name']
#         self.data['decomp_ts'] = []
#         self.data['los_ts'] = []

#         for i in range(N):
#             self.data['decomp_ts'].append([pos for pos, m in enumerate(decomps[i][0]) if m == 1])
#             self.data['los_ts'].append([pos for pos, m in enumerate(loss[i][0]) if m == 1])
#             (Xs[i], ihms[i], decomps[i], loss[i], phenos[i]) = \
#                 self._preprocess_single(Xs[i], ts[i], ihms[i], decomps[i], loss[i], phenos[i])

#         self.data['X'] = Xs
#         self.data['ihm_M'] = [x[0] for x in ihms]
#         self.data['ihm_y'] = [x[1] for x in ihms]
#         self.data['decomp_M'] = [x[0] for x in decomps]
#         self.data['decomp_y'] = [x[1] for x in decomps]
#         self.data['los_M'] = [x[0] for x in loss]
#         self.data['los_y'] = [x[1] for x in loss]
#         self.data['pheno_y'] = phenos

#         self.generator = self._generator()

#     def _preprocess_single(self, X, max_time, ihm, decomp, los, pheno):
#         timestep = self.discretizer._timestep
#         eps = 1e-6

#         def get_bin(t):
#             return int(t / timestep - eps)

#         n_steps = get_bin(max_time) + 1

#         # X
#         X = self.discretizer.transform(X, end=max_time)[0]
#         if self.normalizer is not None:
#             X = self.normalizer.transform(X)
#         assert len(X) == n_steps

#         # ihm
#         # NOTE: when mask is 0, we set y to be 0. This is important
#         #       because in the multitask networks when ihm_M = 0 we set
#         #       our prediction thus the loss will be 0.
#         if np.equal(ihm[1], 0):
#             ihm[2] = 0
#         ihm = (np.int32(ihm[1]), np.int32(ihm[2]))  # mask, label

#         # decomp
#         decomp_M = [0] * n_steps
#         decomp_y = [0] * n_steps
#         for i in range(len(decomp[0])):
#             pos = get_bin(i)
#             decomp_M[pos] = decomp[0][i]
#             decomp_y[pos] = decomp[1][i]
#         decomp = (np.array(decomp_M, dtype=np.int32),
#                   np.array(decomp_y, dtype=np.int32))

#         # los
#         los_M = [0] * n_steps
#         los_y = [0] * n_steps
#         for i in range(len(los[0])):
#             pos = get_bin(i)
#             los_M[pos] = los[0][i]
#             los_y[pos] = los[1][i]
#         los = (np.array(los_M, dtype=np.int32),
#                np.array(los_y, dtype=np.float32))

#         # pheno
#         pheno = np.array(pheno, dtype=np.int32)

#         return (X, ihm, decomp, los, pheno)

#     def _generator(self):
#         B = self.batch_size
#         while True:
#             # convert to right format for sort_and_shuffle
#             kv_pairs = list(self.data.items())
#             data_index = [pair[0] for pair in kv_pairs].index('X')
#             if data_index > 0:
#                 kv_pairs[0], kv_pairs[data_index] = kv_pairs[data_index], kv_pairs[0]
#             mas = [kv[1] for kv in kv_pairs]

#             if self.shuffle:
#                 N = len(self.data['X'])
#                 order = list(range(N))
#                 random.shuffle(order)
#                 tmp = [None] * len(mas)
#                 for mas_idx in range(len(mas)):
#                     tmp[mas_idx] = [None] * len(mas[mas_idx])
#                     for i in range(N):
#                         tmp[mas_idx][i] = mas[mas_idx][order[i]]
#                 for i in range(len(kv_pairs)):
#                     self.data[kv_pairs[i][0]] = tmp[i]
#             else:
#                 # sort entirely
#                 mas = common_utils.sort_and_shuffle(mas, B)
#                 for i in range(len(kv_pairs)):
#                     self.data[kv_pairs[i][0]] = mas[i]

#             for i in range(0, len(self.data['X']), B):
#                 outputs = []

#                 # X
#                 X = self.data['X'][i:i+B]
#                 X = common_utils.pad_zeros(X, min_length=self.ihm_pos + 1)
#                 T = X.shape[1]

#                 # ihm
#                 ihm_M = np.array(self.data['ihm_M'][i:i+B])
#                 ihm_M = np.expand_dims(ihm_M, axis=-1)  # (B, 1)
#                 ihm_y = np.array(self.data['ihm_y'][i:i+B])
#                 ihm_y = np.expand_dims(ihm_y, axis=-1)  # (B, 1)
#                 outputs.append(ihm_y)
#                 if self.target_repl:
#                     ihm_seq = np.expand_dims(ihm_y, axis=-1).repeat(T, axis=1)  # (B, T, 1)
#                     outputs.append(ihm_seq)

#                 # decomp
#                 decomp_M = self.data['decomp_M'][i:i+B]
#                 decomp_M = common_utils.pad_zeros(decomp_M, min_length=self.ihm_pos + 1)
#                 decomp_y = self.data['decomp_y'][i:i+B]
#                 decomp_y = common_utils.pad_zeros(decomp_y, min_length=self.ihm_pos + 1)
#                 decomp_y = np.expand_dims(decomp_y, axis=-1)  # (B, T, 1)
#                 outputs.append(decomp_y)

#                 # los
#                 los_M = self.data['los_M'][i:i+B]
#                 los_M = common_utils.pad_zeros(los_M, min_length=self.ihm_pos + 1)
#                 los_y = self.data['los_y'][i:i+B]
#                 los_y_true = common_utils.pad_zeros(los_y, min_length=self.ihm_pos + 1)

#                 if self.partition == 'log':
#                     los_y = [np.array([metrics.get_bin_log(x, 10) for x in z]) for z in los_y]
#                 if self.partition == 'custom':
#                     los_y = [np.array([metrics.get_bin_custom(x, 10) for x in z]) for z in los_y]
#                 los_y = common_utils.pad_zeros(los_y, min_length=self.ihm_pos + 1)
#                 los_y = np.expand_dims(los_y, axis=-1)  # (B, T, 1)
#                 outputs.append(los_y)

#                 # pheno
#                 pheno_y = np.array(self.data['pheno_y'][i:i+B])
#                 outputs.append(pheno_y)
#                 if self.target_repl:
#                     pheno_seq = np.expand_dims(pheno_y, axis=1).repeat(T, axis=1)  # (B, T, 25)
#                     outputs.append(pheno_seq)

#                 inputs = [X, ihm_M, decomp_M, los_M]

#                 if self.return_y_true:
#                     batch_data = (inputs, outputs, los_y_true)
#                 else:
#                     batch_data = (inputs, outputs)

#                 if not self.return_names:
#                     yield batch_data
#                 else:
#                     yield {'data': batch_data,
#                            'names': self.data['names'][i:i+B],
#                            'decomp_ts': self.data['decomp_ts'][i:i+B],
#                            'los_ts': self.data['los_ts'][i:i+B],
#                            'pheno_ts': self.data['pheno_ts'][i:i + B]}

#     def __iter__(self):
#         return self.generator

#     def next(self, return_y_true=False):
#         with self.lock:
#             self.return_y_true = return_y_true
#             return next(self.generator)

#     def __next__(self):
#         return self.next()

class BatchGen(object):
    def __init__(self, reader, discretizer, normalizer, ihm_pos, partition,
                 target_repl, batch_size, small_part, shuffle, return_names=False):
        self.discretizer = discretizer
        self.normalizer = normalizer
        self.ihm_pos = ihm_pos
        self.partition = partition
        self.target_repl = target_repl
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.return_names = return_names
        
        self.reader = reader
        self.N = reader.get_number_of_examples()
        if small_part:
            self.N = 10000
        self.steps = (self.N + batch_size - 1) // batch_size
        self.lock = threading.Lock()
        with open(reader.listfile_path, "r") as lfile:
            self.data = lfile.readlines()
        self.listfile_header = self.data[0]
        self.data = self.data[1:]
        self.generator = self._generator()
                

    def read_batch(self, reader):
        batch = {}
        for _ in range(self.batch_size):
            to_read_index = reader._current_index
            reader._current_index += 1
            if reader._current_index == self.reader.get_number_of_examples():
                reader._current_index = 0
            data = self.reader.read_example(to_read_index)
            for k, v in data.items():
                if k not in batch:
                    batch[k] = []
                batch[k].append(v)
        return batch
            
        

    def _preprocess_single(self, X, max_time, ihm, decomp, los, pheno):
        timestep = self.discretizer._timestep
        eps = 1e-6

        def get_bin(t):
            return int(t / timestep - eps)

        n_steps = get_bin(max_time) + 1

        # X
        X = self.discretizer.transform(X, end=max_time)[0]
        if self.normalizer is not None:
            X = self.normalizer.transform(X)
        assert len(X) == n_steps

        # ihm
        # NOTE: when mask is 0, we set y to be 0. This is important
        #       because in the multitask networks when ihm_M = 0 we set
        #       our prediction thus the loss will be 0.
        if np.equal(ihm[1], 0):
            ihm[2] = 0
        ihm = (np.int32(ihm[1]), np.int32(ihm[2]))  # mask, label

        # decomp
        decomp_M = [0] * n_steps
        decomp_y = [0] * n_steps
        for i in range(len(decomp[0])):
            pos = get_bin(i)
            decomp_M[pos] = decomp[0][i]
            decomp_y[pos] = decomp[1][i]
        decomp = (np.array(decomp_M, dtype=np.int32),
                  np.array(decomp_y, dtype=np.int32))

        # los
        los_M = [0] * n_steps
        los_y = [0] * n_steps
        for i in range(len(los[0])):
            pos = get_bin(i)
            los_M[pos] = los[0][i]
            los_y[pos] = los[1][i]
        los = (np.array(los_M, dtype=np.int32),
               np.array(los_y, dtype=np.float32))

        # pheno
        pheno = np.array(pheno, dtype=np.int32)

        return (X, ihm, decomp, los, pheno)

    def _generator(self):
        B = self.batch_size
        while True:
            if self.shuffle:
                random.shuffle(self.data)
            

            for i in range(0, self.N, B):
                outputs = []
                data_batch = self.read_batch(self.reader)
                data_batch['pheno_ts'] = data_batch['t']
                data_batch['decom_ts'] = []
                data_batch['los_ts'] = []
                
                
                for j in range(B):
                    data_batch['decom_ts'].append([pos for pos,m in enumerate(data_batch['decomp'][j][0]) if m ==1])
                    data_batch['los_ts'].append([pos for pos,m in enumerate(data_batch['los'][j][0]) if m==1])
                    (data_batch['X'][j], data_batch['ihm'][j], data_batch['decomp'][j],data_batch['los'][j], data_batch['pheno'][j]) = \
                     self._preprocess_single(data_batch['X'][j], data_batch['t'][j],data_batch['ihm'][j], data_batch['decomp'][j],data_batch['los'][j], data_batch['pheno'][j])
                    
                data_batch['ihm_M'] = [x[0] for x in data_batch['ihm']]
                data_batch['ihm_y'] = [x[1] for x in data_batch['ihm']]
                data_batch['decomp_M'] = [x[0] for x in data_batch['decomp']]
                
                
                data_batch['decomp_y'] = [x[1] for x in data_batch['decomp']]
                data_batch['los_M'] = [x[0] for x in data_batch['los']]
                data_batch['los_y'] = [x[1] for x in data_batch['los']]
                data_batch['pheno_y'] = data_batch['pheno']


                # X
                X = data_batch['X']
                X = common_utils.pad_zeros(X, min_length=self.ihm_pos + 1)
                T = X.shape[1]

                # ihm
                ihm_M = np.array(data_batch['ihm_M'])
                ihm_M = np.expand_dims(ihm_M, axis=-1)  # (B, 1)
                ihm_y = np.array(data_batch['ihm_y'])
                ihm_y = np.expand_dims(ihm_y, axis=-1)  # (B, 1)
                outputs.append(ihm_y)
                
                if self.target_repl:
                    ihm_seq = np.expand_dims(ihm_y, axis=-1).repeat(T, axis=1)  # (B, T, 1)
                    outputs.append(ihm_seq)

                # decomp
                decomp_M = data_batch['decomp_M']
                decomp_M = common_utils.pad_zeros(decomp_M, min_length=self.ihm_pos + 1)
                decomp_y = data_batch['decomp_y']
                decomp_y = common_utils.pad_zeros(decomp_y, min_length=self.ihm_pos + 1)
                decomp_y = np.expand_dims(decomp_y, axis=-1)  # (B, T, 1)
                outputs.append(decomp_y)

                # los
                los_M = data_batch['los_M']
                los_M = common_utils.pad_zeros(los_M, min_length=self.ihm_pos + 1)
                los_y = data_batch['los_y']
                los_y_true = common_utils.pad_zeros(los_y, min_length=self.ihm_pos + 1)

                if self.partition == 'log':
                    los_y = [np.array([metrics.get_bin_log(x, 10) for x in z]) for z in los_y]
                if self.partition == 'custom':
                    los_y = [np.array([metrics.get_bin_custom(x, 10) for x in z]) for z in los_y]
                los_y = common_utils.pad_zeros(los_y, min_length=self.ihm_pos + 1)
                los_y = np.expand_dims(los_y, axis=-1)  # (B, T, 1)
                outputs.append(los_y)

                # pheno
                pheno_y = np.array(data_batch['pheno_y'])
                outputs.append(pheno_y)
                if self.target_repl:
                    pheno_seq = np.expand_dims(pheno_y, axis=1).repeat(T, axis=1)  # (B, T, 25)
                    outputs.append(pheno_seq)

                inputs = [X, ihm_M, decomp_M, los_M]

                if self.return_y_true:
                    batch_data = (inputs, outputs, los_y_true)
                else:
                    batch_data = (inputs, outputs)

                if not self.return_names:
                    yield batch_data
                else:
                    yield {'data': batch_data,
                           'names': data_batch['name'],
                           'decomp_ts': data_batch['decom_ts'],
                           'los_ts': data_batch['los_ts'],
                           'pheno_ts': data_batch['pheno_ts']}

    def __iter__(self):
        return self.generator

    def next(self, return_y_true=False):
        with self.lock:
            self.return_y_true = return_y_true
            return next(self.generator)

    def __next__(self):
        return self.next()



class MultiModal_Batch_Gen(BatchGen):
    def __init__(self, text_reader, return_type):
        super(MultiModal_Batch_Gen, self).__init__()
        self.text_reader = text_reader
        self.waveform_reader = waveform_reader

    def read_treatment(self):
        pass

    def read_ts(self):
        for i in range(0, self.N, self.batch_size):
            outputs = []
            data_batch = self.read_batch(self.reader)
                
            for j in range(self.batch_size):
                (data_batch['X'][j], data_batch['ihm'][j], data_batch['decomp'][j],data_batch['los'][j], data_batch['pheno'][j]) = \
                    self._preprocess_single(data_batch['X'][j], data_batch['t'][j],data_batch['ihm'][j], data_batch['decomp'][j],data_batch['los'][j], data_batch['pheno'][j])
                
            data_batch['ihm_M'] = [x[0] for x in data_batch['ihm']]
            data_batch['ihm_y'] = [x[1] for x in data_batch['ihm']]
            data_batch['decomp_M'] = [x[0] for x in data_batch['decomp']]
            
            
            data_batch['decomp_y'] = [x[1] for x in data_batch['decomp']]
            data_batch['los_M'] = [x[0] for x in data_batch['los']]
            data_batch['los_y'] = [x[1] for x in data_batch['los']]
            data_batch['pheno_y'] = data_batch['pheno']


            # X
            X = data_batch['X']
            X = common_utils.pad_zeros(X, min_length=self.ihm_pos + 1)
            T = X.shape[1]

            # ihm
            ihm_M = np.array(data_batch['ihm_M'])
            ihm_M = np.expand_dims(ihm_M, axis=-1)  # (B, 1)
            ihm_y = np.array(data_batch['ihm_y'])
            ihm_y = np.expand_dims(ihm_y, axis=-1)  # (B, 1)
            outputs.append(ihm_y)
            
            if self.target_repl:
                ihm_seq = np.expand_dims(ihm_y, axis=-1).repeat(T, axis=1)  # (B, T, 1)
                outputs.append(ihm_seq)

            # decomp
            decomp_M = data_batch['decomp_M']
            decomp_M = common_utils.pad_zeros(decomp_M, min_length=self.ihm_pos + 1)
            decomp_y = data_batch['decomp_y']
            decomp_y = common_utils.pad_zeros(decomp_y, min_length=self.ihm_pos + 1)
            decomp_y = np.expand_dims(decomp_y, axis=-1)  # (B, T, 1)
            outputs.append(decomp_y)

            # los
            los_M = data_batch['los_M']
            los_M = common_utils.pad_zeros(los_M, min_length=self.ihm_pos + 1)
            los_y = data_batch['los_y']
            los_y_true = common_utils.pad_zeros(los_y, min_length=self.ihm_pos + 1)

            if self.partition == 'log':
                los_y = [np.array([metrics.get_bin_log(x, 10) for x in z]) for z in los_y]
            if self.partition == 'custom':
                los_y = [np.array([metrics.get_bin_custom(x, 10) for x in z]) for z in los_y]
            los_y = common_utils.pad_zeros(los_y, min_length=self.ihm_pos + 1)
            los_y = np.expand_dims(los_y, axis=-1)  # (B, T, 1)
            outputs.append(los_y)

            # pheno
            pheno_y = np.array(data_batch['pheno_y'])
            outputs.append(pheno_y)
            if self.target_repl:
                pheno_seq = np.expand_dims(pheno_y, axis=1).repeat(T, axis=1)  # (B, T, 25)
                outputs.append(pheno_seq)

            inputs = [X, ihm_M, decomp_M, los_M]

            if self.return_y_true:
                batch_data = (inputs, outputs, los_y_true)
            else:
                batch_data = (inputs, outputs)

            if not self.return_names:
                yield batch_data
            else:
                yield {'data': batch_data,
                        'names': data_batch['name'],
                        'decomp_ts': data_batch['decom_ts'],
                        'los_ts': data_batch['los_ts'],
                        'pheno_ts': data_batch['pheno_ts']}
