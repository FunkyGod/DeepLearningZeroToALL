#coding:utf-8
# sys
import torch
import pandas as pd 
import numpy as np
import sys
from torch.autograd import Variable
import tqdm
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

#user


use_cuda = torch.cuda.is_available()
BASE_FOLDER = 'D:/dataset/kaggle_Iceberg'

def generateSingleModel(model,train_loader, val_loader, train_ds, val_ds,LR,num_epoches):
    use_cuda = torch.cuda.is_available()
    loss_func = torch.nn.BCELoss()  # Binary cross entropy: http://pytorch.org/docs/nn.html#bceloss

    optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=5e-5)  # L2 regularization
    
    model.cuda()
    loss_func.cuda()

    # lgr.info(optimizer)
    # lgr.info(loss_func)

    criterion = loss_func
    all_losses = []
    val_losses = []

    for epoch in range(num_epoches):
        # print('Epoch {}'.format(epoch + 1))
        # print('*' * 5 + ':')
        running_loss = 0.0
        running_acc = 0.0
        for i, row_data in enumerate(train_loader, 1):
            img, label = row_data
            # img = row_data['image']
            # label = row_data['labels']
            if use_cuda:
                img, label = Variable(img.cuda(async=True)), Variable(label.cuda(async=True))  # On GPU
            else:
                img, label = Variable(img), Variable(label)  # RuntimeError: expected CPU tensor (got CUDA tensor)

            out = model(img)
            loss = criterion(out, label)
            running_loss += loss.data[0] * label.size(0)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        #     if i % 10 == 0:
        #         all_losses.append(running_loss / (batch_size * i))
        #         print('[{}/{}] Loss: {:.6f}'.format(
        #             epoch + 1, num_epoches, running_loss / (batch_size * i),
        #             running_acc / (batch_size * i)))
        #
        # print('Finish {} epoch, Loss: {:.6f}'.format(epoch + 1, running_loss / (len(train_ds))))

        model.eval()
        eval_loss = 0
        eval_acc = 0
        for row_data in val_loader:
            img, label = row_data
            # img = row_data['image']
            # label = row_data['labels']
            if use_cuda:
                img, label = Variable(img.cuda(async=True), volatile=True), Variable(label.cuda(async=True),volatile=True)  # On GPU
            else:
                img = Variable(img, volatile=True)
                label = Variable(label, volatile=True)
            out = model(img)
            loss = criterion(out, label)
            eval_loss += loss.data[0] * label.size(0)

        val_losses.append(eval_loss / (len(val_ds)))
        # print('VALIDATION Loss: {:.6f}'.format(eval_loss / (len(val_ds))))
        # print()

    print('TRAIN Loss: {:.6f}'.format(running_loss / (len(train_ds))))
    print('VALIDATION Loss: {:.6f}'.format(eval_loss / (len(val_ds))))
    print ("LR:%f"%LR)
    val_result = (eval_loss / (len(val_ds)))
    train_result = (running_loss / (len(train_ds)))
    # torch.save(model.state_dict(), './pth/' + val_result + '_cnn.pth')

    return model, val_result,train_result


def testModel(model):
    df_test_set = pd.read_json(BASE_FOLDER + '/test.json')
    df_test_set['band_1'] = df_test_set['band_1'].apply(lambda x: np.array(x).reshape(75, 75))
    df_test_set['band_2'] = df_test_set['band_2'].apply(lambda x: np.array(x).reshape(75, 75))
    df_test_set['inc_angle'] = pd.to_numeric(df_test_set['inc_angle'], errors='coerce')
    df_test_set.head(3)
    print(df_test_set.shape)
    columns = ['id', 'is_iceberg']
    df_pred = pd.DataFrame(data=np.zeros((0, len(columns))), columns=columns)
    # df_pred.id.astype(int)
    for index, row in df_test_set.iterrows():
        rwo_no_id = row.drop('id')
        band_1_test = (rwo_no_id['band_1']).reshape(-1, 75, 75)
        band_2_test = (rwo_no_id['band_2']).reshape(-1, 75, 75)
        full_img_test = np.stack([band_1_test, band_2_test], axis=1)

        x_data_np = np.array(full_img_test, dtype=np.float32)
        if use_cuda:
            X_tensor_test = Variable(torch.from_numpy(x_data_np).cuda())  # Note the conversion for pytorch
        else:
            X_tensor_test = Variable(torch.from_numpy(x_data_np))  # Note the conversion for pytorch

        # X_tensor_test=X_tensor_test.view(1, trainX.shape[1]) # does not work with 1d tensors
        predicted_val = (model(X_tensor_test).data).float()  # probabilities
        p_test = predicted_val.cpu().numpy().item()  # otherwise we get an array, we need a single float

        df_pred = df_pred.append({'id': row['id'], 'is_iceberg': p_test}, ignore_index=True)

    return df_pred
