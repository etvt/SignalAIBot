# recommended tag: etvt/signalaibot:latest

FROM registry.gitlab.com/signald/signald:latest

ARG DEVELOPMENT=false

# build-time user
USER root


# install system dependencies
RUN apt-get update && \
    apt-get install -y python3.11-minimal python3.11-venv python3-pip python3-poetry dumb-init && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# ---------- set up signald ----------
RUN mkdir /persistent_data && mkdir /persistent_data/signald && chown -R signald:signald /persistent_data
VOLUME /persistent_data


# ---------- prepare the entrypoint and the command ----------
ADD ./docker/entrypoint.sh /usr/bin/entrypoint.sh
RUN chmod +x /usr/bin/entrypoint.sh
ADD ./docker/run-as-signald-entrypoint.sh /usr/bin/run-as-signald-entrypoint.sh
RUN chmod +x /usr/bin/run-as-signald-entrypoint.sh
ADD ./docker/signalaibot.sh /usr/bin/signalaibot.sh
RUN chmod +x /usr/bin/signalaibot.sh


# ---------- set up the bot ----------
WORKDIR /app

# install app dependencies
COPY ./pyproject.toml /app/pyproject.toml
RUN poetry config virtualenvs.create false && \
    if [ "$DEVELOPMENT" = "true" ] ; then \
        poetry install --no-root --no-cache --with dev; \
    else \
        poetry install --no-root --no-cache; \
    fi

# install the project
COPY . /app
RUN if [ "$DEVELOPMENT" = "true" ] ; then \
        poetry install --no-cache --with dev; \
    else \
        poetry install --no-cache; \
    fi


# default run-time user is root, to be able to chown mounted volumes, then we continue with signald user afterwards
ARG RUN_AS=root
USER ${RUN_AS}

ENTRYPOINT ["/usr/bin/dumb-init", "--single-child", "--", "/usr/bin/run-as-signald-entrypoint.sh"]
CMD ["/usr/bin/signalaibot.sh"]
