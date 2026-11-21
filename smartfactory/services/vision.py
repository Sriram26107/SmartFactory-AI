from io import BytesIO
import numpy as np
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

def image_features(data):
    img=Image.open(BytesIO(data)).convert('RGB').resize((64,64))
    x=np.asarray(img,dtype=float)/255.0
    gray=x.mean(axis=2)
    edges=np.abs(np.diff(gray,axis=0)).mean()+np.abs(np.diff(gray,axis=1)).mean()
    return np.array([gray.mean(),gray.std(),edges,*x.mean(axis=(0,1))])

def train_image_classifier(images,labels):
    """Train on labeled bytes; both classes and >= 6 samples required."""
    if len(images)<6 or len(set(labels))<2: raise ValueError('Supply at least six labeled images from two classes')
    X=np.vstack([image_features(img) for img in images]); y=np.asarray(labels)
    model=LogisticRegression(max_iter=1000,class_weight='balanced').fit(X,y)
    return model

def classify_image(model,image_bytes):
    return {'predicted_class':str(model.predict([image_features(image_bytes)])[0]),
            'warning':'Demo feature-based classifier; validate on held-out real factory images.'}
