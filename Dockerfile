# This is the Dockerfile to set up a development environment for edu-machine-learning
#
# - Building the docker image: 
#   docker build -t edu-machine-learning .
#
# - Running the image as a container (assuming code is located in ~/code/edu-machine-learning/):
#   docker run -v ~/code/edu-machine-learning/:/edu-machine-learning/ -it edu-machine-learning

FROM python:3


ARG BASEFOLDER="/edu-machine-learning"
RUN mkdir ${BASEFOLDER}

RUN pip install wheel
RUN pip install --upgrade setuptools
#WORKDIR /usr/src/app
#RUN python3 -m pip install --upgrade https://storage.googleapis.com/tensorflow/mac/cpu/tensorflow-1.12.0-py3-none-any.whl

#RUN pip install pandas
#RUN pip install numpy
#RUN pip install matplotlib
#RUN pip install seaborn
#RUN pip install nltk
#RUN pip install scikit-learn

ENTRYPOINT [ "bash" ]