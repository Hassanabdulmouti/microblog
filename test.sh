#!/bin/sh

source .venv/bin/activate

# Wait for MySQL to be ready
while true; do
    python -c "import pymysql; pymysql.connect(host='db', user='microblog', password='password', database='microblog_test')" 2>/dev/null
    if [[ "$?" == "0" ]]; then
        break
    fi
    echo "Waiting for MySQL to be ready..."
    sleep 2
done

make test

