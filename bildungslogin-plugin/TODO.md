QA-Tasks
========
- is there a spec in research-library/research/bildungslogin/openapi.json
- does the fastapi stub work?
- are all required fields contained in the api?
- is the documentation for api correct?
- was the spec discussed and approved by the team?
- is there a spec?
- can you build a client from the spec using https://editor.swagger.io/?

Notes
=====

run docker:
```

GIT_REPO_PATH=~/projects/univention/univention_git/components
docker ps -aq | xargs docker rm -f
docker run --name dev -d -p 8080:8080 \
   --env-file $GIT_REPO_PATH/ucsschool-apis/docker_dev_dir/env_file \
   -v $GIT_REPO_PATH/ucsschool-apis/docker_dev_dir:/docker_dev_dir \
   -v $GIT_REPO_PATH/ucsschool-apis/settings.json:/etc/ucsschool/apis/settings.json \
   -v $GIT_REPO_PATH/ucsschool-api-plugins/id-broker-plugin/settings.json:/etc/ucsschool/apis/id_broker/settings.json \
   -v $GIT_REPO_PATH/ucsschool-api-plugins/bildungslogin-plugin:/var/lib/univention-appcenter/apps/ucsschool-apis/data/plugins/bildungslogin-plugin \
   -v $GIT_REPO_PATH/ucsschool-api-plugins/id-broker-plugin:/var/lib/univention-appcenter/apps/ucsschool-apis/data/plugins/id-broker-plugin \
   ucsschool-apis:dev
docker exec -it dev /bin/bash

sleep 2

pip uninstall -y bildungslogin-plugin
pip install poetry
poetry config virtualenvs.create false
cd /var/lib/univention-appcenter/apps/ucsschool-apis/data/plugins/bildungslogin-plugin
poetry install


rc-service ucsschool-apis stop
uvicorn --reload ucsschool.apis.main:app --host 0.0.0.0 --port 8080 --log-level debug




```

Fragen
======
- conftest.py - wie kommen wir an den geteilten Kram ran
- user etc. erhalten - sollten wir da nicht auch eine Bibliothek für haben?
