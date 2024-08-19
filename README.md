# Queue Limiters
## A bandwidth limiters' manager to manage simple-queues configured on one or more Mikrotik devices.

This started as a quick and practical solution to reduce the work load and avoid recurring errors while editing simple queues in multiple Mikrotik routers that are performing bandwidth limiting for customers of an ISP.

### Changes in V3:
- Exception handling.
- Hide Routers passwords.
- Updated versions of Django/Gunicorn and Python.
- Some bug fixes applied.
- Code revision/linting

### Changes in V2:

- Ability to define multiple groups of limiter routers (each group will synchronize separately but duplicate simple queue names are not allowed).
- Updated versions of Django/Gunicorn and Python.
- Some bug fixes applied.

### Limitations:

- Before using this app, currently configured [Queue types] and [Simple queues] must be matched in each router that will be added to the same group, or else after adding the first one, the next added routers will stay in a "sync" state, which means the app will not attempt to apply any changes to them when editing simple queues later.
- This app doesn't have a user entry evaluation mechanism yet, so when editing or configuring new simple queues, care must be taken to avoid errors (usually you will get a Server Error (500) if the command was rejected by the Mikrotik router).
- In the event of Server Error (500), just click the back button in your browser and check for errors.
- For creating new simple queue, the recommended approach is to edit an existing one, then click (Save as new) instead of (Save).


### Installation:

1. `apt install docker-compose`
2. `cd /opt`
3. `git clone https://github.com/m-manar-d/mt_queue_mgr.git`
4. `cd mt_queue_mgr`
5. `nano .env`    # edit as needed
6. `cp sample.yml docker-compose.yml`
7. `docker-compose build`
8. `docker-compose up -d`
9. `docker exec -it  mt_queue_mgr python manage.py collectstatic`
10. `docker exec -it  mt_queue_mgr python manage.py makemigrations`
11. `docker exec -it  mt_queue_mgr python manage.py migrate`
12. `http://ip-address`
13. `Before you start adding Mikrotiks to limiter's list, for every router of the same group make sure that:`
	`- They have the same entries in: \queue\type\export`
        `- They have the same entries in: \queue\simple\export`
        `- Import the proper gx.placeholder-queues.rsc file`

### Notes:

- This installation will run two containers, one for NGINX as a reverse-proxy and a second for the app.
- In step 5, it is very important to change the SECRET_KEY and admin credentials that will be used to login to the app. also edit DIRPATH in case you want a different installation path.
- If you are already using Docker, you can copy from sample.yml to your main docker-compose.yml and edit as needed; in this case, you will not need steps 1 and 6 to 8.
- If you are already using NGINX reverse-proxy, you can check nginx/conf/first.conf and copy/edit what you need to your NGINX config file.
- This was tested on Debian 12.
- Many thanks to: [github: RouterOS-API](https://github.com/socialwifi/RouterOS-api) and [pypy: RouterOS-api](https://pypi.org/project/RouterOS-api/)
- Please check [App usage snapshots](https://github.com/m-manar-d/mt_queue_mgr/discussions/5)

### Finally, any suggestion or advice is welcome and appreciated :)

[![Django CI](https://github.com/m-manar-d/mt_queue_mgr/actions/workflows/django.yml/badge.svg)](https://github.com/m-manar-d/mt_queue_mgr/actions/workflows/django.yml)
[![Pylint](https://github.com/m-manar-d/mt_queue_mgr/actions/workflows/pylint.yml/badge.svg)](https://github.com/m-manar-d/mt_queue_mgr/actions/workflows/pylint.yml)
[![CodeQL](https://github.com/m-manar-d/mt_queue_mgr/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/m-manar-d/mt_queue_mgr/actions/workflows/github-code-scanning/codeql)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
