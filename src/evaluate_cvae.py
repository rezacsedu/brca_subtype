import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import confusion_matrix
import matplotlib.pyplot as plt
from sklearn.preprocessing import OneHotEncoder
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.utils import to_categorical

from vae import VAE, ConditionalVAE



X_tcga_no_brca = pd.read_csv("../data/tcga_filtered_no_brca.csv")
x_tcga_type_no_brca = pd.read_csv("../data/tcga_tumor_type.csv")
x_tcga_type_no_brca = x_tcga_type_no_brca[x_tcga_type_no_brca.tumor_type != "BRCA"]

###############
## Load Data ##
###############

X_brca_train = pd.read_csv("../data/ciriello_brca_filtered_train.csv")
X_brca_train = X_brca_train[X_brca_train.Ciriello_subtype != "Normal"]

y_brca_train = X_brca_train["Ciriello_subtype"]

X_brca_train.drop(['Ciriello_subtype'], axis="columns", inplace=True)

# Test data
X_brca_test = pd.read_csv("../data/tcga_brca_filtered_test.csv")
X_brca_test = X_brca_test[X_brca_test.subtype != "Normal"]
y_brca_test = X_brca_test["subtype"]

X_brca_test.drop(['subtype'], axis="columns", inplace=True)

#############################
## 5-Fold Cross Validation ##
#############################
'''
confusion_matrixes = []
validation_set_percent = 0.1
scores = []


skf = StratifiedKFold(n_splits=5)
i=1
classify_df = pd.DataFrame(columns=["Fold", "accuracy"])

for train_index, test_index in skf.split(X_brca_train, y_brca_train):
	print('Fold {} of {}'.format(i, skf.n_splits))

	X_train, X_val = X_brca_train.iloc[train_index], X_brca_train.iloc[test_index]
	y_train, y_val = y_brca_train.iloc[train_index], y_brca_train.iloc[test_index]

	# Prepare data to train Variational Autoencoder (merge dataframes and normalize)
	X_autoencoder = pd.concat([X_train, X_tcga_no_brca], sort=True)
	X_train_tumor_type = pd.DataFrame(data=["BRCA"]*len(X_train), columns=["tumor_type"])
	X_autoencoder_tumor_type = pd.concat([X_train_tumor_type, x_tcga_type_no_brca], sort=True)

	scaler = MinMaxScaler()
	scaler.fit(X_autoencoder)
	X_autoencoder_scaled = pd.DataFrame(scaler.transform(X_autoencoder), columns=X_autoencoder.columns)

	# Scale logistic regression data
	scaler.fit(X_train)
	X_train = pd.DataFrame(scaler.transform(X_train), columns=X_train.columns)
	X_val = pd.DataFrame(scaler.transform(X_val), columns=X_val.columns)

	#Split validation set
	X_autoencoder_train, X_autoencoder_val, X_autoencoder_tumor_type_train, X_autoencoder_tumor_type_val = train_test_split(X_autoencoder_scaled, X_autoencoder_tumor_type, test_size=validation_set_percent, stratify=X_autoencoder_tumor_type, random_state=42)


	# Order the features correctly before training
	X_train = X_train.reindex(sorted(X_train.columns), axis="columns")
	X_val = X_val.reindex(sorted(X_val.columns), axis="columns")


	#Train the Model
	cvae = ConditionalVAE(original_dim=X_autoencoder_train.shape[1], intermediate_dim=300, latent_dim=100, epochs=100, batch_size=50, learning_rate=0.001)
	cvae.initialize_model()
	cvae.train_cvae(train_df=X_autoencoder_train, 
					train_cond_df=pd.get_dummies(X_autoencoder_tumor_type_train), 
					val_df=X_autoencoder_val,
					val_cond_df=pd.get_dummies(X_autoencoder_tumor_type_val))


	# Build and train stacked classifier
	enc = OneHotEncoder(sparse=False)
	y_labels_train = enc.fit_transform(y_train.values.reshape(-1, 1))
	y_labels_val = enc.fit_transform(y_val.values.reshape(-1, 1))

	X_train_train, X_train_val, y_labels_train_train, y_labels_train_val = train_test_split(X_train, y_labels_train, test_size=0.2, stratify=y_train, random_state=42)

	tumors = X_autoencoder_tumor_type_train["tumor_type"].unique()


	X_train_train_tumor_type = pd.DataFrame(0, index=np.arange(len(X_train_train)), columns=tumors)
	X_train_train_tumor_type["BRCA"]=1
	X_train_val_tumor_type = pd.DataFrame(0, index=np.arange(len(X_train_val)), columns=tumors)
	X_train_val_tumor_type["BRCA"]=1
    
	X_val_tumor_type = pd.DataFrame(0, index=np.arange(len(X_val)), columns=tumors)
	X_val_tumor_type["BRCA"]=1


	fit_hist = cvae.classifier.fit(x=[X_train_train, X_train_train_tumor_type], 
									y=y_labels_train_train, 
									shuffle=True, 
									epochs=100,
									batch_size=50,
									callbacks=[EarlyStopping(monitor='val_loss', patience=10)],
									validation_data=([X_train_val, X_train_val_tumor_type], y_labels_train_val))

	score = cvae.classifier.evaluate([X_val, X_val_tumor_type], y_labels_val)

	print(score)
	scores.append(score[1])

	classify_df = classify_df.append({"Fold":str(i), "accuracy":score[1]}, ignore_index=True)
	history_df = pd.DataFrame(fit_hist.history)
	history_df.to_csv("../parameter_tuning/cvae_tcga_classifier_cv_history_"+str(i)+".csv", sep=',')
	i+=1

print('5-Fold results: {}'.format(scores))
print('Average accuracy: {}'.format(np.mean(scores)))


classify_df = classify_df.assign(mean_accuracy=np.mean(scores))
classify_df = classify_df.assign(intermediate_dim=cvae.intermediate_dim)
classify_df = classify_df.assign(latent_dim=cvae.latent_dim)
classify_df = classify_df.assign(batch_size=cvae.batch_size)
classify_df = classify_df.assign(epochs_vae=cvae.epochs)
classify_df = classify_df.assign(learning_rate=cvae.learning_rate)

output_filename="../parameter_tuning/cvae_tcga_classifier_cv.csv"
classify_df.to_csv(output_filename, sep=',')
'''

#################################
## Build and train final model ##
#################################

classify_df = pd.DataFrame(columns=["accuracy", "conf_matrix"])

# Prepare data to train Variational Autoencoder (merge dataframes and normalize)
X_autoencoder = pd.concat([X_brca_train, X_tcga_no_brca], sort=True)
X_brca_tumor_type = pd.DataFrame(data=["BRCA"]*len(X_brca_train), columns=["tumor_type"])
X_autoencoder_tumor_type = pd.concat([X_brca_tumor_type, x_tcga_type_no_brca], sort=True)

scaler = MinMaxScaler()
scaler.fit(X_autoencoder)
X_autoencoder_scaled = pd.DataFrame(scaler.transform(X_autoencoder), columns=X_autoencoder.columns)

# Scale logistic regression data
scaler.fit(X_brca_train)
X_brca_train_scaled = pd.DataFrame(scaler.transform(X_brca_train), columns=X_brca_train.columns)
X_brca_test_scaled = pd.DataFrame(scaler.transform(X_brca_test), columns=X_brca_test.columns)

X_brca_train_scaled = X_brca_train_scaled.reindex(sorted(X_brca_train_scaled.columns), axis="columns")
X_brca_test_scaled = X_brca_test_scaled.reindex(sorted(X_brca_test_scaled.columns), axis="columns")

cvae = ConditionalVAE(original_dim=X_autoencoder_scaled.shape[1], intermediate_dim=300, latent_dim=100, epochs=100, batch_size=50, learning_rate=0.001)
cvae.initialize_model()
cvae.train_cvae(train_df=X_autoencoder_scaled, 
				train_cond_df=pd.get_dummies(X_autoencoder_tumor_type), 
				val_df=pd.DataFrame(),
				val_cond_df=pd.DataFrame(),
				val_flag=False)

enc = OneHotEncoder()
y_labels_train = enc.fit_transform(y_brca_train.values.reshape(-1, 1))
y_labels_test = enc.fit_transform(y_brca_test.values.reshape(-1, 1))

tumors = X_autoencoder_tumor_type["tumor_type"].unique()

X_train_tumor_type = pd.DataFrame(0, index=np.arange(len(X_brca_train_scaled)), columns=tumors)
X_train_tumor_type["BRCA"]=1
X_test_tumor_type = pd.DataFrame(0, index=np.arange(len(X_brca_test_scaled)), columns=tumors)
X_test_tumor_type["BRCA"]=1

fit_hist = cvae.classifier.fit(x=[X_brca_train_scaled, X_train_tumor_type], 
								y=y_labels_train, 
								shuffle=True, 
								epochs=40,
								batch_size=50)

final_score = cvae.classifier.evaluate([X_brca_test_scaled, X_test_tumor_type], y_labels_test)

confusion = confusion_matrix(y_labels_test, cvae.classifier.predict([X_brca_test_scaled, X_test_tumor_type]))

classify_df = classify_df.append({"accuracy":final_score[1], "conf_matrix":confusion}, ignore_index=True)
history_df = pd.DataFrame(fit_hist.history)
history_df.to_csv("../parameter_tuning/cvae_tcga_classifier_history_FINAL.csv", sep=',')
i+=1

print('FINAL ERROR: {}'.format(final_score[0]))
print('ACCURACY: {}'.format(final_score[1]))

classify_df = classify_df.assign(intermediate_dim=cvae.intermediate_dim)
classify_df = classify_df.assign(latent_dim=cvae.latent_dim)
classify_df = classify_df.assign(batch_size=cvae.batch_size)
classify_df = classify_df.assign(epochs_vae=cvae.epochs)
classify_df = classify_df.assign(learning_rate=cvae.learning_rate)

output_filename="../parameter_tuning/cvae_tcga_classifier_FINAL.csv"
classify_df.to_csv(output_filename, sep=',')

