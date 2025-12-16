#!/bin/bash

LOG_USER="gtladmin"
TMP_PWD=$(basename "$PWD")
SCRIPT_CONTEXT_NAME=$(basename "$(dirname "$0")")
LOG_DIR="/home/$LOG_USER/Log/$TMP_PWD"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="$LOG_DIR/$TIMESTAMP.log"

mkdir -p "$LOG_DIR"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== szkript indítása: $0 ==="
echo "Minden kimenet logolva ide: $LOG_FILE"
echo "---------------------------------------------------------"

CHECK_CONTAINERS="z2mqtt2http"

check_and_recover_container() {
    local container=$1
    local timeout=20
    
    echo "Checking state of $container..."
    container_status=$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null)
    
    if [[ "$container_status" != "running" ]]; then
        echo "Warning: $container is not running ($container_status). Attempting recovery..."
        docker compose down "$container" && docker compose up -d "$container"
        sleep $timeout
        
        container_status=$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null)
        [[ "$container_status" != "running" ]] && { echo "Recovery failed"; return 1; }
    fi
    
    echo "$container is running normally"
    return 0
}

# Function to verify container readiness
check_container_ready() {
    local container=$1
    local timeout=30

    for ((i=0; i<timeout; i++)); do
        container_status=$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null)
        health_status=$(docker inspect -f '{{.State.Health.Status}}' "$container" 2>/dev/null)
        
        if [[ "$container_status" == "running" && ("$health_status" == "healthy" || -z "$health_status") ]]; then
            echo "$container is ready"
            return 0
        fi
        sleep 1
    done
    
    echo "Timeout: $container not ready"
    return 1
}

set_iptables_rules() {
    local container=$1

    docker exec -it $container ip route del 10.10.30.0/24 via 172.30.10.30 2>/dev/null
    docker exec -it $container ip route del 10.10.40.0/24 via 172.30.100.40 2>/dev/null
    docker exec -it $container ip route del 10.10.45.0/24 via 172.30.100.45 2>/dev/null
    docker exec -it $container ip route del 10.10.50.0/24 via 172.30.100.50 2>/dev/null

    docker exec -it $container ip route add 10.10.30.0/24 via 172.30.10.30 2>/dev/null
    docker exec -it $container ip route add 10.10.40.0/24 via 172.30.100.40 2>/dev/null
    docker exec -it $container ip route add 10.10.45.0/24 via 172.30.100.45 2>/dev/null
    docker exec -it $container ip route add 10.10.50.0/24 via 172.30.100.50 2>/dev/null
    #sudo docker exec  -it z2mqtt2http ip route add 10.10.50.0/24 via 172.100.10.50
}
# Main execution
for container in $CHECK_CONTAINERS; do  # Note: no quotes to enable word splitting
    check_and_recover_container "$container" || exit 1
    check_container_ready "$container" || exit 1
    sleep 2
    set_iptables_rules "$container" || exit 1
    echo "$container started"
done

exit 0