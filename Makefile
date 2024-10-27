.PHONY: run
run:
	docker compose up -d --build

.PHONY: lint
lint:
	flake8 --config .flake8 src

.PHONY: test

stop_postgres:
	systemctl stop postgresql
stop_apache:
	systemctl stop apache2
kill:
	setcap cap_net_bind_service=ep /usr/bin/rootlesskit
mc:
	mc