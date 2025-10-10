FROM instrumentisto/flutter:3.29.2

RUN apt-get update && \
    apt-get install -y chromium-chromedriver vim python3-pip openjdk-17-jdk && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --break-system-packages "flet[all]" && \
    yes | sdkmanager --licenses || true

ENV JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64/"
ENV CHROME_EXECUTABLE="/usr/bin/chromedriver"

#[PATH, FLUTTER_VERSION,                 
#           FLET_APP_STORAGE_DATA, CHROME_EXECUTABLE, JAVA_HOME, ANDROID_SDK_TOOLS_VERSION, FLUTTER_ROOT, TERM,      
#           FLUTTER_HOME, LANG, ANDROID_HOME, FLET_APP_STORAGE_TEMP, PWD, LANGUAGE, SERIOUS_PYTHON_SITE_PACKAGES,    
#           OLDPWD, ANDROID_SDK_ROOT, PUB_CACHE, ANDROID_PLATFORM_VERSION, ANDROID_BUILD_TOOLS_VERSION,              
#           FLUTTER_ALREADY_LOCKED, HOSTNAME, LC_ALL, FLET_ANDROID_SIGNING_KEY_ALIAS, FVM_CACHE_PATH, LS_COLORS,     
#           SHLVL, HOME]

#ENV FLET_APP_STORAGE_DATA=""
#ENV FLET_APP_STORAGE_TEMP=""
#ENV PUB_CACHE=""
#ENV FVM_CACHE_PATH=""


WORKDIR /root

RUN --mount=type=bind,source=.,target=/root/ \
    flutter build apk --release

# Copy your Flutter project into the container
#VOLUME /root/fetchfile/

#COPY . /app

# RUN flutter clean
