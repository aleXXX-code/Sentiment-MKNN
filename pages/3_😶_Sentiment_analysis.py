import PIL.Image as Image
import numpy as np
import streamlit as st
import re, unicodedata

from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from wordcloud import WordCloud, ImageColorGenerator
from nltk.sentiment.vader import SentimentIntensityAnalyzer
#from transformers import pipeline
from sklearn.model_selection import train_test_split, KFold
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from models.MKNN import ModifiedKNN
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score
from sklearn.metrics import f1_score, recall_score
from heapq import nsmallest as nMin

import matplotlib.pyplot as plt
import matplotlib
from stqdm import stqdm

matplotlib.use("Agg")
import seaborn as sns
import plotly.express as px

import pandas as pd
import json
from collections import Counter
from soupsieve import select

import base64
import time


### SENTIMENT ANALYSIS ###
def Sentiment_analysis():
    df = pd.read_csv('output/Clean_text.csv', encoding='utf-8')

    # LexiconVader dengan custom Lexicon(bahasa indonesia)
    sia1A, sia1B = SentimentIntensityAnalyzer(), SentimentIntensityAnalyzer()
    # Hapus Default lexicon VADER
    sia1A.lexicon.clear()
    sia1B.lexicon.clear()

    # Read custom Lexicon Bahasa Indonesia
    data1A = open('data/lexicon_sentimen_negatif.txt', 'r').read()
    data1B = open('data/lexicon_sentimen_positif.txt', 'r').read()
    # convert lexicon to dictonary
    insetNeg = json.loads(data1A)
    insetPos = json.loads(data1B)

    # update lexicon vader with custom lexicon (b.indo)
    sia1A.lexicon.update(insetNeg)
    sia1B.lexicon.update(insetPos)

    # method untuk cek apa sentimen pos,neg,neu
    def is_positive_inset(Text: str) -> bool:
        return sia1A.polarity_scores(Text)["compound"] + sia1B.polarity_scores(Text)["compound"] >= 0.05

    tweets = df['text'].to_list()

    with open('output/Sentiment-result.txt', 'w+') as f:
        for tweet in tweets:
            label = "Positive" if is_positive_inset(tweet) else "Negative"
            f.write(str(label + "\n"))

    sen = pd.read_csv('output/Sentiment-result.txt', names=['Sentiment'])
    df = df.join(sen)

    ## Save clean Dataset
    df.to_csv('CleanText_Sentiment.csv', index=False)
    return df

def TFIDF_word_weight(vect, word_weight):
    feature_name = np.array(vect.get_feature_names_out())
    data = word_weight.data
    indptr = word_weight.indptr
    indices = word_weight.indices
    n_docs = word_weight.shape[0]

    word_weght_list = []
    for i in range(n_docs):
        doc = slice(indptr[i], indptr[i + 1])
        count, idx = data[doc], indices[doc]
        feature = feature_name[idx]
        word_weght_dict = dict(dict(zip(feature, count)))
        word_weght_list.append(word_weght_dict)
    return word_weght_list

def plot_conf_metrics(y_test, pred,):
    mx = confusion_matrix(y_test, pred)
    plt.figure(figsize=(2,2))
    sns.heatmap(mx, annot=True,cmap="Blues", fmt="g")
    plt.xlabel('Predicted'); plt.ylabel('Y test'); plt.title('Confusion Matrix')
    st.set_option('deprecation.showPyplotGlobalUse', False)
    st.pyplot()
    #recall = (TP) / (TP + FN)
    #f1_score = (2 * precision * recall) / (precision + recall)

# Extract the most common word in each emotion
def extract_keyword(Text, num=50):
    tokens = list(Text.split())
    most_common_tokens = Counter(tokens).most_common(num)
    return dict(most_common_tokens)

# Visualize Keuyword with WorldCloud
def visual_WordCould(Text):
    mask = np.array(Image.open('data/mask.jpg'))
    mywordcould = WordCloud(background_color="white", max_words=1000, mask=mask).generate(Text)
    img_color = ImageColorGenerator(mask)
    fig = plt.figure(figsize=(20, 10))
    plt.imshow(mywordcould.recolor(color_func=img_color), interpolation='bilinear')
    plt.axis('off')
    st.pyplot(fig)

# Visualize Keyword with plot
def plot_most_common_word(mydict, emotion_name):
    df_emotion = pd.DataFrame(mydict.items(), columns=['token', 'count'])
    fig = px.bar(df_emotion, x='token', y='count', color='token', height=500, labels=emotion_name)
    st.plotly_chart(fig)

#############################################################################################################

timestr = time.strftime("%Y%m%d-%H%M%S")

#Download Preprocessing Result
def download_result(Text):
    st.markdown("### Download File ###")
    newFile = f"Clean_dataset_{timestr}_.csv"
    newFile2 = f"Clean_dataset_{timestr}_.txt"
    save_df = Text.to_csv(index=False)
    b64 = base64.b64encode(save_df.encode()).decode()
    href2 = f'<a download="{newFile2}" href="data:text/txt;base64,{b64}">🔰Download .txt</a>'
    href = f'<a download="{newFile}" href="data:text/csv;base64,{b64}">🔰Download .csv</a>'
    st.markdown(href2, unsafe_allow_html=True)
    st.markdown(href, unsafe_allow_html=True)

def main():
    #Page Config
    st.set_page_config(page_title="Sentiment Analysis", page_icon="😶", layout='wide')
    st.title('Sentiment Analysis Twitter')
    st.markdown('This application is all about sentiment analysis of movie Review. All data is Crawling from Twitter')
    st.sidebar.title('Sentiment Analysis Movie Review')
    #hide table index and footer
    Page_config = """
            <style>
            thead tr th:first-child {display:none}
            tbody th {display:none}
            footer {visibility: hidden;}
            </style>
            """
    st.markdown(Page_config, unsafe_allow_html=True)

    #Preprocessing Process
    st.subheader("Preprocessing")
    df_file = st.file_uploader("Upload a dataset to clean", type=['csv'])

    def load_data():
        data = pd.read_csv(df_file, encoding='latin1')
        data = data[['user_name', 'date', 'text']]
        data['date'] = pd.to_datetime(data['date'])
        return data

    def casefolding(Text):
        Text = Text.lower()
        return Text

    # Punctuation Removal
    def punc_clean(Text):
        #remove url
        Text = re.sub(r'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’]))', '', Text)
        #remove mention
        Text = re.sub(r"@[A-Za-z0-9]+","", Text)
        #remove hastag
        Text = re.sub(r"#[A-Za-z0-9_]+","", Text)
        #punchuation
        Text = re.sub(r'[^\w]|_', ' ', Text)
        #remove number in string
        Text = re.sub(r"\S*\d\S*", "", Text).strip()
        #remove number(int/float)
        Text =  re.sub(r"[0-9]", " ", Text)
        Text = re.sub(r"\b\d+\b", " ", Text)
        #remove double Space
        Text = re.sub(r'[\s]+', ' ', Text)
        #remove non-ASCII
        Text = unicodedata.normalize('NFKD', Text).encode('ascii', 'ignore').decode('utf-8', 'ignore')
        Text = ' '.join( [w for w in Text.split() if len(w)>1] )
        return Text

    @st.cache
    def word_norm(tweets):
        word_dict = pd.read_csv('data/indonesia_slangWords.csv')
        norm_word_dict = {}
        for index, row in word_dict.iterrows():
            if row[0] not in norm_word_dict:
                norm_word_dict[row[0]] = row[1]
        return [norm_word_dict[term] if term in norm_word_dict else term for term in tweets]

    # Tokenize
    def word_tokenize_wrapper(Text):
        return word_tokenize(Text)

    # Stopwords
    def remove_stopword(Text):
        stopW = stopwords.words('indonesian', 'english')
        sw = pd.read_csv('data/stopwordbahasa.csv')
        stopW.extend(sw)
        remove_sw = ' '.join(Text)
        clean_sw = [word for word in remove_sw.split() if word.lower() not in stopW]
        return clean_sw

    ## Indonesia Stemming
    @st.cache(suppress_st_warning=True)
    def indo_stem(Text):
        factory = StemmerFactory()
        stemmer = factory.create_stemmer()
        result = []
        for w in Text:
            result.append(stemmer.stem(w))
            result.append(" ")
        return " ".join(result)

    if df_file is not None:
        raw_text = load_data()

        file_details = {"Filename": df_file.name, "Filesize": df_file.size, "Filetype": df_file.type}
        st.success(f'{str(raw_text.shape[0])} Dataset Loaded')
        st.write(file_details)

        # Show Dataset
        with st.expander("Original Text"):
            st.write(raw_text)

        #Preprocessing Result
        with st.spinner("Wait Preprocessing text in progress"):
            with st.expander("Pre-processing"):
                st.subheader('Case Folding (lower case)')
                raw_text['text'] = raw_text['text'].apply(casefolding)
                st.dataframe(raw_text['text'])

                st.subheader("Remove Punctuations,url,numbers,emoji,and Special Character")
                raw_text['text'] = raw_text['text'].apply(punc_clean)
                st.dataframe(raw_text['text'])

                st.subheader("Tokenization")
                raw_text['text'] = raw_text['text'].apply(word_tokenize_wrapper)
                st.table(raw_text['text'].head(5))

                st.subheader("Normalisation")
                raw_text['text'] = raw_text['text'].apply(word_norm)
                st.table(raw_text['text'].head(5))

                st.subheader("Stopword")
                raw_text['text'] = raw_text['text'].apply(remove_stopword)
                st.table(raw_text['text'].head(5))

                st.subheader("Stemming Sastrawi")
                raw_text['text'] = raw_text['text'].apply(indo_stem)
                st.dataframe(raw_text['text'])

                download_result(raw_text)
                raw_text.to_csv('output/Clean_text.csv')

        #Train Sentiment labeling
        with st.expander("Train Labeling"):
            sen_result = Sentiment_analysis()
            st.dataframe(sen_result)
            sen_result.to_csv('output/sentiment_result.csv', index=False)

        # K Fold cross validation & MKNN
        with st.expander("Klasifikasi menggunakan K-FOLD"):
            k_value = st.sidebar.slider('Nilai K ',0,25,3)

            new_df = pd.read_csv('output/sentiment_result.csv')
            X = new_df['text'].values
            y = new_df['Sentiment'].values
            fold_i = 1
            combo_value = {3:"3 Fold", 5:'5 Fold', 7:'7 Fold', 10:'10 Fold'}
            fold_n = st.sidebar.selectbox('Nilai Fold', options=combo_value.keys(), format_func=lambda x:combo_value[x])
            sum_accuracy = 0
            kfold = KFold(fold_n, shuffle=True, random_state=42)
            enc = LabelEncoder()
            fol = []
            cm_result = list()
            acc, rc, pr, f1 = [], [], [], []
            # K-Fold
            for train_index, test_index in kfold.split(X):
                #st.write("Fold : ", fold_i)
                fol.append(fold_i)
                #st.write("Train :", train_index.shape, "Test :",test_index.shape)
                X_train = X[train_index]
                y_train = y[train_index]
                X_test = X[test_index]
                y_test = y[test_index]

                svf = open('output/ResultX.txt', 'w')
                sv_text = '\n'.join(str(item) for item in X_test).replace("   "," ")
                svf.write(sv_text)
                svY = open ('output/y_train.txt', 'w')
                svY.write('\n'.join(str(item) for item in y_train))

                #TFIDF
                tf = TfidfVectorizer(decode_error="replace")
                X_train = tf.fit_transform(X_train)
                X_test = tf.transform(X_test)
                
                y_train = enc.fit_transform(y_train)
                y_test = enc.transform(y_test)

                # Algorithm
                clf = ModifiedKNN(k_value)
                clf.fit(X_train, y_train)
                pred, jarak = clf.predict(X_test)
                neigbor_index = clf.get_neigbors(X_test)

                # Confusion Matrix
                #cm = confusion_matrix(y_test, pred)
                accuracy = accuracy_score(y_test, pred)*100
                precision = precision_score(y_test, pred)*100
                recall = recall_score(y_test, pred)*100
                f1_scores = f1_score(y_test, pred)*100
                #plot_conf_metrics(y_test, pred)

                sum_accuracy += accuracy

                fold_i += 1
                acc.append(accuracy)
                pr.append(precision)
                rc.append(recall)
                f1.append(f1_scores)
                #cm_result.append(cm)
            
            with open("output/MKNN_prediction.txt", "w") as f:
                mknn_predited_label ='\n'.join(str(item) for item in pred)
                f.write(mknn_predited_label)
            with open('output/jarak_ttg.txt', 'w') as g:
                jarak = [nMin(k_value,map(float,i)) for i in jarak]
                mknn_distance = '\n'.join(str(ls) for ls in jarak)
                g.write(mknn_distance)
            with open('output/index_ttg.txt', 'w') as j:
                j.write('\n'.join(str(a) for a in neigbor_index))
            #st.write(cm_result)
            knn_pred = pd.read_csv('output/MKNN_prediction.txt', names=['Sentiment'])
            jarak_pred = pd.read_csv('output/jarak_ttg.txt', names=['Distance'], sep='\t')
            text_test = pd.read_csv('output/ResultX.txt', names=['text'])
            index_pred = pd.read_csv('output/index_ttg.txt', names=['Neigbor'])
            text_test = text_test.join(knn_pred)
            text_test = text_test.join(jarak_pred)
            text_test = text_test.join(index_pred)
            text_test['Sentiment'] = text_test['Sentiment'].apply(lambda x: 'Positive' if x == 1 else 'Negative')
            text_test = text_test.dropna()
            st.dataframe(text_test)
            new_frame = pd.DataFrame(X_test)
            new_frame = new_frame.join(knn_pred)

            avg_acc = sum_accuracy/fold_n
            maxs = max(acc)
            mins = min(acc)
            res_df = pd.DataFrame({'K Fold':fol, 'Accuracy': acc, 'Precison':pr, 'Recall':rc, 'f1 score':f1})
            st.table(res_df)
            st.write("Avearge accuracy : ", str("%.4f" % avg_acc)+'%')
            st.write("Max Score : ",str(maxs),"in Fold : ", str(acc.index(maxs)+1))
            st.write("Min Score : ",str(mins), "in Fold : ", str(acc.index(mins)+1))
            st.line_chart(res_df[['Accuracy', 'Precison', 'Recall', 'f1 score']])
            
        with st.expander("Tweets Sentiment Visualize"):
            st.sidebar.markdown("Sentiment and Emotion Plot")
            sen_y_train = pd.read_csv('output/y_train.txt', names=['Sentiment'])
            text_list = pd.read_csv('output/ResultX.txt', names=['text'])
            sen_y_test = pd.read_csv('output/MKNN_prediction.txt', names=['Sentiment'])
            new_senti = pd.concat([sen_y_train, sen_y_test], ignore_index=True)
            new_df = text_list.join(new_senti)
            sen_list = new_df['Sentiment'].unique().tolist()
            #new_df = new_df.append(sen_y_test[['Sentiment']])

            sentiment = new_df['Sentiment'].value_counts()
            sentiment = pd.DataFrame({'Sentiment': sentiment.index, 'Tweets': sentiment.values})
            select = st.sidebar.selectbox("Visual of Tweets Sentiment", ['Histogram', 'Wordcloud', 'Pie Chart'],
                                            key=0)
            if select == "Wordcloud":
                ch = st.sidebar.selectbox("Sentiment", ("Positive, Negative"))
                if ch == 'Positive':
                    pos_list = new_df[new_df['Sentiment'] == 'Positive']['text'].tolist()
                    pos_docx = ' '.join(pos_list)
                    keyword_pos = extract_keyword(pos_docx)
                    visual_WordCould(pos_docx)
                    plot_most_common_word(keyword_pos, "Positive")
                else:
                    neg_list = new_df[new_df['Sentiment'] == 'Negative']['text'].tolist()
                    neg_docx = ' '.join(neg_list)
                    keyword_neg = extract_keyword(neg_docx)
                    visual_WordCould(neg_docx)
                    plot_most_common_word(keyword_neg, "Negative")
            elif select == "Histogram":
                st.subheader("Sentiment Plot")
                fig = px.bar(sentiment, x='Sentiment', y='Tweets', color='Tweets', height=500)
                st.plotly_chart(fig)
            else:
                fig = px.pie(sentiment, values='Tweets', names='Sentiment')
                st.plotly_chart(fig)

if __name__ == "__main__":
    main()
