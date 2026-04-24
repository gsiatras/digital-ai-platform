import os
import requests
import logging

logger = logging.getLogger(__name__)

KEPLER_PORT = int(os.environ.get("KEPLER_PORT", "9102"))

# Node IP per worker service — each maps to the minikube node hosting that worker
WORKER_NODE_IP = {
    "worker-a-service": os.environ.get("WORKER_A_NODE_IP", "192.168.49.3"),
    "worker-b-service": os.environ.get("WORKER_B_NODE_IP", "192.168.49.4"),
    "worker-c-service": os.environ.get("WORKER_C_NODE_IP", "192.168.49.5"),
}

# StatefulSet pod name per worker service (deterministic: <statefulset>-0)
WORKER_POD_NAME = {
    "worker-a-service": "worker-a-0",
    "worker-b-service": "worker-b-0",
    "worker-c-service": "worker-c-0",
}

# Simulated carbon intensity per node (gCO2/kWh).
# Values represent heterogeneous grid mixes (see docs/methodology.md).
CARBON_INTENSITY_GCO2_KWH = {
    "worker-a-service": float(os.environ.get("CARBON_A", "350")),
    "worker-b-service": float(os.environ.get("CARBON_B", "600")),
    "worker-c-service": float(os.environ.get("CARBON_C", "100")),
}

# Linear power model: E = cpu_time_s * (TDP_W / num_cores)
TDP_W = float(os.environ.get("CPU_TDP_W", "120"))
CPU_CORES = int(os.environ.get("CPU_CORES", "8"))
POWER_PER_CORE_W = TDP_W / CPU_CORES


def get_container_cpu_time_ms(worker_host: str) -> float | None:
    """
    Scrape Kepler metrics from the node hosting worker_host and return the
    cumulative eBPF CPU time (ms) for that worker's container.
    Returns None if the metric cannot be read.
    """
    node_ip = WORKER_NODE_IP.get(worker_host)
    pod_name = WORKER_POD_NAME.get(worker_host)
    if not node_ip or not pod_name:
        logger.warning(f"No node mapping for {worker_host}")
        return None

    try:
        resp = requests.get(f"http://{node_ip}:{KEPLER_PORT}/metrics", timeout=5)
        resp.raise_for_status()
        for line in resp.text.splitlines():
            if (
                line.startswith("kepler_container_bpf_cpu_time_ms_total")
                and f'pod_name="{pod_name}"' in line
                and 'container_name="worker-service"' in line
            ):
                return float(line.split()[-1])
    except Exception as e:
        logger.warning(f"Kepler scrape failed for {worker_host} at {node_ip}: {e}")
    return None


def compute_energy_joules(cpu_time_delta_ms: float) -> float:
    """
    Convert per-container eBPF CPU time delta to energy in joules using the
    linear power model: E = cpu_time_s * P_core
    where P_core = TDP_W / CPU_CORES.
    See docs/methodology.md for derivation and references.
    """
    return (cpu_time_delta_ms / 1000.0) * POWER_PER_CORE_W


def compute_carbon_gco2(energy_joules: float, worker_host: str) -> float:
    """
    Convert energy (joules) to carbon emissions (gCO2) using per-node
    simulated carbon intensity. See docs/methodology.md.
    """
    energy_kwh = energy_joules / 3_600_000.0
    intensity = CARBON_INTENSITY_GCO2_KWH.get(worker_host, 350.0)
    return energy_kwh * intensity
