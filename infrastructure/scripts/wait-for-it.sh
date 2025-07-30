#!/usr/bin/env bash
# wait-for-it.sh - Wait for a service to become available

TIMEOUT=15
QUIET=0
WAITFORIT_CMD=""
WAITFORIT_HOST=""
WAITFORIT_PORT=""

echoerr() {
    if [[ $QUIET -ne 1 ]]; then echo "$@" 1>&2; fi
}

usage() {
    cat << USAGE >&2
Usage:
    $0 host:port [-t timeout] [-- command args]
    -h HOST | --host=HOST       Host or IP under test
    -p PORT | --port=PORT       TCP port under test
    -t TIMEOUT | --timeout=TIMEOUT
                                Timeout in seconds, zero for no timeout
    -q | --quiet                Don't output any status messages
    -- COMMAND ARGS             Execute command with args after the test finishes
USAGE
    exit 1
}

wait_for() {
    if [[ $TIMEOUT -gt 0 ]]; then
        echoerr "$0: waiting $TIMEOUT seconds for $WAITFORIT_HOST:$WAITFORIT_PORT"
    else
        echoerr "$0: waiting for $WAITFORIT_HOST:$WAITFORIT_PORT without a timeout"
    fi
    
    WAITFORIT_start_ts=$(date +%s)
    
    while :
    do
        if [[ $TIMEOUT -gt 0 ]]; then
            WAITFORIT_now_ts=$(date +%s)
            WAITFORIT_elapsed=$((WAITFORIT_now_ts - WAITFORIT_start_ts))
            
            if [[ $WAITFORIT_elapsed -ge $TIMEOUT ]]; then
                echoerr "$0: timeout occurred after waiting $TIMEOUT seconds for $WAITFORIT_HOST:$WAITFORIT_PORT"
                return 1
            fi
        fi
        
        nc -z "$WAITFORIT_HOST" "$WAITFORIT_PORT" >/dev/null 2>&1
        WAITFORIT_result=$?
        
        if [[ $WAITFORIT_result -eq 0 ]]; then
            WAITFORIT_end_ts=$(date +%s)
            echoerr "$0: $WAITFORIT_HOST:$WAITFORIT_PORT is available after $((WAITFORIT_end_ts - WAITFORIT_start_ts)) seconds"
            break
        fi
        
        sleep 1
    done
    
    return $WAITFORIT_result
}

# process arguments
while [[ $# -gt 0 ]]
do
    case "$1" in
        *:* )
        WAITFORIT_hostport=(${1//:/ })
        WAITFORIT_HOST=${WAITFORIT_hostport[0]}
        WAITFORIT_PORT=${WAITFORIT_hostport[1]}
        shift 1
        ;;
        -h)
        WAITFORIT_HOST="$2"
        shift 2
        ;;
        --host=*)
        WAITFORIT_HOST="${1#*=}"
        shift 1
        ;;
        -p)
        WAITFORIT_PORT="$2"
        shift 2
        ;;
        --port=*)
        WAITFORIT_PORT="${1#*=}"
        shift 1
        ;;
        -t)
        TIMEOUT="$2"
        shift 2
        ;;
        --timeout=*)
        TIMEOUT="${1#*=}"
        shift 1
        ;;
        -q | --quiet)
        QUIET=1
        shift 1
        ;;
        --)
        shift
        WAITFORIT_CMD="$@"
        break
        ;;
        *)
        echoerr "Unknown argument: $1"
        usage
        ;;
    esac
done

if [[ "$WAITFORIT_HOST" == "" || "$WAITFORIT_PORT" == "" ]]; then
    echoerr "Error: you need to provide a host and port to test."
    usage
fi

wait_for

WAITFORIT_result=$?
if [[ $WAITFORIT_CMD != "" ]]; then
    if [[ $WAITFORIT_result -ne 0 ]]; then
        echoerr "$0: failed to wait for $WAITFORIT_HOST:$WAITFORIT_PORT"
    fi
    exec $WAITFORIT_CMD
else
    exit $WAITFORIT_result
fi