#!/bin/bash
# Start SQL Server in the background, wait for it, run init.sql, then keep running.
set -e

/opt/mssql/bin/sqlservr &
SQL_PID=$!

SQLCMD=""

for candidate in \
    /opt/mssql-tools/bin/sqlcmd \
    /opt/mssql-tools18/bin/sqlcmd \
    /usr/bin/sqlcmd \
    /usr/local/bin/sqlcmd
do
    if [ -x "$candidate" ]; then
        SQLCMD="$candidate"
        break
    fi
done

if [ -z "$SQLCMD" ]; then
    echo "ERROR: sqlcmd not found in container."
    echo "Looked in:"
    echo "  /opt/mssql-tools/bin/sqlcmd"
    echo "  /opt/mssql-tools18/bin/sqlcmd"
    echo "  /usr/bin/sqlcmd"
    echo "  /usr/local/bin/sqlcmd"
    wait $SQL_PID
    exit 1
fi

echo "Using sqlcmd at: $SQLCMD"
echo "Waiting for SQL Server to be ready..."

for i in $(seq 1 60); do
    "$SQLCMD" -S localhost -U SA -P "$MSSQL_SA_PASSWORD" -Q "SELECT 1" > /dev/null 2>&1 && break
    sleep 2
done

echo "Running init.sql..."
"$SQLCMD" -S localhost -U SA -P "$MSSQL_SA_PASSWORD" \
    -b -V 16 -r 1 -i /sql/init.sql

echo "Database initialized."
wait $SQL_PID